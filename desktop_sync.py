"""
Quattro Sales Copilot — Desktop Sync Script
Run this nightly on your local machine to pull all buffered leads from cloud.
Data is deleted from cloud after sync (Local-First Storage).

Usage:
    python desktop_sync.py
    python desktop_sync.py --url https://your-app.zeabur.app
"""

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests")
    exit(1)

DB_PATH = "sales_pool.db"


def init_db(db_path: str):
    """Create the local SQLite database if it doesn't exist."""
    conn = sqlite3.connect(db_path)
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
    conn.execute("""CREATE TABLE IF NOT EXISTS sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        synced_at TEXT,
        count INTEGER,
        status TEXT
    )""")
    conn.commit()
    return conn


def sync(cloud_url: str, db_path: str = DB_PATH):
    """Pull leads from cloud buffer and store locally."""
    print(f"🔄 Syncing from {cloud_url}...")

    try:
        resp = requests.get(f"{cloud_url}/api/v1/sync/download?clear=true", timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    if not data.get("ok"):
        print(f"❌ Server error: {data}")
        return

    count = data.get("count", 0)
    if count == 0:
        print("✅ No new leads in buffer.")
        return

    # Store in local SQLite
    conn = init_db(db_path)
    now = datetime.now(timezone.utc).isoformat()

    inserted = 0
    for lead in data["leads"]:
        try:
            conn.execute(
                "INSERT OR REPLACE INTO leads VALUES (?,?,?,?,?,?,?,?)",
                (
                    lead["id"],
                    lead.get("content", ""),
                    lead.get("source", ""),
                    lead.get("content_type", ""),
                    json.dumps(lead.get("metadata", {}), ensure_ascii=False),
                    json.dumps(lead.get("extracted_data"), ensure_ascii=False),
                    lead.get("created_at", ""),
                    now,
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"  ⚠️ Skipped lead {lead.get('id')}: {e}")

    # Log sync
    conn.execute(
        "INSERT INTO sync_log (synced_at, count, status) VALUES (?,?,?)",
        (now, inserted, "ok"),
    )
    conn.commit()
    conn.close()

    print(f"✅ Synced {inserted}/{count} leads → {db_path}")
    if data.get("buffer_cleared"):
        print("🗑️  Cloud buffer cleared (Local-First Storage ✓)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quattro Sales Copilot — Desktop Sync")
    parser.add_argument("--url", default="http://localhost:8080", help="Cloud server URL")
    parser.add_argument("--db", default=DB_PATH, help="Local SQLite path")
    args = parser.parse_args()

    sync(args.url, args.db)
