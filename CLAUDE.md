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
5. Agent (In progress) - not linked
6. Risk (In progress) - not linked

This order is a deliberate editorial decision. Do not reorder without asking.

### What this is not

- Not a portfolio site. That's fiyinadeyera.com.
- Not a standalone app. It's a hub that hosts other apps.

## Architecture

| File | Responsibility |
|---|---|
| `app.py` | Flask routes, template rendering, and GitHub webhook. Hub only, no business logic. |
| `templates/base.html` | Shared layout: nav bar, Tailwind, Satoshi font, dark slate theme. |
| `templates/index.html` | Homepage with project cards. |
| `templates/*.html` | Individual project pages (signalrank, agent, risk, events, lunch). |
| `static/` | Static files including subway.html. |

### Key technical decisions

- Tailwind CSS via CDN (`cdn.tailwindcss.com`)
- Satoshi font via Fontshare
- Dark slate theme (bg-slate-950, text-slate-100)
- GitHub webhook for auto-deploying file changes on push
- SignalRank lives in its own repo (fiyinadeyera/SignalRank). The /signalrank route here renders the template, but the /api/optimize endpoint needs to point to the standalone SignalRank deployment once it's live on Render.

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

- `.env` contains GitHub webhook secret and GitHub token
