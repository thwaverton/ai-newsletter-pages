#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
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

CROSSREF_API_URL = "https://api.crossref.org/works"
CROSSREF_QUERY = '"artificial intelligence" machine learning "large language model" "generative AI" multimodal reasoning'
CROSSREF_DAYS_BACK = int(os.environ.get("CROSSREF_DAYS_BACK", "10"))
SERPAPI_API_URL = "https://serpapi.com/search.json"
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY")
SERPAPI_SCHOLAR_QUERY = os.environ.get(
    "SERPAPI_SCHOLAR_QUERY",
    '"artificial intelligence" OR "machine learning" OR "large language model" OR "generative ai"',
)
SERPAPI_SCHOLAR_HL = os.environ.get("SERPAPI_SCHOLAR_HL", "en")
SERPAPI_SCHOLAR_NUM = max(1, min(20, int(os.environ.get("SERPAPI_SCHOLAR_NUM", "20"))))
REQUEST_HEADERS = {
    "User-Agent": "ai-daily-digest/1.0 (+https://thwaverton.github.io/ai-newsletter-pages/)"
}


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
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.replace("\n", " ").split())


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def scholar_search_url(query):
    return "https://scholar.google.com/scholar?q=" + quote_plus(query or "")


def date_parts_to_iso(parts):
    if not parts:
        return None
    try:
        normalized = list(parts[:3]) + [1] * (3 - len(parts[:3]))
        return datetime(normalized[0], normalized[1], normalized[2], tzinfo=timezone.utc).isoformat()
    except Exception:
        return None


def choose_crossref_date(item):
    for key in ("published-print", "published-online", "issued", "created"):
        value = item.get(key, {})
        date_parts = (value.get("date-parts") or [[]])[0]
        parsed = date_parts_to_iso(date_parts)
        if parsed:
            return parsed
    return None


def iso_to_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def request_json(url, params=None):
    res = requests.get(url, params=params, headers=REQUEST_HEADERS, timeout=30)
    res.raise_for_status()
    return res.json()


def crossref_summary(item):
    abstract = clean_text(item.get("abstract"))
    if abstract:
        return abstract[:400]

    journal = clean_text((item.get("container-title") or [""])[0])
    publisher = clean_text(item.get("publisher"))
    parts = [part for part in [journal, publisher] if part]
    if parts:
        return f"Publicado em {' · '.join(parts[:2])}."
    return "Artigo academico recente relacionado a IA."


def extract_year(text):
    if not text:
        return None
    match = re.search(r"\b(19|20)\d{2}\b", text)
    return int(match.group(0)) if match else None


def scholar_publication_details(item):
    info = item.get("publication_info") or {}
    summary = clean_text(info.get("summary"))
    authors = []

    for author in info.get("authors", [])[:6]:
        name = clean_text(author.get("name"))
        if name:
            authors.append(name)

    if not authors and summary:
        author_part = summary.split(" - ", 1)[0]
        if "," in author_part:
            authors = [clean_text(name) for name in author_part.split(",")[:6] if clean_text(name)]

    year = extract_year(summary)
    published_at = None
    if year:
        published_at = datetime(year, 1, 1, tzinfo=timezone.utc).isoformat()

    return summary, authors, published_at


def scholar_primary_link(item):
    if item.get("link"):
        return item["link"]
    for resource in item.get("resources", []):
        if resource.get("link"):
            return resource["link"]
    return None


def scholar_inline_links(item):
    inline = item.get("inline_links") or {}
    versions = inline.get("versions") or {}
    cited_by = inline.get("cited_by") or {}

    if versions.get("link"):
        return versions.get("link"), "Ver versões no Google Acadêmico"
    if cited_by.get("link"):
        return cited_by.get("link"), "Ver citações no Google Acadêmico"
    if inline.get("related_pages_link"):
        return inline.get("related_pages_link"), "Abrir no Google Acadêmico"
    return None, None


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
            "published_at": iso_now(),
            "authors": ["Autor Exemplo"],
            "score": 1,
            "scholar_url": scholar_search_url("paper de IA"),
            "scholar_url_label": "Pesquisar no Google Academico",
        }],
        "news": [{
            "source": "Google News",
            "type": "news",
            "title": "Exemplo de noticia de IA",
            "summary": "Placeholder inicial. Assim que o workflow rodar online, este conteudo sera substituido por dados reais.",
            "url": "https://news.google.com/",
            "published_at": iso_now(),
            "score": 1,
        }],
        "research_blog": [{
            "source": "AI Blog",
            "type": "research_blog",
            "title": "Exemplo de artigo ou blog de pesquisa",
            "summary": "Placeholder inicial para o primeiro deploy do projeto.",
            "url": "https://openai.com/news/",
            "published_at": iso_now(),
            "score": 1,
        }],
        "scholar": [{
            "source": "Crossref",
            "type": "scholar",
            "title": "Exemplo de pesquisa academica em IA",
            "summary": "Secao academica inicial. No deploy online, ela sera atualizada com artigos recentes e atalho de busca no Google Academico.",
            "url": "https://api.crossref.org/",
            "published_at": iso_now(),
            "authors": ["Pesquisador Exemplo"],
            "score": 1,
            "scholar_url": scholar_search_url("pesquisa academica IA"),
            "scholar_url_label": "Pesquisar no Google Academico",
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


def fetch_crossref_research():
    until_date = datetime.now(timezone.utc).date()
    from_date = until_date - timedelta(days=CROSSREF_DAYS_BACK)
    params = {
        "query": CROSSREF_QUERY,
        "filter": f"from-pub-date:{from_date.isoformat()},until-pub-date:{until_date.isoformat()},type:journal-article,type:proceedings-article",
        "sort": "published",
        "order": "desc",
        "rows": 25,
    }
    try:
        data = request_json(CROSSREF_API_URL, params=params)
    except requests.RequestException:
        return fallback_items("scholar")

    items = []
    for entry in data.get("message", {}).get("items", []):
        title = clean_text((entry.get("title") or [""])[0])
        if not title:
            continue

        summary = crossref_summary(entry)
        published_at = choose_crossref_date(entry)
        published_date = iso_to_date(published_at)
        if not published_date or published_date < from_date or published_date > until_date:
            continue

        authors = []
        for author in entry.get("author", [])[:6]:
            full_name = " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part).strip()
            if full_name:
                authors.append(full_name)

        doi = clean_text(entry.get("DOI"))
        url = entry.get("URL") or (f"https://doi.org/{doi}" if doi else None)
        if not url:
            continue

        journal = clean_text((entry.get("container-title") or [""])[0])
        publisher = clean_text(entry.get("publisher"))
        source = journal or publisher or "Crossref"
        score = score_item(title, summary)

        items.append({
            "source": source,
            "type": "scholar",
            "title": title,
            "summary": summary,
            "url": url,
            "published_at": published_at,
            "authors": authors,
            "score": score + 1,
            "scholar_url": scholar_search_url(title),
            "scholar_url_label": "Pesquisar no Google Academico",
        })

    ranked = [
        item for item in sorted(
            items,
            key=lambda x: (x.get("score", 0), x.get("published_at") or ""),
            reverse=True,
        )
        if item.get("score", 0) >= 2
    ]
    return ranked[:8] or fallback_items("scholar")


def fetch_serpapi_scholar():
    current_year = datetime.now(timezone.utc).year
    params = {
        "engine": "google_scholar",
        "api_key": SERPAPI_API_KEY,
        "q": SERPAPI_SCHOLAR_QUERY,
        "hl": SERPAPI_SCHOLAR_HL,
        "num": SERPAPI_SCHOLAR_NUM,
        "as_ylo": current_year,
        "as_yhi": current_year,
        "scisbd": 2,
    }
    try:
        data = request_json(SERPAPI_API_URL, params=params)
    except requests.RequestException:
        return None

    if data.get("error"):
        return None

    items = []
    for entry in data.get("organic_results", []):
        title = clean_text(entry.get("title"))
        if not title:
            continue

        url = scholar_primary_link(entry)
        if not url:
            continue

        summary = clean_text(entry.get("snippet", ""))[:400]
        publication_summary, authors, published_at = scholar_publication_details(entry)
        scholar_url, scholar_label = scholar_inline_links(entry)
        cited_by = ((entry.get("inline_links") or {}).get("cited_by") or {}).get("total")
        versions = ((entry.get("inline_links") or {}).get("versions") or {}).get("total")

        item = {
            "source": "Google Scholar",
            "type": "scholar",
            "title": title,
            "summary": summary or publication_summary or "Resultado recente retornado pelo Google Acadêmico.",
            "url": url,
            "published_at": published_at,
            "authors": authors,
            "score": score_item(title, f"{summary} {publication_summary}") + 1,
            "scholar_url": scholar_url or scholar_search_url(title),
            "scholar_url_label": scholar_label or "Pesquisar no Google Acadêmico",
            "publication_summary": publication_summary,
            "cited_by_total": cited_by,
            "versions_total": versions,
        }
        items.append(item)

    ranked = [item for item in items if item.get("score", 0) >= 2]
    return ranked[:8] or None


def fetch_scholar_research():
    if SERPAPI_API_KEY:
        scholar_items = fetch_serpapi_scholar()
        if scholar_items:
            return scholar_items, "Google Academico ativo via SerpAPI."
        return fetch_crossref_research(), "SerpAPI configurada, mas a busca do Google Academico falhou nesta execucao; usando Crossref como fallback."

    return fetch_crossref_research(), "SERPAPI_API_KEY nao configurada; usando Crossref como fallback para a secao academica."


def build_digest(papers, news, blogs, scholar, scholar_note):
    return {
        "generated_at": iso_now(),
        "papers": sorted(papers, key=lambda x: (x.get("score", 0), x.get("published_at") or ""), reverse=True)[:6],
        "news": sorted(news, key=lambda x: (x.get("score", 0), x.get("published_at") or ""), reverse=True)[:6],
        "blogs": blogs[:6],
        "scholar": scholar[:6],
        "notes": [
            "LinkedIn nao foi automatizado neste MVP porque scraping de posts e instavel e depende de ferramentas externas ou conta autenticada.",
            scholar_note,
            "Google Academico nao oferece feed publico nativo para esse fluxo; a integracao real usa SerpAPI quando a chave esta configurada.",
            "Para e-mail diario, configure os secrets opcionais do workflow.",
        ],
    }


def main():
    papers = fetch_arxiv()
    news = fetch_google_news()
    blogs = fetch_blogs()
    scholar, scholar_note = fetch_scholar_research()
    digest = build_digest(papers, news, blogs, scholar, scholar_note)

    for out_dir in (DATA_DIR, SITE_DATA_DIR):
        (out_dir / "latest.json").write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "papers": len(digest["papers"]),
        "news": len(digest["news"]),
        "blogs": len(digest["blogs"]),
        "scholar": len(digest["scholar"]),
        "generated_at": digest["generated_at"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
