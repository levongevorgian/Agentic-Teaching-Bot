from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request


FALLBACK_RESOURCES = [
    {
        "title": "Stanford CS224N Natural Language Processing",
        "url": "https://web.stanford.edu/class/cs224n/",
        "snippet": "Course materials useful for modern NLP concepts, neural models, and assignments.",
    },
    {
        "title": "Hugging Face NLP Course",
        "url": "https://huggingface.co/learn/nlp-course/",
        "snippet": "Practical explanations and examples for transformers, tokenizers, and NLP workflows.",
    },
    {
        "title": "Speech and Language Processing",
        "url": "https://web.stanford.edu/~jurafsky/slp3/",
        "snippet": "Draft textbook chapters covering core NLP foundations and advanced topics.",
    },
]


def search_web(query: str, limit: int = 3) -> list[dict[str, str]]:
    """Return compact resource records. Avoids fake references by falling back to known URLs."""
    backend = os.getenv("SEARCH_BACKEND", "duckduckgo").lower()
    if backend == "off":
        return FALLBACK_RESOURCES[:limit]
    try:
        results = _duckduckgo(query, limit)
        return results or FALLBACK_RESOURCES[:limit]
    except Exception:
        return FALLBACK_RESOURCES[:limit]


def _duckduckgo(query: str, limit: int) -> list[dict[str, str]]:
    timeout = float(os.getenv("SEARCH_TIMEOUT_SECONDS", "10"))
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        html = response.read().decode("utf-8", errors="ignore")

    results: list[dict[str, str]] = []
    pattern = re.compile(
        r'<a rel="nofollow" class="result__a" href="(?P<href>.*?)".*?>(?P<title>.*?)</a>.*?'
        r'<a class="result__snippet".*?>(?P<snippet>.*?)</a>',
        re.S,
    )
    for match in pattern.finditer(html):
        href = _clean_url(_strip_tags(match.group("href")))
        title = _strip_tags(match.group("title"))
        snippet = _strip_tags(match.group("snippet"))
        if href and title:
            results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= limit:
            break
    return results


def _clean_url(url: str) -> str:
    url = urllib.parse.unquote(url)
    parsed = urllib.parse.urlparse(url)
    if "duckduckgo.com" in parsed.netloc:
        qs = urllib.parse.parse_qs(parsed.query)
        if "uddg" in qs:
            return qs["uddg"][0]
    return url


def _strip_tags(value: str) -> str:
    value = re.sub(r"<.*?>", " ", value)
    value = value.replace("&amp;", "&").replace("&quot;", '"').replace("&#x27;", "'")
    return re.sub(r"\s+", " ", value).strip()


def resources_to_markdown(resources: list[dict[str, str]]) -> str:
    return "\n".join(
        f"- {json.dumps(item['title'])[1:-1]}: {item['url']} ({item['snippet']})"
        for item in resources
    )

