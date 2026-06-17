"""
Download a real, multi-domain document corpus to local disk (no online storage).

Sources (all public, no API keys):
  • arXiv Atom API      → research papers (abstract = small tier; full PDF = large tier)
  • Wikipedia REST API  → technical/business/long-form + NOISE (food/sports/travel/finance)
  • Static doc HTML     → framework documentation (trafilatura extraction)

Resumable: re-running skips already-stored docs. Reproducible: every doc is
recorded in the manifest with source id, url, token count, tier, and sha256.

Usage:
    python -m corpus.ingest --target 1200
    python -m corpus.ingest --target 50 --no-pdf      # quick smoke
"""
import argparse
import ssl
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CTX = ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from corpus.store import CorpusStore
from corpus import sources

UA = "ContextOS-Eval/1.0 (research benchmark; contact: local)"
_ATOM = "{http://www.w3.org/2005/Atom}"


def _get(url: str, timeout: float = 30, retries: int = 3) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


# ─── arXiv ────────────────────────────────────────────────────────────────────
def ingest_arxiv(store: CorpusStore, per_query: int, fulltext_per_query: int, do_pdf: bool):
    for query, domain in sources.ARXIV_QUERIES:
        url = ("http://export.arxiv.org/api/query?search_query="
               + urllib.parse.quote(query)
               + f"&start=0&max_results={per_query}&sortBy=submittedDate&sortOrder=descending")
        try:
            xml = _get(url, timeout=40)
        except Exception as e:
            print(f"  [arxiv] query failed: {e}")
            continue
        root = ET.fromstring(xml)
        entries = root.findall(f"{_ATOM}entry")
        pdf_budget = fulltext_per_query if do_pdf else 0
        for e in entries:
            aid = e.findtext(f"{_ATOM}id", "").rsplit("/", 1)[-1]
            title = (e.findtext(f"{_ATOM}title", "") or "").strip().replace("\n", " ")
            summary = (e.findtext(f"{_ATOM}summary", "") or "").strip()
            if aid and summary:
                store.add(f"arxiv-abs:{aid}", domain, "arxiv", title,
                          f"https://arxiv.org/abs/{aid}", f"{title}\n\n{summary}", min_tokens=120)
            # Full text (large tier) for a few papers per query.
            if pdf_budget > 0 and aid and not store.has(f"arxiv-pdf:{aid}"):
                pdf_url = None
                for link in e.findall(f"{_ATOM}link"):
                    if link.get("title") == "pdf":
                        pdf_url = link.get("href")
                if pdf_url:
                    txt = _pdf_text(pdf_url)
                    if txt and len(txt) > 2000:
                        store.add(f"arxiv-pdf:{aid}", domain, "arxiv", title, pdf_url, txt, min_tokens=2000)
                        pdf_budget -= 1
                    time.sleep(1.0)  # be polite
        print(f"  [arxiv] '{query[:40]}...' -> store now {len(store)}")
        time.sleep(3.0)  # arXiv asks for ~3s between calls


def _pdf_text(pdf_url: str) -> str:
    try:
        import io
        import pdfplumber
        data = _get(pdf_url, timeout=60)
        out = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages[:60]:
                out.append(page.extract_text() or "")
        return "\n".join(out)
    except Exception as e:
        print(f"    [pdf] failed: {str(e)[:80]}")
        return ""


# ─── Wikipedia ────────────────────────────────────────────────────────────────
def _wiki_extracts(titles, domain, store: CorpusStore):
    import json
    # API allows up to 20 titles per request for extracts.
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        url = ("https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1"
               "&exlimit=max&format=json&redirects=1&titles=" + urllib.parse.quote("|".join(batch)))
        try:
            data = json.loads(_get(url, timeout=40))
        except Exception as e:
            print(f"  [wiki] batch failed: {e}")
            continue
        pages = data.get("query", {}).get("pages", {})
        for pid, page in pages.items():
            title = page.get("title", "")
            extract = page.get("extract", "")
            if extract:
                store.add(f"wiki:{title}", domain, "wikipedia", title,
                          f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}", extract, min_tokens=200)
        time.sleep(0.5)


def _wiki_category_members(category, limit):
    import json
    titles, cont = [], None
    while len(titles) < limit:
        url = ("https://en.wikipedia.org/w/api.php?action=query&list=categorymembers&format=json"
               f"&cmtitle={urllib.parse.quote(category)}&cmlimit={min(limit, 500)}&cmtype=page")
        if cont:
            url += f"&cmcontinue={urllib.parse.quote(cont)}"
        try:
            data = json.loads(_get(url, timeout=40))
        except Exception:
            break
        members = data.get("query", {}).get("categorymembers", [])
        titles += [m["title"] for m in members]
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        time.sleep(0.4)
    return titles[:limit]


def ingest_wikipedia(store: CorpusStore):
    for domain, titles in sources.WIKI_TITLES.items():
        _wiki_extracts(titles, domain, store)
        print(f"  [wiki] curated {domain} -> store now {len(store)}")
    for category, domain, n in sources.WIKI_CATEGORIES:
        titles = _wiki_category_members(category, n)
        _wiki_extracts(titles, domain, store)
        print(f"  [wiki] {category} ({len(titles)} titles) -> store now {len(store)}")


# ─── Framework docs (HTML) ────────────────────────────────────────────────────
def ingest_docs(store: CorpusStore):
    import trafilatura
    for url, domain in sources.DOC_URLS:
        if store.has(f"docs:{url}"):
            continue
        try:
            html = _get(url, timeout=30).decode("utf-8", errors="ignore")
            text = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
            title = url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").title()
            store.add(f"docs:{url}", domain, "docs", title, url, text, min_tokens=150)
        except Exception as e:
            print(f"  [docs] {url} failed: {str(e)[:80]}")
        time.sleep(0.5)
    print(f"  [docs] -> store now {len(store)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1200, help="approx total docs to collect")
    ap.add_argument("--no-pdf", action="store_true", help="skip slow arXiv full-text PDFs")
    ap.add_argument("--per-query", type=int, default=120)
    ap.add_argument("--fulltext-per-query", type=int, default=12)
    ap.add_argument("--only", choices=["docs", "wiki", "arxiv"], default=None,
                    help="run only one source (for targeted backfill)")
    args = ap.parse_args()

    store = CorpusStore()
    print(f"Corpus starts with {len(store)} docs. Target ~{args.target}.")

    if args.only in (None, "docs"):
        ingest_docs(store)
    if args.only in (None, "wiki"):
        ingest_wikipedia(store)
    if args.only in (None, "arxiv") and len(store) < args.target:
        ingest_arxiv(store, args.per_query, args.fulltext_per_query, do_pdf=not args.no_pdf)

    print("\nDONE. Corpus stats:")
    import json
    print(json.dumps(store.stats(), indent=2))


if __name__ == "__main__":
    main()
