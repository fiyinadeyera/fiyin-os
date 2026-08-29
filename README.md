# fiyin.org

This repository powers [fiyin.org](https://fiyin.org), Fiyin's hub for AI projects, prototypes, and experiments. It is a single Flask app: the home page presents the projects, and each project is either a Flask route, a static page, or an external app.

## Projects

The home page currently lists:

| Project | Status | Route |
| --- | --- | --- |
| SignalRank | Live | `/signalrank` |
| Subway Map | Available | `/subway` |
| MyRAG | Live | External Render app |
| Lunch Specials | Available | `/lunch` |
| Agent | In progress | Not linked from the home page |
| Risk | In progress | Not linked from the home page |

SignalRank ranks upcoming New York events against a user's goals. Its backend pulls events from Sieve and Ticketmaster, caches source results for one hour, enriches host information, and uses Claude to rank the results. If live sources are unavailable, the page falls back to sample events.

## Project structure

- `app.py` - Flask routes, SignalRank API, GitHub webhook, and background cache warming
- `cache.py` - in-memory event cache and source health tracking
- `sources.py` - Sieve and Ticketmaster event sources
- `sieve.py` - Sieve extraction client
- `ranking.py` - Claude prompt and ranking logic
- `filters.py` - event date filtering
- `enrichment.py` - host and speaker enrichment
- `templates/` - the hub and project pages
- `static/` - static assets, including the subway map

## Local setup

This project requires Python 3 and the packages in `requirements.txt`.

```bash
git clone https://github.com/fiyinadeyera/fiyin-os.git
cd fiyin-os
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file for the services you want to use:

```dotenv
ANTHROPIC_API_KEY=
SIEVE_API_KEY=
TICKETMASTER_API_KEY=
GITHUB_WEBHOOK_SECRET=
GITHUB_TOKEN=
```

`ANTHROPIC_API_KEY`, `SIEVE_API_KEY`, and `TICKETMASTER_API_KEY` support SignalRank's live ranking flow. The GitHub variables are used only by the project-sync webhook described below.

Start the development server:

```bash
python app.py
```

The app listens on `http://localhost:5000`.

## Deployment

The production app runs on Render at `fiyin-os.onrender.com`, with `fiyin.org` pointing to it. Render auto-deploys pushes to `main`.

A production start command can use Gunicorn:

```bash
gunicorn app:app
```

Set the required environment variables in Render rather than committing a `.env` file.

## Project sync

`POST /github-webhook` supports syncing changed files from a pushed GitHub repository into the running app:

1. Configure a GitHub push webhook whose payload URL is `https://fiyin.org/github-webhook`.
2. Set the same secret in GitHub and in `GITHUB_WEBHOOK_SECRET` on Render.
3. Optionally set `GITHUB_TOKEN` so the app can read private repositories or avoid unauthenticated API limits.
4. When GitHub sends a `push` event, the app verifies the `X-Hub-Signature-256` signature, reads the added and modified file paths from the commits, and downloads those files from the source repository through the GitHub Contents API.

The webhook does not process deleted files. Keep Render's normal `main` branch auto-deploy enabled for changes made directly in this repository.
