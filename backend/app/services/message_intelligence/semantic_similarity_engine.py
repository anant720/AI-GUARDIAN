from typing import Dict, Any, List
from app.logger import logger
try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    SentenceTransformer = None
    util = None

class SemanticSimilarityEngine:
    def __init__(self):
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.model = None
        self.templates: List[str] = [
            "Your account has been suspended. Verify immediately.",
            "You received a refund. Claim it here.",
            "Reset your password now.",
            "Verify your bank details to avoid account closure.",
            "Click here to claim your prize."
        ]
        self.template_embeddings = None
        
        try:
            if SentenceTransformer is not None:
                self.model = SentenceTransformer(self.model_name)
                self.template_embeddings = self.model.encode(self.templates, convert_to_tensor=True)
        except Exception as e:
            logger.error(f"Failed to load similarity model: {e}")

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Compare the message against known phishing templates.
        Returns the highest similarity score.
        """
        if not text or not self.model or self.template_embeddings is None:
            return {"template_similarity": 0.0}

        try:
            # Generate embedding for the input text
            query_embedding = self.model.encode(text, convert_to_tensor=True)
            
            # Compute cosine similarities
            cosine_scores = util.cos_sim(query_embedding, self.template_embeddings)[0]
            
            # Find the highest score
            highest_score = float(cosine_scores.max())
            
            return {
                "template_similarity": highest_score
            }
        except Exception as e:
            logger.error(f"Error during semantic similarity check: {e}")
            return {"template_similarity": 0.0}

semantic_similarity_engine = SemanticSimilarityEngine()


def compute_template_similarity(text: str) -> Dict[str, Any]:
    """Public module-level function: compute template similarity for a message."""
    return semantic_similarity_engine.analyze(text)
