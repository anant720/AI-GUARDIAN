"""
dataset_generator.py — Phase 6
────────────────────────────────
Converts List[LabeledExample] into versioned JSONL fine-tuning datasets.

Formats supported:
  • Instruction-tuning (OpenAI / Groq Chat format)
  • Preference/DPO (for future RLHF use)

Enrichment:
  Looks up scan_history to pull behavioral/semantic scores and attaches
  them as additional context in the user message.

Output:
  data/finetune_v{N}.jsonl   (instruction-tuning)
  data/finetune_dpo_v{N}.jsonl (preference, if enough pairs)
"""
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.logger import logger
from app.services.continuous_learning.feedback_processor import LabeledExample

_DATA_DIR = "data"
_DB_PATH = os.path.join(_DATA_DIR, "feedback.db")

_SYSTEM_PROMPT = (
    "You are an elite AI cybersecurity analyst specializing in scam, phishing, "
    "and fraud detection. Given a URL and message, analyse for social engineering, "
    "brand impersonation, domain anomalies, urgency tactics, and financial fraud. "
    "Respond ONLY with valid JSON: "
    "{\"scam_probability\": <0-100>, \"threat_type\": <str>, "
    "\"confidence\": <0.0-1.0>, \"explanation\": <str>}"
)


def _build_user_message(example: LabeledExample, context: Dict[str, Any] = None) -> str:
    """Build the enriched user message for fine-tuning."""
    lines = [f"URL: {example.url}"]

    if example.notes:
        lines.append(f"Context: {example.notes}")

    # Phase 5 context enrichment from scan_history
    if context:
        if context.get("behavioral_score") is not None:
            lines.append(f"Behavioral risk score: {context['behavioral_score']}/100")
        if context.get("semantic_score") is not None:
            lines.append(f"Semantic similarity score: {context['semantic_score']}/100")
        if context.get("ti_score") is not None:
            lines.append(f"Threat intelligence score: {context['ti_score']}/100")
        if context.get("domain_rep"):
            lines.append(f"Domain reputation: {context['domain_rep']}")
        if context.get("intent_conflict"):
            lines.append("⚠ Intent conflict detected: message brand does not match URL domain")
        if context.get("urgency"):
            lines.append("⚠ Time-pressure / urgency language detected")

    return "\n".join(lines)


def _build_assistant_message(example: LabeledExample) -> str:
    """Build the correct assistant response for fine-tuning."""
    is_scam = example.label == "scam"
    prob = 90 if is_scam else 8
    # honour original probability if it was closer to truth
    if is_scam and example.scam_probability and example.scam_probability > 50:
        prob = max(example.scam_probability, 85)
    elif not is_scam and example.scam_probability and example.scam_probability < 40:
        prob = min(example.scam_probability, 12)

    threat_type = "phishing" if is_scam else "safe"
    confidence  = round(example.confidence, 2)
    explanation = (
        example.notes if example.notes
        else (
            f"User confirmed this is a {example.label} case. "
            f"System originally classified as {example.system_verdict} "
            f"(probability {example.scam_probability}%)."
        )
    )
    # Truncate explanation
    explanation = explanation[:200]

    return json.dumps({
        "scam_probability": prob,
        "threat_type": threat_type,
        "confidence": confidence,
        "explanation": explanation
    })


async def _get_history_context(message_id: str) -> Dict[str, Any]:
    """Look up Phase 5 signals stored in scan_history for enrichment."""
    ctx: Dict[str, Any] = {}
    try:
        import aiosqlite
        async with aiosqlite.connect(_DB_PATH) as db:
            async with db.execute(
                "SELECT verdict, scam_probability FROM scan_history "
                "WHERE message_id = ? LIMIT 1",
                (message_id,)
            ) as cursor:
                row = await cursor.fetchone()
        if row:
            ctx["prior_verdict"]  = row[0]
            ctx["ti_score"]       = row[1]
    except Exception:
        pass
    return ctx


def _next_version() -> str:
    """Determine next dataset version by counting existing files."""
    existing = [
        f for f in os.listdir(_DATA_DIR)
        if f.startswith("finetune_v") and f.endswith(".jsonl")
    ] if os.path.exists(_DATA_DIR) else []
    return f"v{len(existing) + 1}.0"


async def generate_dataset(
    examples: List[LabeledExample],
    max_examples: int = 500,
    include_dpo: bool = False
) -> Dict[str, Any]:
    """
    Generate versioned JSONL fine-tuning dataset from labeled examples.

    Args:
        examples: LabeledExample list from feedback_processor
        max_examples: cap on dataset size (best examples first by confidence)
        include_dpo: also generate DPO preference pairs

    Returns:
        Summary dict with paths, counts, version
    """
    if not examples:
        logger.info("No labeled examples available — dataset generation skipped")
        return {"entries": 0, "path": None, "status": "no_data"}

    os.makedirs(_DATA_DIR, exist_ok=True)
    version = _next_version()
    out_path = os.path.join(_DATA_DIR, f"finetune_{version}.jsonl")
    dpo_path = os.path.join(_DATA_DIR, f"finetune_dpo_{version}.jsonl") if include_dpo else None

    # Cap to max_examples — already sorted by confidence DESC
    selected = examples[:max_examples]

    instruction_entries: List[Dict] = []
    dpo_entries: List[Dict] = []

    for ex in selected:
        context = await _get_history_context(ex.message_id)
        user_msg   = _build_user_message(ex, context)
        assist_msg = _build_assistant_message(ex)

        instruction_entries.append({
            "messages": [
                {"role": "system",    "content": _SYSTEM_PROMPT},
                {"role": "user",      "content": user_msg},
                {"role": "assistant", "content": assist_msg}
            ]
        })

        if include_dpo:
            # DPO: chosen = correct label, rejected = system's wrong label
            wrong_assistant = json.dumps({
                "scam_probability": ex.scam_probability,
                "threat_type": ex.system_verdict,
                "confidence": 0.5,
                "explanation": f"System incorrectly classified as {ex.system_verdict}"
            })
            dpo_entries.append({
                "prompt": user_msg,
                "chosen": assist_msg,
                "rejected": wrong_assistant
            })

    # Write instruction-tuning JSONL
    with open(out_path, "w", encoding="utf-8") as f:
        for entry in instruction_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Write DPO JSONL if requested
    if include_dpo and dpo_path:
        with open(dpo_path, "w", encoding="utf-8") as f:
            for entry in dpo_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    fp_count = sum(1 for e in selected if e.system_verdict == "scam" and e.label == "safe")
    fn_count = sum(1 for e in selected if e.system_verdict == "safe"  and e.label == "scam")

    logger.info(
        f"Dataset generated: {len(instruction_entries)} entries "
        f"({fp_count} FP, {fn_count} FN) → {out_path}"
    )

    return {
        "version": version,
        "entries": len(instruction_entries),
        "false_positives_in_set": fp_count,
        "false_negatives_in_set": fn_count,
        "path": out_path,
        "dpo_path": dpo_path,
        "generated_at": datetime.now().isoformat(),
        "status": "success"
    }
