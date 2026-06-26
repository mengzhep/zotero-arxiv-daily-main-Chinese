from .protocol import Paper
import math


def _is_chinese(language: str | None) -> bool:
    if language is None:
        return False
    return language.strip().lower() in {"chinese", "zh", "中文", "简体中文", "繁体中文"}


framework = """
<!DOCTYPE HTML>
<html>
<head>
  <style>
    .star-wrapper {
      font-size: 1.3em; /* 调整星星大小 */
      line-height: 1; /* 确保垂直对齐 */
      display: inline-flex;
      align-items: center; /* 保持对齐 */
    }
    .half-star {
      display: inline-block;
      width: 0.5em; /* 半颗星的宽度 */
      overflow: hidden;
      white-space: nowrap;
      vertical-align: middle;
    }
    .full-star {
      vertical-align: middle;
    }
  </style>
</head>
<body>

<div>
    __CONTENT__
</div>

<br><br>
<div>
__UNSUBSCRIBE__
</div>

</body>
</html>
"""


def get_empty_html(language: str = "English"):
    if _is_chinese(language):
        message = "今日没有新论文，休息一下！"
    else:
        message = "No Papers Today. Take a Rest!"
    block_template = f"""
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
  <tr>
    <td style="font-size: 20px; font-weight: bold; color: #333;">
        {message}
    </td>
  </tr>
  </table>
  """
    return block_template


def get_block_html(
    title: str,
    authors: str,
    rate: str,
    tldr: str,
    pdf_url: str,
    affiliations: str | None = None,
    language: str = "English",
):
    if _is_chinese(language):
        relevance_label = "相关度"
        tldr_label = "摘要"
        pdf_label = "PDF"
        affiliation_unknown = "未知机构"
    else:
        relevance_label = "Relevance"
        tldr_label = "TLDR"
        pdf_label = "PDF"
        affiliation_unknown = "Unknown Affiliation"

    block_template = f"""
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
    <tr>
        <td style="font-size: 20px; font-weight: bold; color: #333;">
            {title}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #666; padding: 8px 0;">
            {authors}
            <br>
            <i>{affiliations if affiliations else affiliation_unknown}</i>
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>{relevance_label}:</strong> {rate}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>{tldr_label}:</strong> {tldr}
        </td>
    </tr>

    <tr>
        <td style="padding: 8px 0;">
            <a href="{pdf_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #d9534f; padding: 8px 16px; border-radius: 4px;">{pdf_label}</a>
        </td>
    </tr>
</table>
"""
    return block_template


def get_stars(score: float):
    full_star = '<span class="full-star">⭐</span>'
    half_star = '<span class="half-star">⭐</span>'
    low = 6
    high = 8
    if score <= low:
        return ""
    elif score >= high:
        return full_star * 5
    else:
        interval = (high - low) / 10
        star_num = math.ceil((score - low) / interval)
        full_star_num = int(star_num / 2)
        half_star_num = star_num - full_star_num * 2
        return (
            '<div class="star-wrapper">'
            + full_star * full_star_num
            + half_star * half_star_num
            + "</div>"
        )


def render_email(papers: list[Paper], language: str = "English") -> str:
    if _is_chinese(language):
        unsubscribe_text = "如需退订，请在 GitHub Action 设置中移除您的邮箱。"
    else:
        unsubscribe_text = "To unsubscribe, remove your email in your Github Action setting."

    parts = []
    if len(papers) == 0:
        return (
            framework.replace("__CONTENT__", get_empty_html(language))
            .replace("__UNSUBSCRIBE__", unsubscribe_text)
        )

    for p in papers:
        # rate = get_stars(p.score)
        rate = round(p.score, 1) if p.score is not None else "Unknown"
        author_list = [a for a in p.authors]
        num_authors = len(author_list)
        if num_authors <= 5:
            authors = ", ".join(author_list)
        else:
            authors = ", ".join(author_list[:3] + ["..."] + author_list[-2:])
        if p.affiliations is not None:
            affiliations = p.affiliations[:5]
            affiliations = ", ".join(affiliations)
            if len(p.affiliations) > 5:
                affiliations += ", ..."
        else:
            affiliations = None
        parts.append(
            get_block_html(p.title, authors, rate, p.tldr, p.pdf_url, affiliations, language)
        )

    content = "<br>" + "</br><br>".join(parts) + "</br>"
    return (
        framework.replace("__CONTENT__", content)
        .replace("__UNSUBSCRIBE__", unsubscribe_text)
    )
