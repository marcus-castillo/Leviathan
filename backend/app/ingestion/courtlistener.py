"""CourtListener (v4 REST) ingestion.

Pulls opinion clusters + their plain text and associated metadata (judge, court, date, citations,
case type heuristic) and upserts them. Token is optional but raises rate limits.

Docs: https://www.courtlistener.com/help/api/rest/
"""
from __future__ import annotations

from datetime import date, datetime

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.ingestion.base import upsert_opinion
from app.nlp.issues import tag_issues


class CourtListenerClient:
    def __init__(self, token: str | None = None, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.courtlistener_base_url).rstrip("/")
        headers = {"User-Agent": "Leviathan/0.1 (research)"}
        token = token or settings.courtlistener_api_token
        if token:
            headers["Authorization"] = f"Token {token}"
        self._client = httpx.Client(headers=headers, timeout=30.0)

    def search(self, *, court: str | None = None, q: str | None = None,
               page_size: int = 20) -> list[dict]:
        params = {"type": "o", "page_size": page_size}
        if court:
            params["court"] = court
        if q:
            params["q"] = q
        r = self._client.get(f"{self.base_url}/search/", params=params)
        r.raise_for_status()
        return r.json().get("results", [])

    def opinion_text(self, opinion_id: int) -> str:
        r = self._client.get(f"{self.base_url}/opinions/{opinion_id}/")
        r.raise_for_status()
        data = r.json()
        # Prefer plain_text; fall back to HTML-stripped variants.
        for key in ("plain_text", "html_with_citations", "html", "html_lawbox"):
            if data.get(key):
                return _strip_html(data[key]) if key.startswith("html") else data[key]
        return ""

    def close(self) -> None:
        self._client.close()


def _strip_html(html: str) -> str:
    import re

    return re.sub(r"<[^>]+>", " ", html)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None


def ingest_courtlistener(
    db: Session,
    *,
    court: str | None = None,
    query: str | None = None,
    limit: int = 20,
    client: CourtListenerClient | None = None,
) -> int:
    """Ingest up to ``limit`` opinions matching the filters. Returns count ingested."""
    owns_client = client is None
    client = client or CourtListenerClient()
    count = 0
    try:
        for hit in client.search(court=court, q=query, page_size=limit):
            opinion_ids = hit.get("opinions") or []
            op_id = None
            if opinion_ids and isinstance(opinion_ids[0], dict):
                op_id = opinion_ids[0].get("id")
            text = client.opinion_text(op_id) if op_id else (hit.get("snippet") or "")
            if not text:
                continue
            citations = hit.get("citation") or hit.get("citations") or []
            if isinstance(citations, str):
                citations = [citations]
            case_type = (tag_issues(text) or ["unknown"])[0]
            upsert_opinion(
                db,
                case_name=hit.get("caseName") or hit.get("case_name") or "Unknown",
                text=text,
                judge_name=hit.get("judge"),
                court=hit.get("court_id") or hit.get("court"),
                decided=_parse_date(hit.get("dateFiled")),
                case_type=case_type,
                citations=list(citations),
                source="courtlistener",
                external_id=str(hit.get("cluster_id") or hit.get("id")),
                extra={"docket": hit.get("docketNumber")},
            )
            count += 1
        db.commit()
    finally:
        if owns_client:
            client.close()
    return count
