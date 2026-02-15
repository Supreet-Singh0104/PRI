# src/graph/citation_enforcer.py

from __future__ import annotations
from typing import Any, Dict, List, Set
import re

REF_PATTERN = re.compile(r"Ref\s+(\d+)", re.IGNORECASE)


def extract_used_ref_ids(text: str) -> List[int]:
    ids: Set[int] = set()
    for m in REF_PATTERN.finditer(text or ""):
        try:
            ids.add(int(m.group(1)))
        except Exception:
            pass
    return sorted(ids)


def build_references_block(citations: List[Dict[str, Any]], only_ids: List[int] | None = None) -> str:
    if not citations:
        return ""

    allowed = set(only_ids) if only_ids else None

    lines = ["\n### References"]
    for c in citations:
        rid = c.get("ref_id")
        if rid is None:
            continue
        if allowed is not None and rid not in allowed:
            continue

        title = c.get("title") or "Source"
        url = c.get("url") or ""

        if url:
            lines.append(f"{rid}. {title} – {url}")
        else:
            lines.append(f"{rid}. {title}")

    # If we filtered and ended up empty, don’t add a blank References block
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def remove_existing_references_section(text: str) -> str:
    """
    Removes anything starting from '### References' to end.
    Keeps the main body intact.
    """
    marker = "### References"
    if marker in text:
        return text.split(marker)[0].rstrip()
    return text.rstrip()


def validate_ref_ids(used_ids: List[int], citations: List[Dict[str, Any]]) -> List[str]:
    logs = []
    valid = set(int(c.get("ref_id")) for c in citations if c.get("ref_id") is not None)
    missing = [x for x in used_ids if x not in valid]
    if missing:
        logs.append(f"citation_enforcer: WARNING - report cites missing Ref IDs: {missing}")
    return logs
