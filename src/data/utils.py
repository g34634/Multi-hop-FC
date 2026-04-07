import json
import random
import re
import unicodedata
from pathlib import Path
from typing import Any


def set_seed(seed: int) -> None:
    random.seed(seed)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_json(data: Any, path: Path, indent: int = 2) -> None:
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_jsonl(rows: list[dict], path: Path) -> None:
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def normalize_title(title: str, lowercase: bool = False) -> str:
    """
    Normalize title for deterministic chunk id.
    Keep parentheses, replace whitespace with underscore.
    """
    title = unicodedata.normalize("NFKC", title).strip()
    title = re.sub(r"\s+", " ", title)
    if lowercase:
        title = title.lower()
    return title.replace(" ", "_")


def make_chunk_id(doc_title: str, sent_id: int, lowercase: bool = False) -> str:
    normalized = normalize_title(doc_title, lowercase=lowercase)
    return f"wiki::{normalized}::{sent_id}"


def safe_get_supporting_facts(row: dict) -> list[list]:
    sf = row.get("supporting_facts", [])
    if sf is None:
        return []
    return sf