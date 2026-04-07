import html
import json
import time
from pathlib import Path
from typing import Optional

import requests

from src.common.config import Config
from src.data.utils import ensure_dir, normalize_title, save_json


def _clean_title(title: str) -> str:
    return html.unescape(title).strip()


def _cache_file_path(title: str, config: Config) -> Path:
    normalized = normalize_title(
        _clean_title(title),
        lowercase=config.lowercase_titles_for_id,
    )
    return config.wiki_cache_dir / f"{normalized}.json"


def _load_cached_doc(title: str, config: Config) -> Optional[dict]:
    cache_path = _cache_file_path(title, config)
    if not cache_path.exists():
        return None

    with open(cache_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_cached_doc(doc: dict, request_title: str, config: Config) -> None:
    ensure_dir(config.wiki_cache_dir)
    cache_path = _cache_file_path(request_title, config)

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def _search_wikipedia_title(title: str, config: Config) -> Optional[str]:
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": _clean_title(title),
        "srwhat": "title",
        "srlimit": 1,
    }

    resp = requests.get(
        config.wiki_api_url,
        params=params,
        timeout=config.wiki_request_timeout,
        headers={"User-Agent": "hover-rag-poc/0.1"},
    )
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    if "application/json" not in content_type.lower():
        return None

    data = resp.json()
    results = data.get("query", {}).get("search", [])
    if not results:
        return None

    return results[0].get("title")


def _fetch_wikipedia_page_uncached(title: str, config: Config, verbose: bool = False) -> Optional[dict]:
    clean_title = _clean_title(title)

    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts|info",
        "inprop": "url",
        "explaintext": True,
        "redirects": 1,
        "titles": clean_title,
    }

    try:
        resp = requests.get(
            config.wiki_api_url,
            params=params,
            timeout=config.wiki_request_timeout,
            headers={"User-Agent": "hover-rag-poc/0.1"},
        )
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            if verbose:
                print(f"[non_json_response] title={clean_title}")
                print(f"status={resp.status_code}, content_type={content_type}")
                print(resp.text[:500])
            return None

        data = resp.json()

        pages = data.get("query", {}).get("pages", {})
        if pages:
            page = next(iter(pages.values()))
            page_id = page.get("pageid", -1)
            page_title = page.get("title")
            extract_text = page.get("extract", "")
            fullurl = page.get("fullurl")

            if page_id != -1 and page_title and extract_text.strip():
                return {
                    "doc_id": page_id,
                    "doc_title": page_title,
                    "normalized_title": normalize_title(
                        page_title,
                        lowercase=config.lowercase_titles_for_id,
                    ),
                    "url": fullurl,
                    "text": [
                        para.strip()
                        for para in extract_text.split("\n")
                        if para.strip()
                    ],
                    "source": "wikipedia_api",
                }

        fallback_title = _search_wikipedia_title(clean_title, config)
        if fallback_title and fallback_title != clean_title:
            if verbose:
                print(f"[fallback] {clean_title} -> {fallback_title}")
            return _fetch_wikipedia_page_uncached(fallback_title, config, verbose=verbose)

        return None

    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"[request_error] title={clean_title} | error={repr(e)}")
        return None
    except ValueError as e:
        if verbose:
            print(f"[json_error] title={clean_title} | error={repr(e)}")
            print(resp.text[:500] if "resp" in locals() else "no response text")
        return None


def fetch_wikipedia_page(title: str, config: Config, verbose: bool = False) -> Optional[dict]:
    """
    Load from local cache first. (local dir: ./data/raw/wiki_cache)
    If missing (or force_refresh=True), fetch from Wikipedia API and cache it.
    """
    if not config.wiki_force_refresh:
        cached = _load_cached_doc(title, config)
        if cached is not None:
            if verbose:
                print(f"[cache_hit] {title}")
            return cached

    if verbose:
        print(f"[cache_miss] {title}")

    doc = _fetch_wikipedia_page_uncached(title, config, verbose=verbose)
    if doc is not None:
        _save_cached_doc(doc, request_title=title, config=config)

    return doc


def match_required_titles_from_wikipedia_api(
    required_titles: list[str],
    config: Config,
    verbose: bool = True,
):
    matched_docs = []
    missing_titles = []

    for raw_title in required_titles:
        doc = fetch_wikipedia_page(raw_title, config, verbose=verbose)
        if doc is None:
            missing_titles.append(raw_title)
        else:
            matched_docs.append(doc)

        time.sleep(config.wiki_sleep_sec)

    return matched_docs, missing_titles


def run_wiki_matching(required_titles: list[str], config: Config):
    matched_docs, missing_titles = match_required_titles_from_wikipedia_api(
        required_titles=required_titles,
        config=config,
        verbose=True,
    )

    payload = {
        "matched_docs": matched_docs,
        "missing_titles": missing_titles,
        "num_required_titles": len(required_titles),
        "num_matched_docs": len(matched_docs),
        "num_missing_titles": len(missing_titles),
    }
    save_json(payload, config.matched_wiki_docs_path)

    return matched_docs, missing_titles