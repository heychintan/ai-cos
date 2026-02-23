# CoSN Agent Dashboard

Internal content automation tool for the [Chief of Staff Network](https://chiefofstaff.network). Pulls live data from Luma, Spotify, and Webflow, then uses Claude to generate content drafts on demand or on a repeating schedule — downloadable as `.docx` files.

**Live:** [ai-cos.streamlit.app](https://ai-cos.streamlit.app)

---

## How it works

```
Luma API ──┐
Spotify ───┼── Normalizer ── Context Assembler ── Claude API ── .docx download
Webflow ───┘
```

1. Create a task — choose sources, schedule interval, Claude model, and optional template/context files
2. Each source is fetched and normalized into clean plain text
3. Context is assembled and sent to `claude-sonnet-4-6`
4. Output appears in the dashboard and is downloadable as a `.docx` file
5. Tasks repeat automatically on your chosen interval for the duration of the session

---

## Stack

| Layer | Tech |
|---|---|
| App | Python + Streamlit |
| AI | Anthropic Claude (`claude-sonnet-4-6`) |
| Output | `python-docx` |
| Hosting | Streamlit Cloud |

---

## Local development

### 1. Clone & configure

```bash
git clone https://github.com/heychintan/cosn-agent-dashboard.git
cd cosn-agent-dashboard
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501)

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
| `WEBFLOW_JOBS_COLLECTION_ID` | Jobs collection ID in Webflow |
| `WEBFLOW_BLOGS_COLLECTION_ID` | Blog collection ID in Webflow |
| `WEBFLOW_SITE_DOMAIN` | e.g. `cosn.community` |

For Streamlit Cloud, add these under **App settings → Secrets** in TOML format.

---

## Deployment

Deployed on [Streamlit Cloud](https://streamlit.io/cloud). Connect your GitHub repo and add the environment variables above as secrets.

---

## Project structure

```
cosn-agent-dashboard/
├── app.py                        # Main dashboard (task orchestration)
├── scheduler.py                  # In-session scheduling fragment
├── requirements.txt
├── agent/
│   ├── claude.py                 # Claude API call + model list
│   ├── context.py                # Context assembly
│   ├── files.py                  # Template / context doc parsing
│   ├── output.py                 # Output formatting
│   ├── runner.py                 # Task execution
│   ├── task.py                   # Task model + schedule helpers
│   └── sources/                  # Luma, Spotify, Webflow fetchers + normalizers
├── pages/
│   ├── 1_config.py               # API key & source configuration
│   ├── 2_history.py              # In-session run history
│   ├── 3_calendar.py             # Content calendar (month grid)
│   └── 4_task.py                 # Task detail & edit
└── ui/
    ├── styles.py                 # Global CSS injection
    └── components.py             # Shared UI components
```
