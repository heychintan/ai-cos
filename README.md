# CoSN Agent Dashboard

Internal content automation tool for the [Chief of Staff Network](https://chiefofstaff.network). Pulls live data from Luma, Spotify, and Webflow CMS, then uses Claude to generate a formatted weekly newsletter draft — downloaded as a `.docx` file.

---

## How it works

```
Luma API ──┐
Spotify ───┼── Normalizer ── Context Assembler ── Claude API ── .docx download
Webflow ───┘
```

1. Fetches upcoming events (Luma), recent podcast episodes (Spotify), and recent blog posts (Webflow)
2. Normalizes each source into clean plain text
3. Assembles context + template and calls `claude-sonnet-4-6`
4. Returns a formatted `.docx` file that auto-downloads in the browser

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 15 + Tailwind |
| Backend | Python FastAPI + Uvicorn |
| AI | Anthropic Claude (`claude-sonnet-4-6`) |
| Output | `python-docx` |
| Hosting | Vercel (frontend) + Railway (backend) |

---

## Local development

### 1. Clone & configure

```bash
git clone https://github.com/heychintan/cosn-agent-dashboard.git
cd cosn-agent-dashboard
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Environment variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `LUMA_API_KEY` | Luma calendar API key |
| `SPOTIFY_CLIENT_ID` | Spotify app client ID |
| `SPOTIFY_CLIENT_SECRET` | Spotify app client secret |
| `SPOTIFY_SHOW_ID` | Podcast show ID from Spotify URL |
| `WEBFLOW_API_KEY` | Webflow API key |
| `WEBFLOW_COLLECTION_ID` | Blog collection ID in Webflow |
| `WEBFLOW_SITE_DOMAIN` | e.g. `chiefofstaff.webflow.io` |

---

## Deployment

- **Frontend** — Vercel. Set `NEXT_PUBLIC_API_URL` to your Railway backend URL.
- **Backend** — Railway. Add all env vars from the table above.

---

## Project structure

```
cosn-agent-dashboard/
├── backend/
│   ├── main.py                  # FastAPI routes
│   ├── agent.py                 # Claude API call
│   ├── fetchers/                # Luma, Spotify, Webflow API clients
│   ├── normalizers/             # Per-source text normalizers + assembler
│   ├── output/docx_writer.py   # .docx generation
│   └── requirements.txt
├── frontend/
│   └── app/
│       ├── page.tsx             # Automations page (Run Now)
│       └── integrations/        # API connection tester
└── .env.example
```

---

## POC scope

- [x] Single automation: Weekly Newsletter
- [x] Three data sources: Luma, Spotify, Webflow
- [x] On-demand trigger
- [x] `.docx` auto-download
- [ ] Scheduling (Phase 1)
- [ ] Auth (Phase 1)
- [ ] Run history (Phase 1)
- [ ] LinkedIn / Slack push (Phase 2)
