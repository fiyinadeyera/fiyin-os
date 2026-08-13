from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import hmac
import hashlib
import requests
import base64

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def sync_file_from_github(repo_full_name, file_path):
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
