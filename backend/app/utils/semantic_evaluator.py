"""
Semantic Answer Evaluator — No LLM required.

Scores a candidate's answer by:
1. Semantic similarity  — cosine similarity between answer and reference embeddings (60%)
2. Keyword coverage     — fraction of key terms from reference found in answer (40%)

Returns a 0-100 score plus structured text feedback.
"""
from __future__ import annotations

import re
import logging
from typing import List, Dict, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stop-words to ignore during keyword extraction
# ---------------------------------------------------------------------------
_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "on", "at", "by", "for", "with", "about",
    "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "from", "up", "down", "out", "off", "over", "under",
    "again", "further", "then", "once", "and", "but", "or", "nor", "so",
    "yet", "both", "either", "neither", "not", "only", "own", "same",
    "than", "too", "very", "just", "because", "as", "until", "while",
    "that", "this", "these", "those", "it", "its", "i", "you", "he",
    "she", "we", "they", "what", "which", "who", "whom", "how", "when",
    "where", "why", "all", "each", "every", "few", "more", "most",
    "other", "some", "such", "no", "any", "if", "then", "else", "when",
}

# Structure words/markers that indicate real sentences vs keyword lists
_STRUCTURE_WORDS = {
    "and", "but", "or", "because", "although", "since", "while", "where",
    "after", "before", "during", "with", "from", "into", "through",
    "about", "between", "under", "over", "above", "below", "that",
    "which", "who", "this", "that", "these", "those", "the", "a", "an",
}


def _tokenize(text: str) -> List[str]:
    """Lowercase, strip punctuation, remove stop-words."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 2]


def _extract_keywords(text: str, top_n: int = 20) -> List[str]:
    """Return the most frequent meaningful tokens as keywords."""
    tokens = _tokenize(text)
    if not tokens:
        return []
    freq: Dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    sorted_tokens = sorted(freq, key=lambda x: freq[x], reverse=True)
    return sorted_tokens[:top_n]


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ---------------------------------------------------------------------------
# Main evaluator class
# ---------------------------------------------------------------------------

class SemanticEvaluator:
    """
    Evaluates interview answers using semantic similarity + keyword coverage.
    Uses the same sentence-transformer model already loaded by the embedder.
    """

    # Weights for the two sub-scores
    SEMANTIC_WEIGHT = 0.60
    KEYWORD_WEIGHT = 0.40

    def __init__(self):
        self._model = None  # lazy-loaded

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            from app.core.config import settings
            model_name = getattr(settings, "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            logger.info(f"Loading embedding model for evaluation: {model_name}")
            self._model = SentenceTransformer(model_name)
        return self._model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        question: str,
        candidate_answer: str,
        reference_contexts: List[Dict],
    ) -> Dict:
        """
        Evaluate a candidate answer against retrieved reference contexts.

        Args:
            question:           The interview question text.
            candidate_answer:   The candidate's answer text.
            reference_contexts: List of retrieved context dicts (each has 'text').

        Returns:
            {
                "score":     float  0-100,
                "feedback":  str    structured feedback,
                "semantic_score":  float 0-100,
                "keyword_score":   float 0-100,
                "matched_keywords": list[str],
                "missing_keywords": list[str],
            }
        """
        if not candidate_answer or not candidate_answer.strip():
            return self._empty_answer_result()

        # Build reference text from retrieved contexts
        reference_text = " ".join(ctx["text"] for ctx in reference_contexts) if reference_contexts else ""

        if not reference_text.strip():
            # No reference — fall back to length/content heuristic
            return self._heuristic_result(candidate_answer)

        # 1. Semantic similarity score
        semantic_score = self._semantic_score(candidate_answer, reference_text)

        # 2. Keyword coverage score
        keywords = _extract_keywords(reference_text, top_n=20)
        answer_tokens = _tokenize(candidate_answer)
        answer_token_set = set(answer_tokens)
        matched = [kw for kw in keywords if kw in answer_token_set]
        missing = [kw for kw in keywords if kw not in answer_token_set]
        raw_keyword_score = (len(matched) / len(keywords) * 100) if keywords else 50.0

        # 3. Quality & Fluency Check (prevent "gaming" the system)
        fluency_score = self._calculate_fluency_score(candidate_answer)
        
        # Penalize keyword stuffing: if technical keywords are too high a percentage of total words,
        # it's likely just a list. (Normal speech is 40-60% structure/stop words)
        total_tokens = len(re.findall(r"[a-z0-9]+", candidate_answer.lower()))
        keyword_density = len(answer_tokens) / total_tokens if total_tokens > 0 else 0
        
        # If density is > 85%, assume it's just a word list
        density_penalty = 1.0
        if keyword_density > 0.85 and total_tokens > 3:
            density_penalty = 0.4 # Significant penalty for word lists
            logger.info(f"Keyword density penalty applied: {keyword_density:.2f}")

        # Combine keyword score with fluency and density
        keyword_score = raw_keyword_score * fluency_score * density_penalty

        # 4. Combined score
        combined = (
            self.SEMANTIC_WEIGHT * semantic_score
            + self.KEYWORD_WEIGHT * keyword_score
        )
        final_score = round(min(max(combined, 0.0), 100.0), 1)

        feedback = self._build_feedback(
            question, candidate_answer, final_score,
            semantic_score, keyword_score, matched, missing
        )

        return {
            "score": final_score,
            "feedback": feedback,
            "semantic_score": round(semantic_score, 1),
            "keyword_score": round(keyword_score, 1),
            "matched_keywords": matched[:10],
            "missing_keywords": missing[:10],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _semantic_score(self, answer: str, reference: str) -> float:
        """Return 0-100 cosine similarity between answer and reference."""
        try:
            model = self._get_model()
            embeddings = model.encode([answer, reference], convert_to_numpy=True)
            sim = _cosine_similarity(embeddings[0], embeddings[1])
            # sim is in [-1, 1]; map to [0, 100]
            return round(max(sim, 0.0) * 100, 2)
        except Exception as e:
            logger.warning(f"Semantic scoring failed: {e}")
            return 50.0

    def _build_feedback(
        self,
        question: str,
        answer: str,
        score: float,
        semantic_score: float,
        keyword_score: float,
        matched: List[str],
        missing: List[str],
    ) -> str:
        """Build a structured, human-readable feedback string."""

        # Grade label
        if score >= 85:
            grade = "Excellent"
            summary = "Your answer demonstrates strong understanding of the topic."
        elif score >= 70:
            grade = "Good"
            summary = "Your answer covers the main points well with minor gaps."
        elif score >= 55:
            grade = "Satisfactory"
            summary = "Your answer addresses the question but lacks some key details."
        elif score >= 40:
            grade = "Needs Improvement"
            summary = "Your answer is partially correct but misses important concepts."
        else:
            grade = "Insufficient"
            summary = "Your answer does not adequately address the question."

        lines = [
            f"SCORE: {score:.0f}/100 — {grade}",
            "",
            f"OVERVIEW: {summary}",
            "",
            f"ANALYSIS:",
            f"  • Semantic relevance: {semantic_score:.0f}/100 — "
            + ("Strong alignment with expected answer." if semantic_score >= 65
               else "Answer diverges from expected concepts."),
            f"  • Concept coverage:   {keyword_score:.0f}/100 — "
            + (f"Covered key terms: {', '.join(matched[:6]) if matched else 'none'}."
               if matched else "No key terms matched."),
        ]

        if missing:
            lines += [
                "",
                f"MISSING CONCEPTS: Consider including — {', '.join(missing[:8])}.",
            ]

        if matched:
            lines += [
                "",
                f"STRENGTHS: You correctly addressed — {', '.join(matched[:6])}.",
            ]

        # Improvement tip based on score band
        lines += ["", "SUGGESTION:"]
        if score < 40:
            lines.append("  Review the fundamentals of this topic and try to structure your answer with a clear definition, explanation, and example.")
        elif score < 60:
            lines.append("  Expand your answer by covering the missing concepts listed above and adding a practical example.")
        elif score < 80:
            lines.append("  Good foundation — deepen your answer by discussing trade-offs, edge cases, or real-world applications.")
        else:
            lines.append("  Excellent answer. To make it perfect, consider mentioning performance implications or advanced use cases.")

        return "\n".join(lines)

    def _calculate_fluency_score(self, text: str) -> float:
        """
        Check if the text looks like real sentences or just a word list.
        Returns a multiplier from 0.5 to 1.0.
        """
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            return 0.5
            
        # Count structure words
        struct_count = sum(1 for t in tokens if t in _STRUCTURE_WORDS)
        struct_ratio = struct_count / len(tokens)
        
        # Check for sentence punctuation
        has_punctuation = bool(re.search(r'[.!?]', text))
        
        # Heuristic: Real sentences usually have > 20% structure words
        if struct_ratio > 0.2:
            return 1.0
        elif struct_ratio > 0.1 or has_punctuation:
            return 0.8
        else:
            return 0.5 # Likely a keyword list

    def _empty_answer_result(self) -> Dict:
        return {
            "score": 0.0,
            "feedback": "SCORE: 0/100 — No Answer\n\nOVERVIEW: No answer was provided.\n\nSUGGESTION: Please provide an answer to receive evaluation.",
            "semantic_score": 0.0,
            "keyword_score": 0.0,
            "matched_keywords": [],
            "missing_keywords": [],
        }

    def _heuristic_result(self, answer: str) -> Dict:
        """Fallback when no reference context is available."""
        tokens = re.findall(r"[a-z0-9]+", answer.lower())
        word_count = len(tokens)
        
        # Check fluency even in heuristic
        fluency = self._calculate_fluency_score(answer)
        
        if word_count < 5:
            base_score = 10.0
        elif word_count < 15:
            base_score = 30.0
        elif word_count < 40:
            base_score = 50.0
        elif word_count < 80:
            base_score = 65.0
        else:
            base_score = 75.0

        score = base_score * fluency
        
        return {
            "score": score,
            "feedback": (
                f"SCORE: {score:.0f}/100\n\n"
                "OVERVIEW: Evaluated based on answer quality and structure (no reference available).\n\n"
                "SUGGESTION: Provide a detailed, coherent answer covering definitions and explanations."
            ),
            "semantic_score": score,
            "keyword_score": score,
            "matched_keywords": [],
            "missing_keywords": [],
        }


# Singleton
semantic_evaluator = SemanticEvaluator()
