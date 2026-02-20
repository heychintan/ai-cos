import os
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from fetchers.luma import fetch_luma_events
from fetchers.spotify import fetch_spotify_episodes
from fetchers.webflow import fetch_webflow_posts
from normalizers.luma import normalize_luma
from normalizers.spotify import normalize_spotify
from normalizers.webflow import normalize_webflow
from normalizers.assembler import assemble_context
from agent import generate_newsletter
from output.docx_writer import write_docx

app = FastAPI(title="CoSN Agent Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory run status for POC
run_status = {"status": "idle", "step": "", "error": None}


@app.get("/api/status")
def get_status():
    return run_status


@app.post("/api/run")
async def run_automation(
    template: UploadFile = File(None),
    spotify_show_id: str = Form(default=""),
):
    global run_status
    run_status = {"status": "fetching", "step": "Fetching data from sources...", "error": None}

    try:
        # Load template
        if template:
            template_text = (await template.read()).decode("utf-8", errors="ignore")
        else:
            template_text = (
                "Write a professional weekly newsletter for the CoSN community. "
                "Include sections for: Upcoming Events, Recent Podcast Episodes, Recent Blog Posts, "
                "and a brief intro/outro."
            )

        # Fetch data
        luma_raw, spotify_raw, webflow_raw = {}, {}, {}

        try:
            luma_raw = fetch_luma_events()
        except Exception as e:
            luma_raw = {"error": str(e)}

        try:
            show_id = spotify_show_id or os.getenv("SPOTIFY_SHOW_ID", "")
            spotify_raw = fetch_spotify_episodes(show_id) if show_id else {}
        except Exception as e:
            spotify_raw = {"error": str(e)}

        try:
            webflow_raw = fetch_webflow_posts()
        except Exception as e:
            webflow_raw = {"error": str(e)}

        # Normalize
        luma_text = normalize_luma(luma_raw)
        spotify_text = normalize_spotify(spotify_raw)
        webflow_text = normalize_webflow(webflow_raw)

        # Assemble context
        context = assemble_context(luma_text, spotify_text, webflow_text, template_text)

        # Generate with Claude
        run_status = {"status": "generating", "step": "Generating newsletter with Claude...", "error": None}
        newsletter_content = generate_newsletter(context)

        # Write docx
        run_status = {"status": "done", "step": "Done!", "error": None}
        doc_buffer = write_docx(newsletter_content)
        filename = f"CoSN_Newsletter_{datetime.now().strftime('%Y-%m-%d')}.docx"

        return StreamingResponse(
            doc_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        run_status = {"status": "error", "step": "", "error": str(e)}
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-connection")
async def test_connection(service: str = Form(...)):
    """Test API key connectivity for a given service."""
    try:
        if service == "luma":
            fetch_luma_events(days_ahead=1)
        elif service == "spotify":
            show_id = os.getenv("SPOTIFY_SHOW_ID", "")
            if not show_id:
                return {"ok": False, "message": "SPOTIFY_SHOW_ID not set in .env"}
            fetch_spotify_episodes(show_id, days_back=30)
        elif service == "webflow":
            fetch_webflow_posts(days_back=30)
        elif service == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
        else:
            return {"ok": False, "message": f"Unknown service: {service}"}
        return {"ok": True, "message": f"{service} connected successfully"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


@app.get("/api/collections")
def get_webflow_collections():
    """List Webflow collections for config UI."""
    try:
        import requests
        api_key = os.getenv("WEBFLOW_API_KEY")
        site_id = os.getenv("WEBFLOW_SITE_ID", "")
        headers = {"Authorization": f"Bearer {api_key}", "accept-version": "1.0.0"}
        resp = requests.get(f"https://api.webflow.com/sites/{site_id}/collections", headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
