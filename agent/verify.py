"""
Checks whether the URLs the agent claims as sources actually exist and respond -- a model can
and does invent plausible-looking URLs, so "the agent gave a source" is not the same as "the
source is real". This never touches content or claims, only reachability: it is not fact-checking,
just filtering out dead/invented links before they're stored as if they were real evidence.
"""

from __future__ import annotations

import urllib.error
import urllib.request

TIMEOUT_SECONDS = 8
USER_AGENT = "Mozilla/5.0 (compatible; GlobalPoliticalCompass/1.0; +source-check)"


def _is_reachable(url: str) -> bool:
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status < 400
    except urllib.error.HTTPError as e:
        if e.code == 405:                    # some servers reject HEAD; a real GET settles it
            return _is_reachable_get(url)
        return e.code < 400
    except Exception:
        return False


def _is_reachable_get(url: str) -> bool:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status < 400
    except Exception:
        return False


def verify_sources(urls: list[str]) -> dict[str, bool]:
    """{url: True/False}. Best-effort and sequential (this is a handful of URLs per entry, not
    a crawl) -- a False doesn't prove the source is fake, only that it didn't answer just now."""
    return {url: _is_reachable(url) for url in urls}
