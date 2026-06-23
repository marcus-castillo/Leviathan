"""Dataset versioning + reproducibility logs.

Each released version gets an immutable directory under ``DATASET_DIR/versions/<vX.Y.Z>/`` holding the
exported data files plus a ``manifest.json`` describing exactly how it was produced:

  * semantic version + previous version
  * schema_version and a field-level diff vs. the previous release
  * row count and a deterministic content hash (over sorted record_ids + text hashes)
  * the reproducibility log: CLI invocation, resolved config, git commit, timestamp
  * per-format file names + sizes

A top-level ``registry.json`` indexes all versions and ``CHANGELOG.md`` is appended for humans.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from levcorpus import config
from levcorpus.schema import SCHEMA_VERSION, schema_field_names


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=config.REPO_ROOT
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def _bump(version: str, part: str) -> str:
    major, minor, patch = (int(x) for x in version.lstrip("v").split("."))
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def _content_hash(records: list[dict]) -> str:
    h = hashlib.sha256()
    for rid in sorted(r.get("record_id", "") + r.get("text_sha256", "") for r in records):
        h.update(rid.encode("utf-8"))
    return h.hexdigest()


class VersionRegistry:
    def __init__(self, dataset_dir: Path | None = None) -> None:
        self.root = Path(dataset_dir or config.DATASET_DIR)
        self.versions_dir = self.root / "versions"
        self.registry_path = self.root / "registry.json"
        self.changelog_path = self.root / "CHANGELOG.md"
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    # ---- registry index ----
    def _load_registry(self) -> dict:
        if self.registry_path.exists():
            return json.loads(self.registry_path.read_text(encoding="utf-8"))
        return {"versions": []}

    def _save_registry(self, reg: dict) -> None:
        self.registry_path.write_text(json.dumps(reg, indent=2), encoding="utf-8")

    def latest_version(self) -> str | None:
        reg = self._load_registry()
        return reg["versions"][-1]["version"] if reg["versions"] else None

    def list_versions(self) -> list[dict]:
        return self._load_registry()["versions"]

    def next_version(self, bump: str = "minor", explicit: str | None = None) -> str:
        if explicit:
            return explicit.lstrip("v")
        latest = self.latest_version()
        return _bump(latest, bump) if latest else "0.1.0"

    # ---- schema diff ----
    def _schema_diff(self) -> dict:
        prev = self._previous_manifest()
        prev_fields = set(prev.get("schema_fields", [])) if prev else set()
        cur_fields = schema_field_names()
        return {
            "previous_schema_version": prev.get("schema_version") if prev else None,
            "added_fields": sorted(cur_fields - prev_fields),
            "removed_fields": sorted(prev_fields - cur_fields),
        }

    def _previous_manifest(self) -> dict | None:
        latest = self.latest_version()
        if not latest:
            return None
        mpath = self.versions_dir / f"v{latest}" / "manifest.json"
        return json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else None

    # ---- release ----
    def release(
        self,
        records: list[dict],
        *,
        formats: list[str],
        bump: str = "minor",
        explicit_version: str | None = None,
        note: str = "",
    ) -> dict:
        from levcorpus.export.writers import WRITERS

        version = self.next_version(bump, explicit_version)
        vdir = self.versions_dir / f"v{version}"
        if vdir.exists():
            raise FileExistsError(f"Version v{version} already exists at {vdir}")
        vdir.mkdir(parents=True)

        # stamp dataset_version into each record before writing
        for r in records:
            r["dataset_version"] = version

        files = {}
        for fmt in formats:
            writer = WRITERS[fmt]
            ext = "jsonl" if fmt == "jsonl" else fmt
            out = vdir / f"data.{ext}"
            n = writer(records, out)
            files[fmt] = {"file": out.name, "rows": n, "bytes": out.stat().st_size}

        manifest = {
            "version": version,
            "previous_version": self.latest_version(),
            "schema_version": SCHEMA_VERSION,
            "schema_fields": sorted(schema_field_names()),
            "schema_diff": self._schema_diff(),
            "row_count": len(records),
            "content_hash": _content_hash(records),
            "files": files,
            "note": note,
            "reproducibility": {
                "cli": " ".join(sys.argv),
                "config": config.resolved(),
                "git_commit": _git_commit(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "python": sys.version.split()[0],
            },
        }
        (vdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        reg = self._load_registry()
        reg["versions"].append(
            {"version": version, "row_count": len(records),
             "content_hash": manifest["content_hash"],
             "created_at": manifest["reproducibility"]["created_at"], "note": note}
        )
        self._save_registry(reg)
        self._append_changelog(manifest)
        return manifest

    def _append_changelog(self, manifest: dict) -> None:
        diff = manifest["schema_diff"]
        lines = [
            f"## v{manifest['version']} — {manifest['reproducibility']['created_at'][:10]}",
            f"- rows: {manifest['row_count']} · content hash: `{manifest['content_hash'][:12]}`",
            f"- schema: {manifest['schema_version']}"
            + (f" (added {diff['added_fields']})" if diff["added_fields"] else "")
            + (f" (removed {diff['removed_fields']})" if diff["removed_fields"] else ""),
        ]
        if manifest["note"]:
            lines.append(f"- note: {manifest['note']}")
        lines.append("")
        header = "" if self.changelog_path.exists() else "# Dataset changelog\n\n"
        with self.changelog_path.open("a", encoding="utf-8") as fh:
            fh.write(header + "\n".join(lines) + "\n")
