"""
llm_retrainer.py
─────────────────
Reads collected feedback and generates a fine-tuning-ready JSONL dataset.

Output format: OpenAI / Hugging Face supervised fine-tuning JSONL
  {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}

Use cases:
  1. Feed into Groq / OpenAI fine-tuning API
  2. LoRA fine-tune a local Llama/Mistral model
  3. Augment phishing_knowledge.json with new patterns

NOTE: Does NOT auto-retrain (requires GPU / paid API).
      Generates ready-to-use dataset files for offline processing.
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any

from app.logger import logger
from app.services.behavioral_engine.feedback_collector import get_false_positives, get_false_negatives

_FINETUNE_PATH = os.path.join("data", "finetune_dataset.jsonl")
_KNOWLEDGE_PATH = os.path.join("data", "phishing_knowledge.json")

_SYSTEM_PROMPT = (
    "You are an elite cybersecurity fraud detection AI. "
    "Analyse the provided message and URL for scam indicators. "
    "Respond ONLY with valid JSON: {scam_probability, threat_type, confidence, explanation}"
)


def _make_training_entry(
    url: str,
    notes: str,
    label: str,  # "scam" or "safe"
    verdict_override: str
) -> Dict[str, Any]:
    """Create a single fine-tuning training example."""
    user_content = f"URL: {url}\nContext: {notes or 'No additional context'}"
    assistant_content = json.dumps({
        "scam_probability": 95 if label == "scam" else 5,
        "threat_type": "phishing" if label == "scam" else "safe",
        "confidence": 0.90,
        "explanation": f"Verified {label} by user feedback. {notes or ''}"
    })
    return {
        "messages": [
            {"role": "system",    "content": _SYSTEM_PROMPT},
            {"role": "user",      "content": user_content},
            {"role": "assistant", "content": assistant_content}
        ]
    }


async def generate_finetune_dataset() -> Dict[str, Any]:
    """
    Generate fine-tuning JSONL from false positives and false negatives.

    Returns:
        Summary dict with counts and output path.
    """
    false_positives = await get_false_positives(limit=500)
    false_negatives = await get_false_negatives(limit=500)

    entries: List[Dict] = []

    # False positives: system=scam, user=safe → train AI to NOT flag as scam
    for fp in false_positives:
        entries.append(_make_training_entry(
            url=fp.get("url", ""),
            notes=fp.get("notes", ""),
            label="safe",
            verdict_override="false_positive"
        ))

    # False negatives: system=safe, user=scam → train AI to flag as scam
    for fn in false_negatives:
        entries.append(_make_training_entry(
            url=fn.get("url", ""),
            notes=fn.get("notes", ""),
            label="scam",
            verdict_override="false_negative"
        ))

    if not entries:
        logger.info("No feedback entries to generate fine-tuning dataset from")
        return {"entries": 0, "path": None, "status": "no_data"}

    os.makedirs(os.path.dirname(_FINETUNE_PATH) or ".", exist_ok=True)
    with open(_FINETUNE_PATH, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info(
        f"Fine-tuning dataset generated: {len(entries)} entries → {_FINETUNE_PATH}"
    )
    return {
        "entries": len(entries),
        "false_positives": len(false_positives),
        "false_negatives": len(false_negatives),
        "path": _FINETUNE_PATH,
        "generated_at": datetime.now().isoformat(),
        "status": "success"
    }


async def augment_knowledge_base(new_entries: List[Dict]) -> bool:
    """
    Add new verified phishing patterns to phishing_knowledge.json.
    Automatically assigns next available ID.
    """
    try:
        existing: List[Dict] = []
        if os.path.exists(_KNOWLEDGE_PATH):
            with open(_KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)

        max_id = max((int(e.get("id", 0)) for e in existing), default=0)

        for i, entry in enumerate(new_entries):
            entry["id"] = str(max_id + i + 1)
            existing.append(entry)

        with open(_KNOWLEDGE_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

        logger.info(f"Knowledge base augmented: {len(new_entries)} new entries added")
        return True

    except Exception as e:
        logger.error(f"Failed to augment knowledge base: {e}")
        return False
