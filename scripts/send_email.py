#!/usr/bin/env python3
import json
import os
from pathlib import Path

import resend

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "data" / "latest.json"


def build_html(data):
    def section(title, items):
        lis = "".join(
            (
                f"<li><a href='{i['url']}'>{i['title']}</a>"
                f"<br><small>{build_meta(i)}</small>"
                f"<p>{i.get('summary','')}</p>"
                f"{build_scholar_link(i)}</li>"
            )
            for i in items
        )
        return f"<h2>{title}</h2><ul>{lis}</ul>"

    def build_meta(item):
        parts = [item.get("source", ""), item.get("published_at", "")]
        if item.get("cited_by_total"):
            parts.append(f"Citado por {item['cited_by_total']}")
        if item.get("versions_total"):
            parts.append(f"{item['versions_total']} versões")
        return " · ".join([part for part in parts if part])

    def build_scholar_link(item):
        scholar_url = item.get("scholar_url")
        if not scholar_url:
            return ""
        label = item.get("scholar_url_label", "Buscar no Google Academico")
        return f"<p><a href='{scholar_url}'>{label}</a></p>"

    return f"""
    <html>
      <body>
        <h1>Newsletter diária de IA</h1>
        <p>Gerada em: {data['generated_at']}</p>
        {section('Papers', data['papers'])}
        {section('Pesquisas e Google Academico', data.get('scholar', []))}
        {section('Notícias', data['news'])}
        {section('Artigos e blogs', data['blogs'])}
      </body>
    </html>
    """


def main():
    api_key = os.environ.get("RESEND_API_KEY")
    to_email = os.environ.get("NEWSLETTER_TO")
    from_email = os.environ.get("NEWSLETTER_FROM", "AI Digest <onboarding@resend.dev>")
    if not api_key or not to_email:
        print("Missing RESEND_API_KEY or NEWSLETTER_TO. Skipping email send.")
        return

    resend.api_key = api_key
    data = json.loads(LATEST.read_text(encoding="utf-8"))
    params = {
        "from": from_email,
        "to": [to_email],
        "subject": "Newsletter diária de IA",
        "html": build_html(data),
    }
    result = resend.Emails.send(params)
    print(result)


if __name__ == "__main__":
    main()
