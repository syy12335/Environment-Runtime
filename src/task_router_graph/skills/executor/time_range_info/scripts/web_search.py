#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

try:
    from defusedxml import ElementTree as SafeElementTree
except Exception:  # pragma: no cover
    from xml.etree import ElementTree as SafeElementTree

MAX_WEB_SEARCH_RESULTS = 5
MAX_WEB_SEARCH_QUERY_CHARS = 120
MAX_WEB_SEARCH_HTTP_BYTES = 120000


def _safe_http_get_text(*, url: str, timeout_sec: float = 10.0, max_bytes: int = MAX_WEB_SEARCH_HTTP_BYTES) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "task-routing-skill-web-search/1.0 (+https://example.local)",
            "Accept": "application/rss+xml, application/xml, text/xml, text/plain, */*",
        },
    )
    with urlopen(request, timeout=timeout_sec) as response:
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    return raw.decode("utf-8", errors="ignore")


def _parse_bing_rss_results(*, xml_text: str, limit: int) -> list[dict[str, str]]:
    try:
        root = SafeElementTree.fromstring(xml_text)
    except Exception:
        return []

    results: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for item in root.findall("./channel/item"):
        title = str(item.findtext("title") or "").strip()
        link = str(item.findtext("link") or "").strip()
        desc = str(item.findtext("description") or "").strip()

        if not link or link in seen_urls:
            continue
        seen_urls.add(link)

        results.append({"title": title, "url": link, "snippet": desc})
        if len(results) >= limit:
            break

    return results


def _main() -> int:
    raw_input = sys.stdin.read().strip()
    if not raw_input:
        print(json.dumps({"error": "input is empty"}, ensure_ascii=False))
        return 0

    try:
        payload = json.loads(raw_input)
    except Exception as exc:
        print(json.dumps({"error": f"input is not valid json: {exc}"}, ensure_ascii=False))
        return 0

    if not isinstance(payload, dict):
        print(json.dumps({"error": "input must be a json object"}, ensure_ascii=False))
        return 0

    query_value = str(payload.get("query", "")).strip()
    if not query_value:
        print(json.dumps({"error": "query is empty"}, ensure_ascii=False))
        return 0

    if len(query_value) > MAX_WEB_SEARCH_QUERY_CHARS:
        print(
            json.dumps(
                {
                    "error": (
                        f"query is too long (>{MAX_WEB_SEARCH_QUERY_CHARS}). "
                        "Please use a concise and specific query."
                    )
                },
                ensure_ascii=False,
            )
        )
        return 0

    try:
        limit_value = int(payload.get("limit", 3))
    except Exception:
        limit_value = 3
    limit_value = max(1, min(MAX_WEB_SEARCH_RESULTS, limit_value))

    rss_url = f"https://www.bing.com/search?q={quote_plus(query_value)}&format=rss"

    try:
        xml_text = _safe_http_get_text(url=rss_url)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "query": query_value,
                    "count": 0,
                    "results": [],
                    "error": f"web search request failed: {exc}",
                },
                ensure_ascii=False,
            )
        )
        return 0

    results = _parse_bing_rss_results(xml_text=xml_text, limit=limit_value)
    output: dict[str, object] = {
        "query": query_value,
        "count": len(results),
        "results": results,
        "engine": "bing_rss",
        "usage_note": "web_search 开销较高且结果噪声较大，仅在必须依赖外部时效信息时使用",
    }
    if not results:
        output["hint"] = "no results found; try a more specific query"

    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
