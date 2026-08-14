import os
import hmac
import hashlib
import base64
import threading
import time

from flask import Flask, render_template, request, jsonify, send_from_directory

import cache
import sources
import ranking
import filters
import enrichment

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def sync_file_from_github(repo_full_name, file_path):
    import requests
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    r = requests.get(
        f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}",
        headers=headers,
        timeout=10
    )
    if r.status_code != 200:
        return False, r.status_code
    content = base64.b64decode(r.json()["content"])
    dest = os.path.join(BASE_DIR, file_path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(content)
    return True, None


@app.route("/github-webhook", methods=["POST"])
def github_webhook():
    sig = request.headers.get("X-Hub-Signature-256", "")
    body = request.get_data()
    if WEBHOOK_SECRET:
        expected = "sha256=" + hmac.new(
            WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return jsonify({"error": "Invalid signature"}), 403

    event = request.headers.get("X-GitHub-Event", "")
    if event != "push":
        return jsonify({"status": "ignored"}), 200

    payload = request.get_json(force=True) or {}
    commits = payload.get("commits", [])
    repo = payload.get("repository", {}).get("full_name", "")

    changed = set()
    for commit in commits:
        for f in commit.get("added", []) + commit.get("modified", []):
            changed.add(f)

    synced, failed = [], []
    for file_path in changed:
        ok, err = sync_file_from_github(repo, file_path)
        (synced if ok else failed).append(file_path)

    return jsonify({"status": "synced", "synced": synced, "failed": failed}), 200


@app.route("/")
def index():
    return render_template("index.html", page="home")

@app.route("/signalrank")
def signalrank():
    return render_template("signalrank.html", page="signalrank")

@app.route("/subway")
def subway():
    return send_from_directory(os.path.join(BASE_DIR, "static"), "subway.html")

@app.route("/agent")
def agent():
    return render_template("agent.html", page="agent")

@app.route("/risk")
def risk():
    return render_template("risk.html", page="risk")

@app.route("/events")
def events():
    return render_template("events.html", page="events")

@app.route("/lunch")
def lunch():
    return render_template("lunch.html", page="lunch")


@app.route("/api/status")
def api_status():
    return jsonify(cache.get_all_status())


@app.route("/api/optimize", methods=["POST"])
def optimize():
    data = request.json
    goals = data.get("goals", "")
    date_filter = data.get("dateFilter", "this-week")

    if not goals:
        return jsonify({"error": "Please enter your goals"}), 400

    # Non-blocking: return whatever is cached now and let any needed fetch run in
    # the background (single-flight). The request never waits on Sieve, so it can't
    # be killed at Render's 30s limit and retried into a duplicate job.
    all_events = []
    for name, fn in sources.SOURCES:
        data = cache.get_or_start(name, fn)
        if data:
            all_events.extend(data)

    if not all_events:
        all_events = sources.build_sample_events()
        is_live = False
    else:
        is_live = True
        start_date, end_date = filters.get_date_range(date_filter)
        all_events = filters.filter_by_date(all_events, start_date, end_date)

        if not all_events:
            all_events = sources.build_sample_events()
            is_live = False

    all_events = enrichment.enrich_events(all_events)

    try:
        ranked = ranking.rank_events(all_events, goals)
        return jsonify({
            "success": True,
            "ranking": ranked,
            "events": all_events,
            "is_live": is_live,
            "event_count": len(all_events),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _warm_cache():
    # Force a refresh (single-flight) so the cache is repopulated before its TTL
    # expires and users keep hitting warm data instead of triggering fresh jobs.
    for name, fn in sources.SOURCES:
        try:
            cache.fetch_async(name, fn).result(timeout=130)
        except Exception:
            pass

    # Pre-warm host enrichment from the cached events so the first user search
    # doesn't trigger the (uncached, slow) Sieve profile lookup itself.
    warmed = []
    for name, _fn in sources.SOURCES:
        cached = cache.get_cached(name)
        if cached:
            warmed.extend(cached)
    if warmed:
        enrichment.enrich_events(warmed)


def _cache_refresh_loop():
    _warm_cache()
    while True:
        time.sleep(55 * 60)
        _warm_cache()


_bg_thread = threading.Thread(target=_cache_refresh_loop, daemon=True)
_bg_thread.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
