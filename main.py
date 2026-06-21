"""
Quattro Sales Copilot — Unified B2B/B2C Entry Point
FastAPI backend + Dynamic Frontend
"""

import os
import json
import uuid
import time
import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Quattro Sales Copilot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Config ───────────────────────────────────────────────────────────────────
BUFFER_DIR = Path("database/buffer")
BUFFER_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# ─── Models ───────────────────────────────────────────────────────────────────

class DiagnosticInput(BaseModel):
    mode: str           # "b2b" or "b2c"
    channel: str        # "email", "whatsapp", "wechat"
    segment: str        # "appliance", "electronics", "insurance", "real_estate"
    company_name: Optional[str] = None
    user_name: Optional[str] = None

class SyncUploadText(BaseModel):
    content: str
    source: str = "mobile"       # "mobile", "desktop", "api"
    content_type: str = "text"   # "text", "screenshot_ocr", "quote"
    metadata: Optional[dict] = None

# ─── Vertical Profiles ────────────────────────────────────────────────────────

PROFILES = {
    "b2b": {
        "appliance": {
            "title": "Kitchen Appliance Export Copilot",
            "tagline": "From trade show card to signed PO in 72 hours",
            "features": [
                "Business card OCR → auto company enrichment",
                "Customs import history matching (HS 8516/8509)",
                "FOB/CIF/DDP price calculator with MOQ tiers",
                "3-email cold outreach sequence generator",
                "PDF/Excel quote parser & comparison engine",
                "Container load optimizer (20'/40'/40'HC)"
            ],
            "cta": "Upload Your First Business Card",
            "color_accent": "#00D4AA",
            "icon": "🏭"
        },
        "electronics": {
            "title": "Electronics Export Copilot",
            "tagline": "Find buyers. Parse RFQs. Close deals faster.",
            "features": [
                "Component BOM extraction from datasheets",
                "Customs data matching (HS 8471/8517/8542)",
                "FOB pricing with multi-tier MOQ breaks",
                "Automated RFQ response drafting",
                "Compliance checker (CE/FCC/UL/RoHS)",
                "Freight & logistics cost estimator"
            ],
            "cta": "Upload Your First RFQ",
            "color_accent": "#4D9FFF",
            "icon": "⚡"
        }
    },
    "b2c": {
        "insurance": {
            "title": "Insurance Agent Copilot",
            "tagline": "Turn every WhatsApp chat into a closed policy",
            "features": [
                "WhatsApp/WeChat screenshot OCR & sentiment analysis",
                "Client objection handler with rebuttals",
                "Policy comparison table generator",
                "Follow-up timeline with smart reminders",
                "Birthday & renewal date tracker",
                "Commission calculator & pipeline forecaster"
            ],
            "cta": "Upload Your First Client Chat",
            "color_accent": "#FF6B9D",
            "icon": "🛡️"
        },
        "real_estate": {
            "title": "Property Agent Copilot",
            "tagline": "Match clients to properties. Automate follow-ups.",
            "features": [
                "Client requirement extraction from chat screenshots",
                "Property listing comparison & shortlist builder",
                "Viewing schedule optimizer",
                "Price negotiation strategy assistant",
                "Transaction milestone tracker",
                "Market data quick-reference cards"
            ],
            "cta": "Upload Your First Client Inquiry",
            "color_accent": "#FFB84D",
            "icon": "🏠"
        }
    }
}


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the dynamic frontend."""
    template_path = Path("templates/index.html")
    return HTMLResponse(content=template_path.read_text(encoding="utf-8"))


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0", "timestamp": datetime.now(timezone.utc).isoformat()}


# ─── Diagnostic Profile API ──────────────────────────────────────────────────

@app.post("/api/v1/profile/diagnostic")
async def get_profile(input: DiagnosticInput):
    """
    Accept questionnaire inputs → return personalized configuration.
    """
    mode = input.mode.lower()
    segment = input.segment.lower()

    if mode not in PROFILES:
        raise HTTPException(400, f"Invalid mode: {mode}. Use 'b2b' or 'b2c'.")

    if segment not in PROFILES[mode]:
        available = list(PROFILES[mode].keys())
        raise HTTPException(400, f"Invalid segment: {segment}. Available: {available}")

    profile = PROFILES[mode][segment]

    return {
        "ok": True,
        "profile": profile,
        "config": {
            "mode": mode,
            "channel": input.channel,
            "segment": segment,
            "company_name": input.company_name,
            "user_name": input.user_name,
        },
        "sandbox_url": f"/sandbox?mode={mode}&segment={segment}",
    }


# ─── Sync Upload API (Mobile → Cloud Buffer) ─────────────────────────────────

@app.post("/api/v1/sync/upload")
async def sync_upload_text(payload: SyncUploadText):
    """
    Receive text/extracted content from mobile.
    Buffer it for later desktop sync.
    """
    lead_id = str(uuid.uuid4())[:12]
    timestamp = datetime.now(timezone.utc).isoformat()

    record = {
        "id": lead_id,
        "content": payload.content,
        "source": payload.source,
        "content_type": payload.content_type,
        "metadata": payload.metadata or {},
        "created_at": timestamp,
        "processed": False,
        "extracted_data": None,
    }

    # TODO: Run AI extraction (Gemini/DeepSeek) here
    # For now, store raw content
    if payload.content_type == "text" and len(payload.content) > 20:
        record["extracted_data"] = {
            "summary": payload.content[:200],
            "type": "raw_text",
            "word_count": len(payload.content.split()),
        }
        record["processed"] = True

    # Save to buffer
    buffer_file = BUFFER_DIR / f"{lead_id}.json"
    buffer_file.write_text(json.dumps(record, ensure_ascii=False, indent=2))

    return {
        "ok": True,
        "lead_id": lead_id,
        "message": "Buffered successfully. Will be available on next desktop sync.",
        "timestamp": timestamp,
    }


@app.post("/api/v1/sync/upload/image")
async def sync_upload_image(
    file: UploadFile = File(...),
    source: str = Form("mobile"),
    metadata: str = Form("{}"),
):
    """
    Receive screenshot/image from mobile.
    OCR + extract, buffer for desktop sync.
    """
    lead_id = str(uuid.uuid4())[:12]
    timestamp = datetime.now(timezone.utc).isoformat()

    contents = await file.read()
    b64_content = base64.b64encode(contents).decode()

    record = {
        "id": lead_id,
        "content": f"[image:{file.filename}]",
        "image_b64": b64_content[:100] + "...",  # Don't store full image in buffer
        "source": source,
        "content_type": "screenshot",
        "metadata": json.loads(metadata) if metadata else {},
        "created_at": timestamp,
        "processed": False,
        "extracted_data": None,
    }

    # TODO: Run OCR via Gemini 2.5 Flash
    record["extracted_data"] = {
        "status": "pending_ocr",
        "filename": file.filename,
        "size_bytes": len(contents),
    }

    buffer_file = BUFFER_DIR / f"{lead_id}.json"
    buffer_file.write_text(json.dumps(record, ensure_ascii=False, indent=2))

    return {
        "ok": True,
        "lead_id": lead_id,
        "message": "Image received. OCR processing queued.",
        "timestamp": timestamp,
    }


# ─── Sync Download API (Cloud Buffer → Desktop) ──────────────────────────────

@app.get("/api/v1/sync/download")
async def sync_download(clear: bool = True):
    """
    Desktop app calls this to fetch today's buffered leads.
    If clear=True (default), empties the cloud buffer after download.
    Enforces 'Local-First Storage' privacy promise.
    """
    buffer_files = sorted(BUFFER_DIR.glob("*.json"))

    if not buffer_files:
        return {
            "ok": True,
            "leads": [],
            "count": 0,
            "message": "No new leads in buffer.",
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

    leads = []
    for f in buffer_files:
        try:
            data = json.loads(f.read_text())
            # Remove image data before transfer (keep it lightweight)
            data.pop("image_b64", None)
            leads.append(data)
        except Exception:
            continue

    response = {
        "ok": True,
        "leads": leads,
        "count": len(leads),
        "message": f"Synced {len(leads)} leads to local storage.",
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }

    # Clear buffer after successful download (privacy: data doesn't linger in cloud)
    if clear:
        for f in buffer_files:
            try:
                f.unlink()
            except Exception:
                pass
        response["buffer_cleared"] = True

    return response


# ─── Sandbox Demo (placeholder) ──────────────────────────────────────────────

@app.get("/sandbox", response_class=HTMLResponse)
async def sandbox(mode: str = "b2b", segment: str = "appliance"):
    """Sandbox demo page — shows the vertical-specific tool interface."""
    profile = PROFILES.get(mode, {}).get(segment, PROFILES["b2b"]["appliance"])
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>{profile['title']} - Sandbox</title>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body {{ font-family: Inter, sans-serif; background: #0a0e1a; color: #e0e7ef; margin: 0; padding: 40px; }}
.sandbox {{ max-width: 800px; margin: 0 auto; }}
h1 {{ color: {profile['color_accent']}; }}
.feature {{ background: #141a2e; border-left: 3px solid {profile['color_accent']}; padding: 12px 16px; margin: 8px 0; border-radius: 4px; }}
.upload-zone {{ border: 2px dashed {profile['color_accent']}40; padding: 60px; text-align: center; border-radius: 12px; margin: 24px 0; cursor: pointer; }}
.upload-zone:hover {{ border-color: {profile['color_accent']}; background: {profile['color_accent']}08; }}
a {{ color: {profile['color_accent']}; }}
</style></head><body>
<div class="sandbox">
<p><a href="/">← Back to Home</a></p>
<h1>{profile['icon']} {profile['title']}</h1>
<p style="font-size:1.2em;color:#8899aa;">{profile['tagline']}</p>
<div class="upload-zone">
<p style="font-size:1.5em;">{profile['icon']}</p>
<p><strong>{profile['cta']}</strong></p>
<p style="color:#667;">Drag & drop or click to upload</p>
</div>
<h3>Features</h3>
{''.join(f'<div class="feature">✓ {f}</div>' for f in profile['features'])}
</div></body></html>""")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
