"""In-memory cache with TTL, single-flight fetching, and per-source health tracking."""

import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

_cache = {}
_source_status = {}
CACHE_TTL = 3600

# Single-flight: at most one in-flight fetch per key. Concurrent requests, retries,
# and the background warmer all attach to the running job instead of starting a
# second one. This is what stops duplicate Sieve jobs from burning credits.
_executor = ThreadPoolExecutor(max_workers=4)
_in_flight = {}
_registry_lock = threading.Lock()


def get_cached(source_name):
    key = f"events_{source_name}"
    if key in _cache:
        data, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
    return None


def set_cache(source_name, data):
    key = f"events_{source_name}"
    _cache[key] = (data, time.time())


def record_status(name, count=None, error=None):
    _source_status[name] = {
        "ok": error is None,
        "count": count,
        "error": error,
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_all_status():
    return dict(_source_status)


def _single_flight(key, job):
    """Submit `job` unless one is already running for `key`. Returns the in-flight Future."""
    with _registry_lock:
        fut = _in_flight.get(key)
        if fut is None or fut.done():
            fut = _executor.submit(job)
            _in_flight[key] = fut
        return fut


def _run_and_cache(name, fn):
    try:
        result = fn()
        if result:
            set_cache(name, result)
        record_status(name, count=len(result) if result else 0)
        return result
    except Exception as e:
        record_status(name, error=f"{type(e).__name__}: {e}")
        return []


def fetch_async(name, fn):
    """Ensure a single-flight source fetch for `name` is running. Non-blocking. Returns the Future."""
    return _single_flight(name, lambda: _run_and_cache(name, fn))


def submit(key, job):
    """Run a background side-effect job, single-flight per `key`. Non-blocking. Returns the Future."""
    return _single_flight(key, job)


def get_or_start(name, fn):
    """Return fresh cached data if present. Otherwise kick off a single-flight background
    fetch and return None immediately, so the request never blocks on Sieve."""
    cached = get_cached(name)
    if cached is not None:
        return cached
    fetch_async(name, fn)
    return None
