import asyncio
from typing import Dict, Any
from app.logger import logger
from app.services.message_intelligence.message_preprocessor import preprocessor
from app.services.message_intelligence.language_detector import language_detector
from app.services.message_intelligence.message_risk_engine import message_risk_engine
from app.models.message_models import MessageIntelligence, MessageIntelligenceReport

class MessageReportBuilder:
    def build_report(self, text: str) -> Dict[str, Any]:
        """
        Main entry point for message intelligence engine.
        Orchestrates preprocessing, signal extraction, and risk scoring.
        """
        if not text:
            logger.warning("MessageReportBuilder received empty text")
            return {"error": "Message text is empty"}

        try:
            # 1. Preprocessing
            processed_data = preprocessor.process(text)
            normalized_text = processed_data.get("normalized", "")

            # 2. Language Detection
            lang_info = language_detector.detect(normalized_text)
            language_code = lang_info.get("language")

            # 3. Evaluate Risk (includes score_details)
            risk_evaluation = message_risk_engine.evaluate(normalized_text, processed_data)

            # 4. Assemble Report — include score_details inside MessageIntelligence
            intelligence = MessageIntelligence(
                intent=risk_evaluation.get("intent", "unknown"),
                urgency_score=risk_evaluation.get("urgency_score", 0.0),
                impersonated_brand=risk_evaluation.get("impersonated_brand"),
                credential_request_detected=risk_evaluation.get("credential_request_detected", False),
                scam_probability=risk_evaluation.get("scam_probability", 0.0),
                scam_category=risk_evaluation.get("scam_category"),
                language=language_code,
                score_details=risk_evaluation.get("score_details", {})
            )

            report = MessageIntelligenceReport(message_analysis=intelligence)

            return report.model_dump()
        except Exception as e:
            logger.error(f"Error in MessageReportBuilder: {e}")
            return {"error": "Internal error during message analysis"}

message_report_builder = MessageReportBuilder()
