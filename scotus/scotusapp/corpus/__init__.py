"""Corpus loaders for the SCOTUS platform.

Kept import-light (no eager submodule imports) so that the dependency-free bulk-parsing helpers in
``courtlistener_bulk`` can be imported and unit-tested without pulling in ``scotusapp.db`` (and thus
psycopg / pydantic-settings). Import the loaders explicitly, e.g.::

    from scotusapp.corpus.loader import ingest_records, ingest_jsonl
    from scotusapp.corpus.courtlistener_bulk import iter_segment_rows
"""
