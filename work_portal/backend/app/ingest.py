"""Ingestion pipeline: webhook payload or Read.ai pull -> storage."""
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .readai import ReadAIClient, _normalize
from .storage import Storage
from .summarizer import Summarizer


def _assign_action_item_ids(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items or []:
        item = dict(item)
        item.setdefault("id", f"ai_{uuid.uuid4().hex[:10]}")
        item.setdefault("completed", False)
        out.append(item)
    return out


@dataclass
class IngestService:
    storage: Storage
    summarizer: Summarizer
    readai: ReadAIClient | None = None
    title_pattern: str = ""

    def title_matches(self, title: str) -> bool:
        if not self.title_pattern:
            return True
        try:
            return bool(re.search(self.title_pattern, title or ""))
        except re.error:
            return True

    def ingest_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        meeting = payload.get("meeting") or payload
        normalized = _normalize(meeting)
        if not self.title_matches(normalized.get("title", "")):
            return {"status": "ignored", "reason": "title_filter", "meeting": normalized}
        return self._finalize(normalized)

    def refresh_from_readai(self) -> list[dict[str, Any]]:
        if self.readai is None:
            raise RuntimeError("Read.ai client not configured")
        meetings = self.readai.list_recent_meetings()
        saved: list[dict[str, Any]] = []
        for m in meetings:
            if not self.title_matches(m.get("title", "")):
                continue
            if self.storage.get_meeting(m["id"]):
                continue
            saved.append(self._finalize(m))
        return saved

    def _finalize(self, meeting: dict[str, Any]) -> dict[str, Any]:
        needs_summary = not meeting.get("summary") or not meeting.get("action_items")
        if needs_summary and meeting.get("transcript"):
            extracted = self.summarizer.summarize(
                meeting["transcript"], title=meeting.get("title", "L10 Meeting")
            )
            meeting["summary"] = extracted.get("summary") or meeting.get("summary", "")
            if not meeting.get("action_items"):
                meeting["action_items"] = extracted.get("action_items", [])
            if not meeting.get("files"):
                meeting["files"] = extracted.get("files", [])
        meeting["action_items"] = _assign_action_item_ids(meeting.get("action_items") or [])
        meeting.setdefault("ingested_at", datetime.now(timezone.utc).isoformat())
        if not meeting.get("id"):
            meeting["id"] = meeting.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
        self.storage.save_meeting(meeting)
        try:
            self.storage.purge_completed_todos()
        except AttributeError:
            pass
        return meeting
