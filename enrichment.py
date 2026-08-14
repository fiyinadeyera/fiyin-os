"""Enrich events with host/speaker profiles via Sieve. Cached and single-flight."""

import hashlib
import time
import urllib.parse

import cache
import sieve


PROFILE_INSTRUCTION = (
    "For each search results page, extract the person's name, current job title, "
    "current company, and a one-line professional summary from whatever profile "
    "or bio you find (LinkedIn, personal website, company page, etc.). "
    "If no relevant result is found, return just their name with empty fields."
)

# Host profiles are slow-changing and each lookup costs Sieve credits, so cache
# them for a day. An empty string is a negative result: looked up, none found,
# don't look again until it expires.
_PROFILE_TTL = 24 * 3600
_profiles = {}  # name.lower() -> (bio, timestamp)


def _build_search_urls(names):
    urls = []
    for name in names:
        q = urllib.parse.quote_plus(f"{name} linkedin OR bio OR about")
        urls.append(f"https://www.google.com/search?q={q}")
    return urls


def lookup_profiles(names):
    if not names or not sieve.API_KEY:
        return {}

    urls = _build_search_urls(names)

    try:
        session_id = sieve.start_extraction(
            urls=urls,
            instruction=PROFILE_INSTRUCTION,
        )
        result = sieve.poll_result(session_id)
    except Exception:
        return {}

    if not result:
        return {}

    profiles = {}
    raw = result.get("result", [])
    if not isinstance(raw, list):
        return {}

    for profile in raw:
        if not profile or not profile.get("name"):
            continue
        name = profile["name"]
        title = profile.get("title", "")
        company = profile.get("company", "")
        summary = profile.get("summary", "")
        bio = ""
        if title and company:
            bio = f"{title} at {company}"
        elif title:
            bio = title
        if summary:
            bio = f"{bio}. {summary}" if bio else summary
        if bio:
            profiles[name.lower()] = bio

    return profiles


def _is_fresh(name):
    hit = _profiles.get(name.lower())
    return hit is not None and time.time() - hit[1] < _PROFILE_TTL


def _cached_bio(name):
    hit = _profiles.get(name.lower())
    if hit and time.time() - hit[1] < _PROFILE_TTL:
        return hit[0]
    return None


def _fetch_and_store(names):
    """Background job: look up profiles once and cache both hits and misses."""
    found = lookup_profiles(names)
    now = time.time()
    for key, bio in found.items():
        _profiles[key] = (bio, now)
    for name in names:
        key = name.lower()
        if key not in _profiles or now - _profiles[key][1] >= _PROFILE_TTL:
            _profiles[key] = ("", now)


def enrich_events(events):
    all_hosts = set()
    for ev in events:
        for name in ev.get("hosts", []):
            if name and len(name.strip()) > 2:
                all_hosts.add(name.strip())

    if not all_hosts:
        return events

    # Kick off one background Sieve lookup for any hosts we don't have cached.
    # Single-flight keyed on the host set means retries of the same search share
    # the running job instead of starting another one.
    missing = sorted(n for n in all_hosts if not _is_fresh(n))
    if missing:
        digest = hashlib.sha1("|".join(missing).encode()).hexdigest()[:12]
        cache.submit(f"enrich:{digest}", lambda: _fetch_and_store(missing[:15]))

    # Attach whatever profiles are already cached. Anything still pending shows up
    # on a later request once the background lookup has populated the cache.
    for ev in events:
        host_bios = []
        for name in ev.get("hosts", []):
            bio = _cached_bio(name)
            if bio:
                host_bios.append(f"{name}: {bio}")
            elif name:
                host_bios.append(name)
        if host_bios:
            ev["host_info"] = "; ".join(host_bios)

    return events
