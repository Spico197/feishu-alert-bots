"""
Inspired by:
- https://github.com/yzhangcs/yzhangcs.github.io/blob/main/arxiv-daily.py
- https://github.com/Jacob-Zhou/jacob-zhou.github.io/blob/master/arxiv-daily.py
"""

import re
import json
import datetime as dt
from typing import Iterable

import arxiv

from alert import send_feishu_messages


# fmt: off
SETTINGS = {
    "timezone": 8,
    "keys": [
        "information extraction", "Information Extraction", "document-level event", "Document-level Event",
        # "language model", "LLM", "task planning", "Large Vision-Language Model",
        "alignment", "preference optimization", "Alignment", "Preference Optimization", "RLHF", "reflection", "Reflection",
        "Task Planning", "task planning",
        "tool learning", "Tool Learning", "tooling", "Tooling",
        "GUI Agent", "GUI", "GUI agent",
        # "knowledge graph", "Knowledge Graph", "knowledge base", "Knowledge Base",
        # "in-context learning", "In-Context Learning",
        # "pre-train", "pretrain", "Pre-train", "Pretrain",
        "Mixture-of-Experts", "MoE",
        # "reasoning",
        "instruction following", "Instruction Following",
    ],
    "authors": [
        "Heng Ji", "Dan Roth", "Manling Li", "Sha Li", "Xinya Du", "Thien Huu Nguyen",
        "Zhiyuan Liu", "Yankai Lin", "Xu Han", "Yubo Chen", "Lifu Huang", "Yaojie Lu", "Bowen Yu", "Xipeng Qiu", "Jie Tang",
        "Sebastian Riedel", "Fabio Petroni", "Alexander M. Rush", "Noah A. Smith",
        "Max Tegmark", "Owain Evans",
        "Jeff Dean", "Nan Du", "Colin Raffel", "Luke Zettlemoyer", "Graham Neubig", "Percy Liang", "Ilya Sutskever",
        "Danqi Chen", "Tianyu Gao", "William Yang Wang", "Tengyu Ma", "Diyi Yang", "Jason Wei", "Junxian He",
        "Tri Dao", "Song Han", "Hao Zhang",
    ],
    "comments": [
        "ACL", "EMNLP", "NAACL", "ICLR", "NeurIPS", "ICML",
    ],
    "categories": ["cs.CL", "cs.AI"]
}
# fmt: on


def load_json(filepath):
    with open(filepath, "r", encoding="utf8") as f:
        return json.load(f)


def dump_json(filepath, data):
    with open(filepath, "w", encoding="utf8") as fout:
        json.dump(data, fout, indent=2, ensure_ascii=False)


def cover_timezones(date: dt.datetime, timezone: int = 8) -> dt.datetime:
    # to UTF+k
    return date.astimezone(dt.timezone(dt.timedelta(hours=timezone)))


def collect_category(
    category: str, days: int = 1, timezone: int = 8
) -> Iterable[arxiv.Result]:
    """
    Collect arxiv papers from a category.
    """
    client = arxiv.Client(num_retries=10, page_size=500)
    query = arxiv.Search(
        query=f"cat:{category}",
        sort_by=arxiv.SortCriterion.LastUpdatedDate,
    )
    results = client.results(query)
    max_iter = 1000

    while True:
        try:
            paper = next(results)
        except StopIteration:
            break
        except arxiv.arxiv.UnexpectedEmptyPageError:
            continue

        max_iter -= 1
        if max_iter <= 0:
            break

        today = dt.datetime.now(paper.updated.tzinfo)
        if paper.updated.date() < today.date() - dt.timedelta(days=days):
            if paper.updated.weekday() < 4 or today.weekday() != 0:
                break

        # Convert to UTC+8
        date = cover_timezones(paper.updated, timezone=timezone).strftime("%b %d %Y %a")
        paper.local_date = date

        yield paper


def span(string: str, span_class: str):
    return f'<span class="{span_class}">{string}</span>'


def replace(pattern: str, string: str, span_class: str):
    obj = re.search(pattern, string, flags=re.I)
    if obj is not None:
        s, e = obj.span()
        string = string[:s] + span(string[s:e], span_class) + string[e:]
    return string


def tan_class(
    papers: Iterable[dict],
    keys: list = None,
    authors: list = None,
    comments: list = None,
    element_class: str = "emph",
):
    keys = keys or []
    authors = authors or []
    comments = comments or []

    new_papers = {}
    for cat, cat_papers in papers.items():
        new_papers[cat] = []
        for paper in cat_papers:
            for i, author in enumerate(paper["authors"]):
                if author in authors:
                    paper["authors"][i] = span(author, element_class)
            for comment in comments:
                paper["comment"] = replace(comment, paper["comment"], element_class)
            key_cands = sorted(keys, key=lambda x: len(x), reverse=True)
            for key in key_cands:
                paper["title"] = replace(key, paper["title"], element_class)
                paper["abstract"] = replace(key, paper["abstract"], element_class)
            new_papers[cat].append(paper)
    return new_papers


def get_highlights(paper: dict):
    highlights = []
    for author in paper["authors"]:
        if author in SETTINGS["authors"]:
            highlights.append(author)
    key_cands = sorted(SETTINGS["keys"], key=lambda x: len(x), reverse=True)
    for key in key_cands:
        if key in paper["title"] or key in paper["abstract"]:
            highlights.append(key)
    return highlights


def is_an_interesting_paper(paper: dict):
    highlights = get_highlights(paper)
    if highlights:
        return True
    else:
        return False


def convert_to_feishu_messages(papers: list):
    messages = []
    for paper in papers:
        title = paper["title"]
        for highlight in sorted(paper["highlights"], key=lambda x: len(x), reverse=True):
            if highlight in title:
                title = title.replace(highlight, f"<b>{highlight}</b>")
        messages.append(
            [
                {"tag": "a", "text": "PDF ", "href": paper["pdf_url"]},
                {"tag": "text", "text": f'{paper["title"]}'},
                {"tag": "text", "text": f" {', '.join(paper['highlights'])}"},
            ]
        )
    return messages


if __name__ == "__main__":
    # Collect papers
    papers = []
    paper_ids = set()
    for category in SETTINGS["categories"]:
        print(f"Collecting {category}...")
        for paper in collect_category(category, days=1, timezone=SETTINGS["timezone"]):
            if paper.entry_id in paper_ids:
                continue
            paper_dict = {
                "title": paper.title,
                "url": paper.entry_id,
                "pdf_url": paper.pdf_url,
                "date": paper.local_date,
                "authors": [author.name for author in paper.authors],
                "comment": "" if paper.comment is None else paper.comment,
                "abstract": paper.summary,
                "category": category,
            }
            highlights = get_highlights(paper_dict)
            if highlights:
                paper_dict["highlights"] = highlights
                papers.append(paper_dict)
                paper_ids.add(paper.entry_id)
                print(
                    f"Collected Highlight Paper: {category} ({len(papers)}) - {paper.local_date} - {paper.title}"
                )

    print("Dumping...")
    dump_json("daily-arxiv-papers.json", papers)
    print(f"Total collected: {len(papers)}")
    print("Sending to feishu...")
    if len(papers) > 0:
        messages = convert_to_feishu_messages(papers)
    else:
        messages = [{"tag": "text", "text": "Oops, there are no arXiv papers today 🥰."}]
    date = dt.datetime.now().strftime("%b %d %Y %a")
    res = send_feishu_messages(f"Daily arXiv Highlights - {date}", messages)
    print(res)
    print("Done!")
