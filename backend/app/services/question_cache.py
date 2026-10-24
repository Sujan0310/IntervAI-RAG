"""
Question Pre-generation Cache Service
Generates questions in advance to reduce wait time
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
from threading import Thread
import time
import logging

logger = logging.getLogger(__name__)


class QuestionCache:
    """
    In-memory cache for pre-generated questions
    Stores questions by interview_id
    """
    
    def __init__(self):
        self._cache: Dict[int, List[Dict]] = {}
        self._generation_tasks: Dict[int, bool] = {}
        self._max_cache_size = 3  # Pre-generate up to 3 questions
        self._cache_ttl = timedelta(minutes=30)  # Cache expires after 30 minutes
    
    def get_question(self, interview_id: int) -> Optional[Dict]:
        """
        Get a pre-generated question from cache
        
        Args:
            interview_id: Interview ID
            
        Returns:
            Pre-generated question dict or None
        """
        if interview_id not in self._cache:
            return None
        
        questions = self._cache[interview_id]
        if not questions:
            return None
        
        # Get first question and remove from cache
        question = questions.pop(0)
        
        # Check if expired
        if 'generated_at' in question:
            generated_at = question['generated_at']
            if datetime.utcnow() - generated_at > self._cache_ttl:
                # Expired, return None
                return None
        
        return question
    
    def add_question(self, interview_id: int, question_data: Dict):
        """
        Add a pre-generated question to cache
        
        Args:
            interview_id: Interview ID
            question_data: Question data dict
        """
        from app.utils.score_validation import validate_confidence_score
        
        if interview_id not in self._cache:
            self._cache[interview_id] = []
        
        # Validate confidence score before caching
        if 'confidence_score' in question_data:
            original_score = question_data['confidence_score']
            validated_score = validate_confidence_score(original_score, "cache_confidence")
            question_data['confidence_score'] = validated_score
            
            if original_score != validated_score:
                logger.warning(
                    f"Confidence score adjusted in cache: {original_score:.4f} -> {validated_score:.4f}"
                )
        
        # Add timestamp
        question_data['generated_at'] = datetime.utcnow()
        
        # Add to cache if not full
        if len(self._cache[interview_id]) < self._max_cache_size:
            self._cache[interview_id].append(question_data)
            logger.info(
                f"Added question to cache for interview {interview_id}, "
                f"cache size: {len(self._cache[interview_id])}/{self._max_cache_size}"
            )
    
    def get_cache_size(self, interview_id: int) -> int:
        """Get number of cached questions for interview"""
        if interview_id not in self._cache:
            return 0
        return len(self._cache[interview_id])
    
    def is_generating(self, interview_id: int) -> bool:
        """Check if questions are being generated for interview"""
        return self._generation_tasks.get(interview_id, False)
    
    def set_generating(self, interview_id: int, status: bool):
        """Set generation status for interview"""
        self._generation_tasks[interview_id] = status
    
    def clear_interview(self, interview_id: int):
        """Clear all cached questions for interview"""
        if interview_id in self._cache:
            del self._cache[interview_id]
        if interview_id in self._generation_tasks:
            del self._generation_tasks[interview_id]
    
    def cleanup_expired(self):
        """Remove expired questions from cache"""
        now = datetime.utcnow()
        for interview_id in list(self._cache.keys()):
            questions = self._cache[interview_id]
            # Filter out expired questions
            self._cache[interview_id] = [
                q for q in questions
                if 'generated_at' in q and (now - q['generated_at']) <= self._cache_ttl
            ]
            # Remove empty caches
            if not self._cache[interview_id]:
                del self._cache[interview_id]


# Global cache instance
question_cache = QuestionCache()
