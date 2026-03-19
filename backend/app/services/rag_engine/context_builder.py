"""
context_builder.py
───────────────────
Formats RAG retrieval results into a plain-English context block
that can be injected directly into the LLM prompt.
"""
from typing import List, Dict, Any


_NO_CONTEXT = "No relevant historical knowledge found for this scan."


def build_rag_context(results: List[Dict[str, Any]]) -> str:
    """
    Format retrieved knowledge entries into a prompt-ready context string.

    Args:
        results: List of dicts from knowledge_retriever.retrieve_knowledge()

    Returns:
        Formatted multi-line string describing matched phishing patterns.
    """
    if not results:
        return _NO_CONTEXT

    lines = ["The following historical phishing patterns are relevant to this scan:\n"]

    for i, entry in enumerate(results, 1):
        title = entry.get("title", "Unknown pattern")
        brand = entry.get("brand", "")
        threat_type = entry.get("threat_type", "")
        indicators = entry.get("indicators", "")
        similarity = entry.get("similarity", 0)

        block = [f"[{i}] {title}"]
        if brand:
            block.append(f"    Brand targeted: {brand}")
        if threat_type:
            block.append(f"    Threat type: {threat_type}")
        if indicators:
            block.append(f"    Indicators: {indicators}")
        block.append(f"    Similarity score: {similarity:.2f}")

        lines.append("\n".join(block))

    return "\n\n".join(lines)


def get_evidence_list(results: List[Dict[str, Any]]) -> List[str]:
    """
    Extract just the titles for use in the API response's 'evidence' field.
    """
    return [r.get("title", "") for r in results if r.get("title")]
