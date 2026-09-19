"""Mirror the public Meridian documentation as Markdown for offline study.

Crawls https://developers.google.com/meridian/* (one language) breadth-first, keeps only
the article body of each page, and writes one .md per page under libs/docs/meridian/ plus
an INDEX.md. The mirror is gitignored: it is regenerable and the content belongs to Google.

Run from the repo root with ephemeral deps (no change to pyproject/uv.lock):

    uv run --with requests --with beautifulsoup4 --with markdownify \
        python libs/docs/fetch_meridian_docs.py [--lang es-419] [--max-pages 2000]
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify

HOST = "developers.google.com"
ROOT_PATH = "/meridian"
START = "https://developers.google.com/meridian/mmm"
OUT_DIR = Path(__file__).resolve().parent / "meridian"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) mmt-docs-mirror/1.0"}
SKIP_PREFIXES = ("/meridian/mmm?", "/meridian/geox?")


def canonical(url: str, lang: str) -> str | None:
    """Normalise a link to a crawlable Meridian docs URL, or None if out of scope."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", "") or (parsed.netloc and parsed.netloc != HOST):
        return None
    # devsite links API reference pages both as ".../Name" and ".../Name.md": one page.
    path = re.sub(r"\.md$", "", parsed.path.rstrip("/")) or "/"
    if not (path == ROOT_PATH or path.startswith(ROOT_PATH + "/")):
        return None
    if re.search(r"\.(png|jpg|jpeg|gif|svg|pdf|zip|ipynb)$", path, re.IGNORECASE):
        return None
    return urlunparse(("https", HOST, path, "", f"hl={lang}", ""))


TITLE_NOISE = re.compile(
    r"\s*(Organiza tus páginas con colecciones|Stay organized with collections|\|\s*Google for Developers).*$"
)


def clean_title(text: str) -> str:
    """Drop the devsite UI text that gets glued to h1/title."""
    return TITLE_NOISE.sub("", text).strip() or text


def local_path(url: str) -> Path:
    path = urlparse(url).path[len(ROOT_PATH):].strip("/") or "index"
    return OUT_DIR / (path + ".md")


def extract(html: str, url: str) -> tuple[str, str, list[str]]:
    """Return (title, markdown body, links) for one docs page."""
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.find("h1") or soup.find("title"))
    title_text = clean_title(title.get_text(" ", strip=True) if title else url)
    links = [a["href"] for a in soup.find_all("a", href=True)]
    article = soup.find("div", class_="devsite-article-body") or soup.find("article") or soup.body
    for tag in article.find_all(["script", "style", "nav", "devsite-feedback", "button"]):
        tag.decompose()
    body = markdownify(str(article), heading_style="ATX", bullets="-")
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return title_text, body, links


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lang", default="es-419")
    parser.add_argument("--max-pages", type=int, default=2000)
    parser.add_argument("--delay", type=float, default=0.3, help="seconds between requests")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    start = canonical(START, args.lang)
    queue: deque[str] = deque([start])
    seen: set[str] = {start}
    index: list[tuple[str, str, Path]] = []
    session = requests.Session()
    session.headers.update(HEADERS)
    today = dt.date.today().isoformat()

    while queue and len(index) < args.max_pages:
        url = queue.popleft()
        try:
            response = session.get(url, timeout=30)
        except requests.RequestException as error:
            print(f"SKIP {url}: {error}", file=sys.stderr)
            continue
        if response.status_code != 200 or "text/html" not in response.headers.get("content-type", ""):
            print(f"SKIP {url}: HTTP {response.status_code}", file=sys.stderr)
            continue
        title, body, links = extract(response.text, url)
        target = local_path(url)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"# {title}\n\nFuente: {url}\nDescargado: {today}\n\n---\n\n{body}\n", encoding="utf-8"
        )
        index.append((title, url, target.relative_to(OUT_DIR)))
        print(f"{len(index):4d} {target.relative_to(OUT_DIR)}")
        for link in links:
            candidate = canonical(urljoin(url, link), args.lang)
            if candidate and candidate not in seen:
                seen.add(candidate)
                queue.append(candidate)
        time.sleep(args.delay)

    lines = [
        "# Índice del espejo de documentación de Meridian",
        "",
        f"Descargado: {today} · idioma: {args.lang} · páginas: {len(index)}",
        "",
        "Espejo local y gitignored de developers.google.com/meridian. Regenerar con",
        "`libs/docs/fetch_meridian_docs.py` (ver cabecera del script).",
        "",
    ]
    for title, url, rel in sorted(index, key=lambda item: str(item[2])):
        lines.append(f"- [{title}]({rel}) — {url}")
    (OUT_DIR / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(index)} pages and INDEX.md under {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
