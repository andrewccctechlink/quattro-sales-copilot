# Quattro Sales Copilot

AI-powered sales automation serving B2B (Trading/Manufacturing) and B2C (Insurance/Property) via a unified dynamic entry point.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Zeabur Cloud                       │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │          FastAPI Backend (port 8080)          │   │
│  │                                               │   │
│  │  GET  /              → Dynamic Frontend       │   │
│  │  POST /api/v1/profile/diagnostic → Profile    │   │
│  │  POST /api/v1/sync/upload       → Buffer      │   │
│  │  POST /api/v1/sync/upload/image → OCR+Buffer  │   │
│  │  GET  /api/v1/sync/download     → Flush       │   │
│  │  GET  /sandbox                  → Demo UI     │   │
│  └──────────────────────────────────────────────┘   │
│                       ↑              ↓               │
└───────────────────────┼──────────────┼───────────────┘
                        │              │
              ┌─────────┴──┐    ┌──────┴──────┐
              │   Mobile    │    │   Desktop    │
              │  (Upload)   │    │  (Download)  │
              │             │    │              │
              │ Screenshot  │    │ sales_pool.db│
              │ Quick notes │    │ (SQLite)     │
              └─────────────┘    └──────────────┘
```

## Verticals

| Mode | Segment | Focus |
|------|---------|-------|
| B2B | Appliance | FOB pricing, customs data, container optimization |
| B2B | Electronics | BOM extraction, compliance, RFQ parsing |
| B2C | Insurance | Chat OCR, objection handling, renewal tracking |
| B2C | Real Estate | Client matching, viewing scheduler, negotiation |

## Local Development

```bash
cd projects/quattro-sales-copilot
pip install -r requirements.txt
python main.py
# Open http://localhost:8080
```

## Deploy to Zeabur

1. Push this folder to a Git repo, or use Zeabur CLI
2. Set environment variables:
   - `GEMINI_API_KEY` (for OCR)
   - `DEEPSEEK_API_KEY` (for AI extraction)
3. Deploy — Zeabur auto-detects Dockerfile
4. Access via your `.zeabur.app` domain

## Desktop Sync Script

```python
"""Local desktop sync — run nightly to pull day's leads."""
import requests
import sqlite3
import json
from datetime import datetime

CLOUD_URL = "https://your-app.zeabur.app"

# Fetch buffered leads
resp = requests.get(f"{CLOUD_URL}/api/v1/sync/download?clear=true")
data = resp.json()

if data["ok"] and data["count"] > 0:
    # Store in local SQLite
    conn = sqlite3.connect("sales_pool.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS leads (
        id TEXT PRIMARY KEY,
        content TEXT,
        source TEXT,
        content_type TEXT,
        metadata TEXT,
        extracted_data TEXT,
        created_at TEXT,
        synced_at TEXT
    )""")
    
    for lead in data["leads"]:
        conn.execute(
            "INSERT OR REPLACE INTO leads VALUES (?,?,?,?,?,?,?,?)",
            (lead["id"], lead["content"], lead["source"],
             lead["content_type"], json.dumps(lead.get("metadata", {})),
             json.dumps(lead.get("extracted_data")),
             lead["created_at"], datetime.utcnow().isoformat())
        )
    conn.commit()
    conn.close()
    print(f"✅ Synced {data['count']} leads to sales_pool.db")
else:
    print("No new leads.")
```

## API Reference

### POST /api/v1/profile/diagnostic
Returns personalized profile configuration based on questionnaire.

### POST /api/v1/sync/upload
Buffers text content from mobile for later desktop sync.

### POST /api/v1/sync/upload/image
Buffers screenshot/image with OCR processing queue.

### GET /api/v1/sync/download?clear=true
Desktop downloads all buffered leads. `clear=true` empties cloud buffer (privacy).
