#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SITE_DATA_DIR = ROOT / "site" / "data"
DATA_DIR.mkdir(exist_ok=True)
SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

TOPICS = [
    "artificial intelligence",
    "machine learning",
    "large language models",
    "generative AI",
    "computer vision",
]

ARXIV_QUERY = "cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV"
ARXIV_URL = (
    "https://export.arxiv.org/api/query?search_query="
    + quote_plus(ARXIV_QUERY)
    + "&sortBy=submittedDate&sortOrder=descending&start=0&max_results=20"
)

GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search?q="
    + quote_plus('artificial intelligence OR "machine learning" OR "generative AI" when:1d')
    + "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
)

BLOG_FEEDS = [
    "https://openai.com/news/rss.xml",
    "https://blog.google/technology/ai/rss/",
    "https://www.anthropic.com/news/rss.xml",
]


def to_iso(value):
    if not value:
        return None
    if isinstance(value, str):
        try:
            return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
        except Exception:
            return value
    if hasattr(value, "tm_year"):
        return datetime(*value[:6], tzinfo=timezone.utc).isoformat()
    return None


def clean_text(text):
    return " ".join((text or "").replace("\n", " ").split())


def score_item(title, summary=""):
    text = f"{title} {summary}".lower()
    score = 0
    for topic in TOPICS:
        if topic in text:
            score += 2
    for kw in ["llm", "agent", "reasoning", "benchmark", "safety", "multimodal", "robotics"]:
        if kw in text:
            score += 1
    return score


def fallback_items(kind):
    base = {
        "paper": [{
            "source": "arXiv",
            "type": "paper",
            "title": "Exemplo de paper de IA",
            "summary": "Este item aparece como placeholder ate a primeira execucao online do workflow no GitHub Actions.",
            "url": "https://arxiv.org/",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "authors": ["Autor Exemplo"],
            "score": 1,
        }],
        "news": [{
            "source": "Google News",
            "type": "news",
            "title": "Exemplo de noticia de IA",
            "summary": "Placeholder inicial. Assim que o workflow rodar online, este conteudo sera substituido por dados reais.",
            "url": "https://news.google.com/",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "score": 1,
        }],
        "research_blog": [{
            "source": "AI Blog",
            "type": "research_blog",
            "title": "Exemplo de artigo ou blog de pesquisa",
            "summary": "Placeholder inicial para o primeiro deploy do projeto.",
            "url": "https://openai.com/news/",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "score": 1,
        }],
    }
    return base[kind]


def fetch_arxiv():
    parsed = feedparser.parse(ARXIV_URL)
    items = []
    for entry in parsed.entries[:10]:
        authors = [a.get("name", "") for a in entry.get("authors", [])]
        items.append({
            "source": "arXiv",
            "type": "paper",
            "title": clean_text(entry.get("title")),
            "summary": clean_text(entry.get("summary"))[:400],
            "url": entry.get("link"),
            "published_at": to_iso(entry.get("published") or entry.get("updated")),
            "authors": authors[:6],
            "score": score_item(entry.get("title"), entry.get("summary")),
        })
    return items or fallback_items("paper")


def fetch_google_news():
    parsed = feedparser.parse(GOOGLE_NEWS_RSS)
    items = []
    for entry in parsed.entries[:10]:
        source_title = None
        tags = entry.get("tags") or []
        if tags:
            source_title = tags[0].get("term")
        items.append({
            "source": source_title or "Google News",
            "type": "news",
            "title": clean_text(entry.get("title")),
            "summary": clean_text(entry.get("summary", ""))[:300],
            "url": entry.get("link"),
            "published_at": to_iso(entry.get("published")),
            "score": score_item(entry.get("title"), entry.get("summary", "")),
        })
    return items or fallback_items("news")


def fetch_blogs():
    items = []
    for feed in BLOG_FEEDS:
        parsed = feedparser.parse(feed)
        for entry in parsed.entries[:4]:
            items.append({
                "source": clean_text(parsed.feed.get("title", "Blog")),
                "type": "research_blog",
                "title": clean_text(entry.get("title")),
                "summary": clean_text(entry.get("summary", ""))[:300],
                "url": entry.get("link"),
                "published_at": to_iso(entry.get("published") or entry.get("updated")),
                "score": score_item(entry.get("title"), entry.get("summary", "")),
            })
    items.sort(key=lambda x: (x.get("published_at") or "", x.get("score", 0)), reverse=True)
    return (items[:10] or fallback_items("research_blog"))


def build_digest(papers, news, blogs):
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "papers": sorted(papers, key=lambda x: (x.get("score", 0), x.get("published_at") or ""), reverse=True)[:6],
        "news": sorted(news, key=lambda x: (x.get("score", 0), x.get("published_at") or ""), reverse=True)[:6],
        "blogs": blogs[:6],
        "notes": [
            "LinkedIn nao foi automatizado neste MVP porque scraping de posts e instavel e depende de ferramentas externas ou conta autenticada.",
            "Para e-mail diario, configure os secrets opcionais do workflow.",
        ],
    }


def main():
    papers = fetch_arxiv()
    news = fetch_google_news()
    blogs = fetch_blogs()
    digest = build_digest(papers, news, blogs)

    for out_dir in (DATA_DIR, SITE_DATA_DIR):
        (out_dir / "latest.json").write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "papers": len(digest["papers"]),
        "news": len(digest["news"]),
        "blogs": len(digest["blogs"]),
        "generated_at": digest["generated_at"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
