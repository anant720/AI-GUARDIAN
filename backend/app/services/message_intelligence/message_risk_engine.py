from typing import Dict, Any
from app.logger import logger
from app.services.message_intelligence.intent_classifier import intent_classifier
from app.services.message_intelligence.urgency_detector import urgency_detector
from app.services.message_intelligence.credential_request_detector import credential_request_detector
from app.services.message_intelligence.financial_scam_detector import financial_scam_detector
from app.services.message_intelligence.impersonation_detector import impersonation_detector
from app.services.message_intelligence.link_context_analyzer import link_context_analyzer
from app.services.message_intelligence.semantic_similarity_engine import semantic_similarity_engine

class MessageRiskEngine:
    def evaluate(self, normalized_text: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine signals to calculate final risk score and compile report.
        """
        try:
            urls = message.get("extracted_urls", [])
            
            # 1. Intent Classification
            intent_res = intent_classifier.classify(normalized_text)
            intent = intent_res.get("intent", "unknown")
            
            # 2. Urgency Detection
            urgency_score = urgency_detector.detect(normalized_text)
            
            # 3. Credential Request Detection
            credential_request_detected = credential_request_detector.detect(normalized_text)
            
            # 4. Financial Scam Detection
            financial_scam_prob = financial_scam_detector.detect(normalized_text)
            
            # 5. Brand Impersonation
            impersonation_res = impersonation_detector.detect(normalized_text)
            impersonated_brand = impersonation_res.get("brand")
            
            # 6. Link Context Analysis
            link_context = link_context_analyzer.analyze(normalized_text, urls, impersonated_brand)
            
            # 7. Semantic Similarity
            similarity_res = semantic_similarity_engine.analyze(normalized_text)
            template_similarity = similarity_res.get("template_similarity", 0.0)
            
            # Calculate Base Score (Optimized for High Recall)
            score = 0
            score += int(urgency_score * 30)  # Increased from 25
            if credential_request_detected:
                score += 50
            if impersonated_brand:
                score += 30
            score += int(financial_scam_prob * 35)  # Increased from 30
            score += int(template_similarity * 20)  # Increased from 15
            
            # IDENTITY MISMATCH BOOSTER: If a brand is claimed but the URL doesn't match
            if impersonated_brand and link_context.get("mismatch_detected"):
                score += 40
                logger.info(f"Accuracy Booster: CRITICAL Brand Mismatch for {impersonated_brand} (+40)")
            
            # High-risk intent booster (Account verification or finance)
            if intent in ["account_verification", "financial_payment"]:
                score += 30
                logger.info(f"Accuracy Booster: High-risk intent '{intent}' detected (+30)")
            
            # Link context multiplier (phishing sign)
            if link_context.get("mismatch_detected"):
                score += 25
            
            final_score = min(100, score)
            scam_probability = final_score / 100.0
            
            # Determine category based on signals
            scam_category = "general_phishing"
            if financial_scam_prob > 0.5:
                scam_category = "financial_fraud"
            elif credential_request_detected or intent == "account_verification":
                scam_category = "account_takeover"
                
            if final_score < 40:
                scam_category = None
                
            return {
                "intent": intent,
                "urgency_score": float(urgency_score),
                "impersonated_brand": impersonated_brand,
                "credential_request_detected": credential_request_detected,
                "scam_probability": scam_probability,
                "scam_category": scam_category,
                "score_details": {
                    "message_risk_score": final_score,
                    "financial_scam_prob": float(financial_scam_prob),
                    "template_similarity": float(template_similarity),
                    "mismatch_detected": link_context.get("mismatch_detected", False)
                }
            }
        except Exception as e:
            logger.error(f"Error during message risk evaluation: {e}")
            return {
                "intent": "unknown",
                "urgency_score": 0.0,
                "impersonated_brand": None,
                "credential_request_detected": False,
                "scam_probability": 0.0,
                "scam_category": None,
                "score_details": {
                    "message_risk_score": 0,
                    "financial_scam_prob": 0.0,
                    "template_similarity": 0.0,
                    "mismatch_detected": False
                }
            }

message_risk_engine = MessageRiskEngine()


def calculate_message_risk(normalized_text: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
    """Public module-level function: calculate full risk score for a message."""
    return message_risk_engine.evaluate(normalized_text, message_data)
