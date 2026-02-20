# CoSN Agent Orchestration Dashboard
## Technical Product Requirements Document
### Streamlit POC Edition — v0.2 | February 2026 | Confidential

---

| | |
|---|---|
| **Project** | CoSN Agent Orchestration Dashboard |
| **Version** | v0.2 — Streamlit POC |
| **Date** | February 2026 |
| **Status** | Draft — Confidential |

---

## △ What Changed from v0.1

This revision supersedes the original PRD (v0.1) which specified a Next.js + FastAPI + Supabase stack. The POC is now fully implemented as a single-file Streamlit application. The core automation logic, Claude integration, and .docx output are unchanged; only the delivery mechanism is simplified.

| Concern | v0.1 (Original) | v0.2 (This Document) |
|---|---|---|
| Frontend | Next.js (React) | Streamlit (Python) |
| Backend / API | FastAPI (separate service) | Streamlit session (same process) |
| Database | Supabase (Postgres + Storage) | None — session state only |
| File storage | Supabase Storage (template uploads) | In-session file uploads (`st.file_uploader`) |
| Hosting | Vercel + Railway / Render | Streamlit Community Cloud or any Python host |
| Scheduling / cron | Future scope | Removed from POC scope |
| Auth / key management | Env vars + Supabase RLS (future) | Env vars / sidebar input for POC |

---

## 1. Overview & Goals

The Chief of Staff Network (CoSN) is a professional community for Chiefs of Staff, operators, and aspiring CoS professionals at tech companies. Content operations today are largely manual: community managers must pull information from multiple disconnected sources and hand-craft posts, newsletters, and outreach emails.

This document specifies a Streamlit-based Proof of Concept that validates the complete automation pipeline before investing in a production-grade web application. The POC must:

- Connect to live data sources via API (Luma Events, Spotify Podcast, Webflow CMS Blog)
- Accept session-uploaded context files (DOCX, TXT, MD) as supplementary input
- Normalize and consolidate fetched + uploaded data into clean Claude context
- Invoke the Claude API to generate content against a user-provided template
- Output a formatted, downloadable `.docx` newsletter draft

**Success criteria:** Scott and the CoSN team can run the weekly newsletter automation end-to-end without engineering involvement, using the Streamlit UI on a laptop.

---

## 2. Architecture

### 2.1 Single-Process Model

Streamlit runs everything in one Python process. There is no separate backend service. Each user session is isolated; state is held in `st.session_state` and disappears when the browser tab is closed. No data is written to disk or a database.

| Layer | Responsibility | Streamlit Mechanism |
|---|---|---|
| UI / Config | Collect API keys, source params, template file, context docs | `st.sidebar` + `st.form` |
| Data Fetch | Call Luma / Spotify / Webflow APIs in parallel | `asyncio.gather` → `st.cache_data` (TTL 5 min) |
| Normalizer | Transform raw JSON → clean plain-text context per source | Pure Python functions |
| Context Assembly | Merge normalized data + uploaded file contents | String concatenation → `st.session_state` |
| AI Generation | POST to Claude API with assembled context | `anthropic` SDK → streaming response |
| Output | Render preview + generate downloadable `.docx` | `st.download_button` + `python-docx` |

### 2.2 Data Flow

1. User fills sidebar: API keys, date params, selects sources
2. User uploads template file and optional context docs (DOCX / TXT / MD)
3. Clicks **"Run Automation"** — triggers data fetch
4. API calls run in parallel (`asyncio`); raw responses cached for 5 minutes
5. Normalizer functions produce clean text blocks per source
6. Uploaded file text is extracted and appended to context
7. Context string assembled: `[Sources] + [Uploaded Docs] + [Template] + [Task Instruction]`
8. Claude API called with streaming; output streams into `st.empty()` placeholder
9. On completion, `.docx` generated in memory and offered as `st.download_button`

---

## 3. Technology Stack

| Package | Version | Purpose |
|---|---|---|
| `streamlit` | >= 1.32 | UI framework |
| `anthropic` | >= 0.25 | Claude API SDK |
| `httpx` | >= 0.27 | Async HTTP client for external APIs |
| `python-docx` | >= 1.1 | Generate `.docx` output |
| `mammoth` | >= 1.7 | Extract text from uploaded `.docx` context files |
| `python-dotenv` | >= 1.0 | Load `.env` for local development |
| `asyncio` (stdlib) | — | Parallel API calls |
| `python` | >= 3.11 | Runtime |

### requirements.txt

```
streamlit>=1.32
anthropic>=0.25
httpx>=0.27
python-docx>=1.1
mammoth>=1.7
python-dotenv>=1.0
```

---

## 4. UI Design — Stripe Design Language

The Streamlit app should feel like a Stripe internal tool: clean, monochromatic, data-forward, with subtle borders and generous whitespace. Typography is Inter (loaded via `st.markdown` + Google Fonts). The primary accent color is Stripe Indigo `#635BFF`.

### 4.1 Design Tokens

| Token | Hex | Usage |
|---|---|---|
| `stripe-indigo` | `#635BFF` | Primary CTAs, active states, links, progress |
| `stripe-indigo-dark` | `#4B44CC` | Hover states |
| `ink-black` | `#0A2540` | Page titles, strong labels |
| `slate` | `#425466` | Body text, descriptions |
| `slate-light` | `#6B7C93` | Captions, meta labels, placeholders |
| `border-gray` | `#E3E8EF` | Card borders, dividers, input borders |
| `surface-gray` | `#F6F9FC` | Card backgrounds, sidebar bg, input fill |
| `surface-dark-gray` | `#EEF2F7` | Table header rows, hover rows |
| `white` | `#FFFFFF` | Page background, card interiors |
| `green` | `#09825D` | Success badge, status: completed |
| `red` | `#C0392B` | Error badge, status: failed |

### 4.2 Custom CSS (injected via `st.markdown`)

The following CSS is injected once at app startup to override Streamlit defaults and apply the Stripe aesthetic:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: Inter, sans-serif !important; }

/* Page background */
.stApp { background-color: #FFFFFF; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #F6F9FC;
    border-right: 1px solid #E3E8EF;
}

/* Primary button — Stripe indigo */
.stButton > button[kind="primary"] {
    background: #635BFF;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    letter-spacing: -0.01em;
}
.stButton > button[kind="primary"]:hover {
    background: #4B44CC;
}

/* Cards */
.cos-card {
    border: 1px solid #E3E8EF;
    border-radius: 8px;
    padding: 20px 24px;
    background: #FFFFFF;
    margin-bottom: 16px;
}

/* Status badges */
.badge-success { color: #09825D; font-weight: 600; font-size: 0.8rem; }
.badge-error   { color: #C0392B; font-weight: 600; font-size: 0.8rem; }
.badge-idle    { color: #6B7C93; font-weight: 600; font-size: 0.8rem; }

/* Step indicator */
.step-active { color: #635BFF; font-weight: 600; }
.step-done   { color: #09825D; }
.step-idle   { color: #6B7C93; }
```

### 4.3 Page Layout

| Region | Width | Content |
|---|---|---|
| Sidebar | 320px | API keys (password inputs), source toggles, date-range params, file uploaders |
| Main — Header | Full | CoSN wordmark + page title + run status badge |
| Main — Source Cards | 3-col grid | Luma / Spotify / Webflow — each shows toggle, params, last-fetch status |
| Main — Context Docs | Full | Uploaded file chips; expandable preview |
| Main — Run Bar | Full | "Run Automation" CTA + step indicators |
| Main — Preview | Full | Generated text in `st.expander` with copy button |
| Main — Download | Full | `st.download_button` for `.docx` output |

### 4.4 Pages (Streamlit Multi-Page)

| Page | File | Purpose |
|---|---|---|
| 🏠 Dashboard | `app.py` (default) | Run automations, view output, download `.docx` |
| ⚙️ Configuration | `pages/1_config.py` | Persistent config via `st.secrets` / env vars; template management |
| 📋 Run History | `pages/2_history.py` | In-session log of run results (cleared on page reload) |

---

## 5. Data Sources & Normalizers

### 5.1 Luma — Events

| | |
|---|---|
| **Endpoint** | `GET https://api.lu.ma/v1/calendar/list-events` |
| **Auth** | Header: `x-luma-api-key: <LUMA_API_KEY>` |
| **Calendar ID** | `cal-9Z75SHNwmRJPyWb` |
| **Key fields** | `title`, `start_at`, `end_at`, `url`, `description`, `geo_address_info` |
| **Default filter** | Events in the next 21 days (configurable via sidebar slider) |

Normalizer output format:

```
UPCOMING EVENTS (next {n} days)
1. [Event Title] — [Date, Time] | [City / Online]
   [First 200 chars of description]
   Register: [url]
```

### 5.2 Spotify — Podcast Episodes

| | |
|---|---|
| **Endpoint** | `GET https://api.spotify.com/v1/shows/{show_id}/episodes` |
| **Auth** | Bearer token (Client Credentials flow via `SPOTIFY_CLIENT_ID` + `SECRET`) |
| **Show ID** | `0mroNmOfEqWdkPEYYtN3PF` |
| **Key fields** | `name`, `description`, `release_date`, `duration_ms`, `external_urls.spotify` |
| **Default filter** | Episodes released in the last 7 days (configurable) |

Normalizer output format:

```
RECENT PODCAST EPISODES (last {n} days)
1. [Episode Title] — Released [Date] | [Duration in mins]
   [First 200 chars of description]
   Listen: [spotify url]
```

### 5.3 Webflow CMS — Blog Posts

| | |
|---|---|
| **Endpoint** | `GET https://api.webflow.com/v2/collections/{collection_id}/items` |
| **Auth** | Bearer token (`WEBFLOW_API_KEY`) |
| **Collection ID** | Discovered at runtime: `GET /v2/sites` → `GET /v2/collections` |
| **Key fields** | `name`, `slug`, `fieldData.publish-date`, `fieldData.summary` |
| **Default filter** | Posts published in the last 7 days (configurable) |

Normalizer output format:

```
RECENT BLOG POSTS (last {n} days)
1. [Post Title] — Published [Date]
   [Summary or first 200 chars]
   Read: https://[site-domain]/blog/[slug]
```

### 5.4 Session-Uploaded Context Files

Users may upload one or more files via `st.file_uploader` (accepts `.docx`, `.txt`, `.md`). Text content is extracted in-session and appended to the Claude context. No files are stored anywhere.

| File type | Extraction method | Notes |
|---|---|---|
| `.txt` / `.md` | `file.read().decode("utf-8")` | Direct text read |
| `.docx` | `mammoth.extract_raw_text(file)` | Strips formatting, plain text only |

---

## 6. Claude API Integration

### 6.1 Model

Use `claude-sonnet-4-6` for the POC. Upgrade to `claude-opus-4-6` if output quality needs improvement. Both models are configurable via a sidebar selectbox.

### 6.2 Context Assembly

```
=== DATA CONTEXT ===
{normalized_luma_output}

{normalized_spotify_output}

{normalized_webflow_output}

=== UPLOADED DOCUMENTS ===
{extracted_text_from_each_uploaded_file}

=== TEMPLATE & INSTRUCTIONS ===
{template_file_contents}

=== YOUR TASK ===
Using the data above and following the template exactly, generate the
newsletter draft. Output should be ready to copy into the final document
with no further editing needed.
```

### 6.3 System Prompt

```
You are a professional content writer for the Chief of Staff Network (CoSN),
a community for Chiefs of Staff and operators at tech companies. Your writing
is professional but warm, direct, and community-focused.

Rules:
- Never fabricate events, links, dates, or statistics.
- If data is missing, note it with [MISSING: description] rather than inventing.
- Follow the provided template structure exactly.
- Do not add sections that are not in the template.
- Write in second person for calls-to-action ("join us", "register now").
```

### 6.4 Streaming

```python
with client.messages.stream(
    model=selected_model,
    max_tokens=4096,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": context}]
) as stream:
    placeholder = st.empty()
    full_text = ""
    for chunk in stream.text_stream:
        full_text += chunk
        placeholder.markdown(full_text)
    st.session_state["last_output"] = full_text
```

### 6.5 API Key Management

For local development, keys are loaded from a `.env` file via `python-dotenv`. For Streamlit Cloud deployment, keys are stored in `st.secrets` (TOML-based secrets management). The sidebar exposes password-type input fields as a fallback override for demo/testing sessions.

| Key | Env var / Secret | Sidebar fallback? |
|---|---|---|
| Anthropic / Claude | `ANTHROPIC_API_KEY` | Yes |
| Luma | `LUMA_API_KEY` | Yes |
| Spotify Client ID | `SPOTIFY_CLIENT_ID` | Yes |
| Spotify Client Secret | `SPOTIFY_CLIENT_SECRET` | Yes |
| Webflow | `WEBFLOW_API_KEY` | Yes |

---

## 7. Output — .docx Generation

The Claude response is written into a `.docx` file in memory using `python-docx`. The file is never saved to disk; it is returned as bytes and offered to the user via `st.download_button`. No cloud storage or database is required.

### 7.1 Document Structure

- Document title: `"CoSN Newsletter Draft — [Week of Date]"`
- Sections derived from template headings (parsed from uploaded template file)
- Claude-generated content under each heading
- Footer: `"Generated by CoSN Agent Dashboard on [datetime] via Claude [model]"`

### 7.2 Download Flow

1. User clicks **"Run Automation"** — step indicator shows: `Fetching → Generating → Done`
2. Streaming output renders in `st.empty()` placeholder in real time
3. On stream completion, `python-docx` writes formatted `.docx` to `io.BytesIO`
4. `st.download_button` appears with filename `CoSN_Newsletter_[YYYY-MM-DD].docx`
5. User clicks download — file transferred directly to browser; nothing stored server-side

---

## 8. Repository & File Structure

```
cosn-agent-dashboard/
├── app.py                    # Main Streamlit entry point (Dashboard page)
├── pages/
│   ├── 1_config.py           # Configuration page
│   └── 2_history.py          # Run history page (in-session)
├── agent/
│   ├── __init__.py
│   ├── sources/
│   │   ├── luma.py           # Luma API fetch + normalizer
│   │   ├── spotify.py        # Spotify API fetch + normalizer
│   │   └── webflow.py        # Webflow CMS fetch + normalizer
│   ├── files.py              # Uploaded file text extraction
│   ├── context.py            # Context assembly
│   ├── claude.py             # Claude API call + streaming
│   └── output.py             # .docx generation via python-docx
├── ui/
│   ├── styles.py             # CSS injection (Stripe theme)
│   └── components.py         # Reusable st.markdown card/badge helpers
├── .env.example              # Template env file
├── requirements.txt
└── README.md
```

---

## 9. Non-Functional Requirements

| Requirement | Target | Notes |
|---|---|---|
| API fetch latency | < 5 seconds total | All 3 sources called in parallel via `asyncio.gather` |
| Claude generation time | 20–40 seconds | Mitigated by streaming — user sees output immediately |
| Max context size | ~80K tokens (`claude-sonnet-4-6`) | Normalizers truncate descriptions to 200 chars; max 10 items per source |
| Session isolation | 100% | All state in `st.session_state`; no shared state between users |
| Data persistence | None | By design — no DB, no disk writes, no cloud storage |
| Uptime / availability | Best effort (POC) | Streamlit Community Cloud free tier acceptable for POC |

---

## 10. POC Milestones

| Milestone | Deliverable | Target |
|---|---|---|
| M1 — Scaffold | Streamlit app skeleton, sidebar, CSS theme, page routing | Week 1 |
| M2 — Data Sources | Luma, Spotify, Webflow fetchers + normalizers + unit tests | Week 1–2 |
| M3 — File Upload | DOCX/TXT/MD extraction, context assembly | Week 2 |
| M4 — Claude Integration | Streaming call, preview render, session state | Week 2 |
| M5 — DOCX Output | `.docx` generation, download button | Week 2–3 |
| M6 — Stripe Theme | Full CSS polish, card layout, badges, step indicators | Week 3 |
| M7 — Internal Demo | Scott + CoSN team run newsletter end-to-end | Week 3–4 |
| M8 — Handoff | README, `.env.example`, Streamlit Cloud deploy | Week 4 |

---

## 11. Out of Scope for POC

- Scheduled / cron automations (requires persistent process; deferred to v1.0)
- User authentication or role-based access control
- Multi-user / multi-tenant support
- Persistent run history (logs clear on session reset)
- LinkedIn post or chapter outreach email automations (deferred to v1.0)
- Analytics, usage tracking, or dashboards
- Supabase or any database integration

---

*Chief of Staff Network — Agent Orchestration Dashboard | Technical PRD v0.2 — Streamlit POC | February 2026 | Confidential*
