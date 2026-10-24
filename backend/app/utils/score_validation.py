"""
Score Validation and Normalization Utilities
Handles confidence score normalization and validation across different retrieval methods
"""
import logging
from typing import Union, List, Dict

logger = logging.getLogger(__name__)


def normalize_confidence_score(
    score: float,
    method: str = "unknown",
    min_val: float = None,
    max_val: float = None
) -> float:
    """
    Normalize confidence scores from different retrieval methods to 0-1 range
    
    Args:
        score: Raw score from retrieval method
        method: Retrieval method ('rrf', 'bm25', 'faiss', 'dense', 'sparse', 'hybrid')
        min_val: Optional minimum value for custom normalization
        max_val: Optional maximum value for custom normalization
        
    Returns:
        Normalized score in 0-1 range
    """
    try:
        # Handle None or invalid scores
        if score is None or not isinstance(score, (int, float)):
            logger.warning(f"Invalid score type: {type(score)}, defaulting to 0.0")
            return 0.0
        
        # Handle NaN or infinity
        if not (-float('inf') < score < float('inf')):
            logger.warning(f"Invalid score value: {score}, defaulting to 0.0")
            return 0.0
        
        method = method.lower()
        
        # Custom range normalization
        if min_val is not None and max_val is not None:
            if max_val == min_val:
                return 0.5  # Avoid division by zero
            normalized = (score - min_val) / (max_val - min_val)
            normalized = max(0.0, min(1.0, normalized))
            logger.debug(f"Custom normalization: {score} -> {normalized} (range: {min_val}-{max_val})")
            return normalized
        
        # RRF (Reciprocal Rank Fusion) scores: typically 0.001 to 0.02
        if method in ['rrf', 'hybrid']:
            # RRF formula: 1/(k + rank), where k=60, rank starts at 0
            # Max score: 1/60 ≈ 0.0167
            # Min score: 1/120 ≈ 0.0083 (for top 60 results)
            # We'll normalize assuming max RRF score of 0.02
            normalized = min(score / 0.02, 1.0)
            logger.debug(f"RRF normalization: {score} -> {normalized}")
            return max(0.0, normalized)
        
        # BM25 scores: typically 0 to 15+ (unbounded)
        elif method in ['bm25', 'sparse']:
            # BM25 scores are unbounded but typically 0-15 for relevant docs
            # We'll use a sigmoid-like normalization
            # Assume scores > 10 are highly relevant
            if score <= 0:
                return 0.0
            # Normalize with soft cap at 10
            normalized = min(score / 10.0, 1.0)
            logger.debug(f"BM25 normalization: {score} -> {normalized}")
            return normalized
        
        # FAISS cosine similarity: -1 to 1, but typically 0 to 1 for normalized vectors
        elif method in ['faiss', 'dense', 'cosine']:
            # If score is already in 0-1 range, just clamp it
            if 0 <= score <= 1:
                logger.debug(f"FAISS normalization: {score} -> {score} (already normalized)")
                return score
            # If score is in -1 to 1 range, shift to 0-1
            elif -1 <= score <= 1:
                normalized = (score + 1) / 2
                logger.debug(f"FAISS normalization: {score} -> {normalized} (shifted from -1,1)")
                return normalized
            # If score is > 1, it might be dot product, normalize by clamping
            else:
                normalized = min(max(score, 0.0), 1.0)
                logger.debug(f"FAISS normalization: {score} -> {normalized} (clamped)")
                return normalized
        
        # Unknown method - assume 0-1 range and clamp
        else:
            logger.warning(f"Unknown retrieval method: {method}, assuming 0-1 range")
            normalized = max(0.0, min(1.0, score))
            return normalized
            
    except Exception as e:
        logger.error(f"Error normalizing score {score} with method {method}: {e}")
        return 0.0


def normalize_retrieval_contexts(contexts: List[Dict]) -> List[Dict]:
    """
    Normalize confidence scores in a list of retrieved contexts
    
    Args:
        contexts: List of context dicts with 'score' and 'retrieval_method' keys
        
    Returns:
        List of contexts with normalized scores
    """
    if not contexts:
        return contexts
    
    normalized_contexts = []
    for ctx in contexts:
        if not isinstance(ctx, dict):
            logger.warning(f"Invalid context type: {type(ctx)}, skipping")
            continue
        
        # Create a copy to avoid modifying original
        normalized_ctx = ctx.copy()
        
        # Get retrieval method
        method = ctx.get('retrieval_method', 'unknown')
        
        # Normalize score
        raw_score = ctx.get('score', 0.0)
        normalized_score = normalize_confidence_score(raw_score, method)
        
        # Store both raw and normalized scores
        normalized_ctx['raw_score'] = raw_score
        normalized_ctx['score'] = normalized_score
        
        logger.debug(f"Context normalized: method={method}, raw={raw_score:.4f}, normalized={normalized_score:.4f}")
        
        normalized_contexts.append(normalized_ctx)
    
    return normalized_contexts


def calculate_average_confidence(contexts: List[Dict]) -> float:
    """
    Calculate average confidence from normalized contexts
    
    Args:
        contexts: List of context dicts with normalized 'score' values
        
    Returns:
        Average confidence score (0-1)
    """
    if not contexts:
        logger.warning("No contexts provided for confidence calculation")
        return 0.0
    
    # Normalize contexts first
    normalized_contexts = normalize_retrieval_contexts(contexts)
    
    # Calculate average
    scores = [ctx.get('score', 0.0) for ctx in normalized_contexts]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    
    # Validate result
    avg_score = max(0.0, min(1.0, avg_score))
    
    logger.info(f"Average confidence calculated: {avg_score:.4f} from {len(contexts)} contexts")
    
    return avg_score


def validate_confidence_score(score: float, field_name: str = "confidence") -> float:
    """
    Validate and clamp confidence score to 0-1 range
    
    Args:
        score: Confidence score to validate
        field_name: Name of field for logging
        
    Returns:
        Valid confidence score (0-1)
    """
    if score is None:
        logger.warning(f"{field_name} is None, defaulting to 0.0")
        return 0.0
    
    if not isinstance(score, (int, float)):
        logger.error(f"{field_name} has invalid type {type(score)}, defaulting to 0.0")
        return 0.0
    
    if not (-float('inf') < score < float('inf')):
        logger.error(f"{field_name} has invalid value {score}, defaulting to 0.0")
        return 0.0
    
    # Clamp to 0-1 range
    if score < 0.0 or score > 1.0:
        logger.warning(f"{field_name} out of range: {score}, clamping to 0-1")
        score = max(0.0, min(1.0, score))
    
    return score


def validate_answer_score(score: float, field_name: str = "answer_score") -> float:
    """
    Validate and clamp answer score to 0-100 range
    
    Args:
        score: Answer score to validate
        field_name: Name of field for logging
        
    Returns:
        Valid answer score (0-100)
    """
    if score is None:
        logger.warning(f"{field_name} is None, defaulting to 0.0")
        return 0.0
    
    if not isinstance(score, (int, float)):
        logger.error(f"{field_name} has invalid type {type(score)}, defaulting to 0.0")
        return 0.0
    
    if not (-float('inf') < score < float('inf')):
        logger.error(f"{field_name} has invalid value {score}, defaulting to 0.0")
        return 0.0
    
    # Clamp to 0-100 range
    if score < 0.0 or score > 100.0:
        logger.warning(f"{field_name} out of range: {score}, clamping to 0-100")
        score = max(0.0, min(100.0, score))
    
    return score


def extract_score_from_llm_response(response: str, default_score: float = 50.0) -> float:
    """
    Extract score from LLM response with multiple fallback patterns
    
    Args:
        response: LLM response text
        default_score: Default score if extraction fails
        
    Returns:
        Extracted score (0-100)
    """
    import re
    
    if not response or not isinstance(response, str):
        logger.warning("Invalid LLM response for score extraction")
        return default_score
    
    # Try multiple patterns in order of specificity
    patterns = [
        r'SCORE:\s*(-?\d+(?:\.\d+)?)',           # "SCORE: 75" or "SCORE: -10"
        r'Score:\s*(-?\d+(?:\.\d+)?)',           # "Score: 75"
        r'score:\s*(-?\d+(?:\.\d+)?)',           # "score: 75"
        r'SCORE\s*=\s*(-?\d+(?:\.\d+)?)',        # "SCORE = 75"
        r'Score\s*=\s*(-?\d+(?:\.\d+)?)',        # "Score = 75"
        r'score\s*=\s*(-?\d+(?:\.\d+)?)',        # "score = 75"
        r'(\d+(?:\.\d+)?)\s*/\s*100',            # "75/100"
        r'(\d+(?:\.\d+)?)\s*out of\s*100',       # "75 out of 100"
        r'(\d+(?:\.\d+)?)\s*%',                  # "75%"
        r'rating:\s*(-?\d+(?:\.\d+)?)',          # "rating: 75"
        r'Rating:\s*(-?\d+(?:\.\d+)?)',          # "Rating: 75"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            try:
                score = float(match.group(1))
                # Validate range - clamp if out of range
                if score < 0:
                    logger.warning(f"Extracted score {score} is negative, clamping to 0")
                    return 0.0
                elif score > 100:
                    logger.warning(f"Extracted score {score} exceeds 100, clamping to 100")
                    return 100.0
                else:
                    logger.info(f"Extracted score {score} using pattern: {pattern}")
                    return score
            except (ValueError, IndexError) as e:
                logger.warning(f"Error parsing score from match: {e}")
                continue
    
    # Fallback: find first number in 0-100 range (but not negative numbers)
    numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', response)
    for num_str in numbers:
        try:
            num = float(num_str)
            if 0 <= num <= 100:
                logger.info(f"Extracted score {num} using fallback number search")
                return num
        except ValueError:
            continue
    
    # Final fallback: estimate from answer length
    logger.warning(f"Could not extract score from response, using default: {default_score}")
    return default_score


def estimate_score_from_answer(answer: str, question: str = "") -> float:
    """
    Estimate answer score based on heuristics when LLM extraction fails
    
    Args:
        answer: User's answer text
        question: Question text (optional, for context)
        
    Returns:
        Estimated score (0-100)
    """
    if not answer or not isinstance(answer, str):
        return 0.0
    
    answer = answer.strip()
    
    # Very short answers
    if len(answer) < 10:
        return 10.0
    
    # Calculate based on word count
    words = answer.split()
    word_count = len(words)
    
    # Base score from length (capped at 50)
    length_score = min(word_count * 2, 50)
    
    # Bonus for technical keywords
    technical_keywords = [
        'algorithm', 'complexity', 'data structure', 'function', 'class',
        'method', 'variable', 'loop', 'condition', 'array', 'list',
        'tree', 'graph', 'hash', 'sort', 'search', 'time', 'space',
        'optimize', 'efficient', 'performance', 'scalable', 'design'
    ]
    
    keyword_count = sum(1 for keyword in technical_keywords if keyword in answer.lower())
    keyword_score = min(keyword_count * 5, 30)
    
    # Bonus for code-like content
    code_indicators = ['()', '{}', '[]', '==', '!=', '<=', '>=', 'return', 'if', 'for', 'while']
    code_count = sum(1 for indicator in code_indicators if indicator in answer)
    code_score = min(code_count * 3, 20)
    
    total_score = length_score + keyword_score + code_score
    total_score = min(total_score, 100.0)
    
    logger.info(f"Estimated score: {total_score} (length={length_score}, keywords={keyword_score}, code={code_score})")
    
    return total_score
