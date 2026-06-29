from dataclasses import dataclass, field
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
    tips: dict = field(default_factory=dict)

    def _build_tips_prompt(self, lang: str) -> tuple[str, str]:
        if _is_chinese(lang):
            system_prompt = (
                "你是学术阅读助手。请用中文输出，不要包含英文。"
                "针对每篇论文，分别生成三个模块：核心概念、推荐原因、研究价值小抄。"
                "输出格式必须是严格的 JSON，包含三个字段：concept、relevance、cheatsheet。"
                "- concept：一句话解释论文中最重要的一个专业术语。"
                "- relevance：一句话解释这篇论文与用户 Zotero 中量子通信/量子光学/精密测量等研究方向的相关性。"
                "- cheatsheet：一个包含 2-4 条关键信息的字符串数组（不要多于4条），每条简短、中文、无英文。"
                "只输出 JSON，不要任何前言或后缀。"
            )
            instruction = (
                "请根据以下论文信息，生成学习提示小 tip，以 JSON 格式返回。\n"
                "要求：全部中文、无英文、JSON 格式。"
            )
        else:
            system_prompt = (
                "You are an academic reading assistant. For each paper, generate three modules: "
                "core concept, relevance, and research value cheatsheet. "
                "Output must be a strict JSON object with three fields: concept, relevance, cheatsheet. "
                "- concept: one sentence explaining the most important technical term in the paper. "
                "- relevance: one sentence explaining why this paper is relevant to the user's research interests. "
                "- cheatsheet: an array of 2-4 short strings summarizing key takeaways. "
                "Return only JSON, no preamble or suffix."
            )
            instruction = (
                "Based on the following paper information, generate learning tips in JSON format."
            )
        return system_prompt, instruction

    def _generate_tips_with_llm(self, openai_client: OpenAI, llm_params: dict) -> dict:
        lang = llm_params.get('language', 'English')
        system_prompt, instruction = self._build_tips_prompt(lang)

        prompt = instruction + "\n\n"
        if self.title:
            prompt += f"Title:\n{self.title}\n\n"
        if self.abstract:
            prompt += f"Abstract:\n{self.abstract}\n\n"
        if self.tldr:
            prompt += f"TLDR:\n{self.tldr}\n\n"
        if self.full_text:
            prompt += f"Preview of main content:\n{self.full_text[:3000]}\n\n"

        enc = tiktoken.encoding_for_model("gpt-4o")
        prompt_tokens = enc.encode(prompt)
        prompt_tokens = prompt_tokens[:4000]
        prompt = enc.decode(prompt_tokens)

        generation_kwargs = dict(llm_params.get('generation_kwargs', {}))

        response = openai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            **generation_kwargs
        )
        content = response.choices[0].message.content
        logger.info(f"[TIPS] generated for {self.url}: {content[:200]}...")
        return json.loads(content)

    def generate_tips(self, openai_client: OpenAI, llm_params: dict) -> dict:
        try:
            tips = self._generate_tips_with_llm(openai_client, llm_params)
            self.tips = tips
            return tips
        except Exception as e:
            logger.warning(f"Failed to generate tips of {self.url}: {e}")
            self.tips = {}
            return {}

    def _generate_tldr_with_llm(self, openai_client: OpenAI, llm_params: dict) -> str:
        lang = llm_params.get('language', 'English')
        logger.info(f"[TLDR] detected language config: {lang!r}, is_chinese={_is_chinese(lang)}")

        if _is_chinese(lang):
            instruction = (
                "请阅读以下论文信息，并用流利、地道的中文写一句话摘要。"
                "要求：只输出中文摘要，不要包含任何英文单词，不要翻译标题，不要复述原文句子。"
            )
            system_prompt = (
                "你是学术摘要助手。你的回答必须全部使用中文，不得包含英文。"
                "直接输出摘要，不要加前缀、解释或额外内容。"
            )
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

        generation_kwargs = dict(llm_params.get('generation_kwargs', {}))

        logger.info(f"[TLDR] system prompt language: {'Chinese' if _is_chinese(lang) else 'English'}")

        response = openai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": prompt},
            ],
            **generation_kwargs
        )
        tldr = response.choices[0].message.content
        logger.info(f"[TLDR] generated ({'Chinese' if _is_chinese(lang) else 'English'} mode): {tldr[:100]}...")
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