from __future__ import annotations

from typing import Any


def serialize_documents(docs: list[Any]) -> str:
    lines: list[str] = []

    for i, doc in enumerate(docs, start=1):
        if isinstance(doc, dict):
            text = str(
                doc.get("text")
                or doc.get("page_content")
                or doc.get("document")
                or ""
            )
            metadata = doc.get("metadata") or {}
            doc_id = doc.get("id")
        else:
            text = str(getattr(doc, "page_content", doc))
            metadata = getattr(doc, "metadata", {}) or {}
            doc_id = getattr(doc, "id", None)

        title = (
            metadata.get("title")
            or metadata.get("source")
            or doc_id
            or f"doc_{i}"
        )

        text = " ".join(text.split())
        lines.append(f"[Evidence {i}] {title}: {text}")

    return "\n".join(lines)