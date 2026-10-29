import json
import re
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"
KNOWLEDGE_FILES = ["fees.json", "eligibility.json", "faq.json"]


def load_knowledge_base() -> list[dict]:
    entries: list[dict] = []
    for filename in KNOWLEDGE_FILES:
        with open(KNOWLEDGE_DIR / filename, encoding="utf-8") as f:
            entries.extend(json.load(f))
    return entries


def _keywords(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def search_knowledge_base(query: str, kb: list[dict]) -> list[dict]:
    query_words = _keywords(query)
    scored = []
    for entry in kb:
        entry_words = _keywords(entry["topic"] + " " + entry["content"])
        score = len(query_words & entry_words)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [entry for _score, entry in scored[:3]]
