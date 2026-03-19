from app.services.message_intelligence.message_report_builder import message_report_builder

import asyncio

async def analyze_message(text: str) -> dict:
    """
    Main entry point for message intelligence engine.
    Orchestrates preprocessing, parallel/sequential signal extraction, and risk scoring.
    """
    # Moving CPU-bound NLP processing to a separate thread to prevent event loop blocking
    return await asyncio.to_thread(message_report_builder.build_report, text)
