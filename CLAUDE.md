# fiyin.org (fiyin-os)

## Product

Fiyin's AI projects hub. A single Flask app that hosts all projects as routes. This is the front door to everything Fiyin builds.

### Requirements

- Homepage lists all projects as cards with name, tagline, and status badge
- Each project is either a Flask route (renders a template) or a static file served via `send_from_directory`
- Projects with "Live" badge are functional. "In progress" projects are greyed out and not clickable.
- Only SignalRank and MyRAG have the Live badge. Other projects do not.

### Current project order on homepage

1. SignalRank (Live) - /signalrank
2. Subway Map - /subway
3. MyRAG (Live) - external link to myrag-o7eu.onrender.com
4. Lunch Specials - /lunch
5. SidelineReel - external link to sidelinereel-coach-review.onrender.com
6. Agent (In progress) - not linked
7. Risk (In progress) - not linked
8. Orbit (In progress) - not linked

This order is a deliberate editorial decision. Do not reorder without asking.

### What this is not

- Not a portfolio site. That's fiyinadeyera.com.
- Not a standalone app. It's a hub that hosts other apps.

## Architecture

| File | Responsibility |
|---|---|
| `app.py` | Flask routes, SignalRank API (/api/optimize, /api/status), GitHub webhook, background cache warming. |
| `cache.py` | In-memory cache with 1-hour TTL and per-source health tracking. |
| `sources.py` | Event fetchers (Sieve, Ticketmaster, NYC Open Data, sample events). |
| `sieve.py` | Sieve API client for web extraction (events and host profiles). |
| `ranking.py` | Claude prompt building and event ranking. Returns JSON array of scored events. |
| `filters.py` | Date range calculation and event filtering. |
| `enrichment.py` | Host/speaker profile lookup via Google search through Sieve. |
| `templates/base.html` | Shared layout: nav bar, Tailwind, Satoshi font, dark slate theme. |
| `templates/index.html` | Homepage with project cards. |
| `templates/*.html` | Individual project pages (signalrank, agent, risk, events, lunch). |
| `static/` | Static files including subway.html. |

### Key technical decisions

- Tailwind CSS via CDN (`cdn.tailwindcss.com`)
- Satoshi font via Fontshare
- Dark slate theme (bg-slate-950, text-slate-100)
- GitHub webhook for auto-deploying file changes on push
- SignalRank's modular backend code lives in this repo (not deployed separately). The SignalRank repo is the reference, but fiyin-os is what runs at fiyin.org.
- API request timeout capped at 25 seconds (Render kills at 30s).
- Background thread warms event cache every 55 minutes.

## Design system

- **Background:** slate-950 with subtle blue radial gradient at top
- **Font:** Satoshi (400, 500, 700, 900)
- **Cards:** rounded-xl, border-slate-800, bg-slate-900/40, hover transitions
- **Live badge:** emerald-500 tones, rounded-full, 10px text
- **In progress badge:** slate-800 tones, greyed out, opacity-50, cursor-default
- **Icons:** 8x8 rounded-lg containers with colored SVG icons
- **Nav:** Fixed top bar, backdrop-blur, border-b border-slate-800/60
- **Max width:** 2xl (672px) content area, centered

## Deployment

- Render (fiyin.org)
- Auto-deploys on push to main (~75s)
- DNS: fiyin.org CNAMEs to fiyin-os.onrender.com

## Coding conventions

- No God modules. Each file has one responsibility.
- No unused CSS.
- No em dashes.
- No invented copy. If Fiyin didn't write it, don't publish it.
- No job-seeking language anywhere.

## Secrets (never commit)

- `.env` contains API keys (Anthropic, Sieve, Ticketmaster, GitHub webhook secret, GitHub token)
