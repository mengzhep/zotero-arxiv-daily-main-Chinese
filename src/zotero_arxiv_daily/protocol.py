from dataclasses import dataclass
from typing import Optional, TypeVar
from datetime import datetime
import re
import tiktoken
from openai import OpenAI
from loguru import logger
import json
RawPaperItem = TypeVar('RawPaperItem')


def _is_chinese(language: str | None) -> bool:
    if language is None:
        return False
    return language.strip().lower() in {"chinese", "zh", "中文", "简体中文", "繁体中文"}


@dataclass
class Paper:
    source: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    pdf_url: Optional[str] = None
    full_text: Optional[str] = None
    tldr: Optional[str] = None
    affiliations: Optional[list[str]] = None
    score: Optional[float] = None

    def _generate_tldr_with_llm(self, openai_client: OpenAI, llm_params: dict) -> str:
        lang = llm_params.get('language', 'English')
        if _is_chinese(lang):
            instruction = f"根据以下论文信息，用{lang}生成一句话的 TLDR 摘要："
            system_prompt = f"你是一位擅长总结学术论文的助手，能够用{lang}准确提炼论文的核心思想。"
        else:
            instruction = f"Given the following information of a paper, generate a one-sentence TLDR summary in {lang}:\n\n"
            system_prompt = f"You are an assistant who perfectly summarizes scientific paper, and gives the core idea of the paper to the user. Your answer should be in {lang}."

        prompt = instruction + "\n\n"
        if self.title:
            prompt += f"Title:\n {self.title}\n\n"

        if self.abstract:
            prompt += f"Abstract: {self.abstract}\n\n"

        if self.full_text:
            prompt += f"Preview of main content:\n {self.full_text}\n\n"

        if not self.full_text and not self.abstract:
            logger.warning(f"Neither full text nor abstract is provided for {self.url}")
            return "Failed to generate TLDR. Neither full text nor abstract is provided"

        # use gpt-4o tokenizer for estimation
        enc = tiktoken.encoding_for_model("gpt-4o")
        prompt_tokens = enc.encode(prompt)
        prompt_tokens = prompt_tokens[:4000]  # truncate to 4000 tokens
        prompt = enc.decode(prompt_tokens)

        response = openai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": prompt},
            ],
            **llm_params.get('generation_kwargs', {})
        )
        tldr = response.choices[0].message.content
        return tldr

    def generate_tldr(self, openai_client: OpenAI, llm_params: dict) -> str:
        try:
            tldr = self._generate_tldr_with_llm(openai_client, llm_params)
            self.tldr = tldr
            return tldr
        except Exception as e:
            logger.warning(f"Failed to generate tldr of {self.url}: {e}")
            tldr = self.abstract
            self.tldr = tldr
            return tldr

    def _generate_affiliations_with_llm(self, openai_client: OpenAI, llm_params: dict) -> Optional[list[str]]:
        if self.full_text is not None:
            lang = llm_params.get('language', 'English')
            if _is_chinese(lang):
                instruction = (
                    "根据论文开头部分，按作者顺序提取作者所属机构，返回一个 Python 列表。"
                    "如果找不到任何机构，请返回空列表 '[]'：\n\n"
                )
                system_prompt = (
                    "你是一位擅长从论文中提取作者机构的助手。"
                    "请按作者顺序返回一个 Python 列表，例如 [\"清华大学\",\"北京大学\"]。"
                    "如果机构包含多级信息（如 \"清华大学计算机科学与技术系\"），请只返回顶级机构 \"清华大学\"。"
                    "不要包含重复机构。如果找不到任何机构，请返回空列表 []。"
                    "请只返回最终机构列表，不要返回任何中间结果。"
                )
            else:
                instruction = (
                    "Given the beginning of a paper, extract the affiliations of the authors in a python list format, "
                    "which is sorted by the author order. If there is no affiliation found, return an empty list '[]':\n\n"
                )
                system_prompt = (
                    "You are an assistant who perfectly extracts affiliations of authors from a paper. "
                    "You should return a python list of affiliations sorted by the author order, "
                    "like [\"TsingHua University\",\"Peking University\"]. "
                    "If an affiliation is consisted of multi-level affiliations, like 'Department of Computer Science, TsingHua University', "
                    "you should return the top-level affiliation 'TsingHua University' only. "
                    "Do not contain duplicated affiliations. If there is no affiliation found, you should return an empty list [ ]. "
                    "You should only return the final list of affiliations, and do not return any intermediate results."
                )

            prompt = instruction + self.full_text
            # use gpt-4o tokenizer for estimation
            enc = tiktoken.encoding_for_model("gpt-4o")
            prompt_tokens = enc.encode(prompt)
            prompt_tokens = prompt_tokens[:2000]  # truncate to 2000 tokens
            prompt = enc.decode(prompt_tokens)
            affiliations = openai_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {"role": "user", "content": prompt},
                ],
                **llm_params.get('generation_kwargs', {})
            )
            affiliations = affiliations.choices[0].message.content

            affiliations = re.search(r'\[.*?\]', affiliations, flags=re.DOTALL).group(0)
            affiliations = json.loads(affiliations)
            affiliations = list(set(affiliations))
            affiliations = [str(a) for a in affiliations]

            return affiliations

    def generate_affiliations(self, openai_client: OpenAI, llm_params: dict) -> Optional[list[str]]:
        try:
            affiliations = self._generate_affiliations_with_llm(openai_client, llm_params)
            self.affiliations = affiliations
            return affiliations
        except Exception as e:
            logger.warning(f"Failed to generate affiliations of {self.url}: {e}")
            self.affiliations = None
            return None


@dataclass
class CorpusPaper:
    title: str
    abstract: str
    added_date: datetime
    paths: list[str]
