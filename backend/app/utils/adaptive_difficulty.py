"""
Adaptive Difficulty Management
Adjusts interview difficulty based on user performance
"""
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class AdaptiveDifficultyManager:
    """Manages adaptive difficulty adjustment based on answer scores"""
    
    # Difficulty levels in order
    DIFFICULTY_LEVELS = ['easy', 'medium', 'hard']
    
    # Score thresholds for difficulty adjustment
    INCREASE_THRESHOLD = 80  # Score >= 80: increase difficulty
    DECREASE_THRESHOLD = 40  # Score < 40: decrease difficulty
    
    @classmethod
    def calculate_next_difficulty(
        cls,
        current_difficulty: str,
        answer_score: float,
        question_number: int = 1
    ) -> Tuple[str, str]:
        """
        Calculate next question difficulty based on current performance
        
        Args:
            current_difficulty: Current difficulty level (easy/medium/hard)
            answer_score: Score of the last answer (0-100)
            question_number: Current question number (for logging)
            
        Returns:
            Tuple of (next_difficulty, adjustment_reason)
        """
        # Normalize difficulty to lowercase
        current_difficulty = current_difficulty.lower()
        
        # Validate current difficulty
        if current_difficulty not in cls.DIFFICULTY_LEVELS:
            logger.warning(f"Invalid difficulty '{current_difficulty}', defaulting to 'medium'")
            current_difficulty = 'medium'
        
        # Get current difficulty index
        current_index = cls.DIFFICULTY_LEVELS.index(current_difficulty)
        
        # Determine adjustment based on score
        if answer_score >= cls.INCREASE_THRESHOLD:
            # Excellent performance - increase difficulty
            if current_index < len(cls.DIFFICULTY_LEVELS) - 1:
                next_difficulty = cls.DIFFICULTY_LEVELS[current_index + 1]
                reason = f"Excellent answer (score: {answer_score:.1f}) - increasing difficulty"
                logger.info(f"Q{question_number}: {current_difficulty} → {next_difficulty} ({reason})")
                return next_difficulty, reason
            else:
                # Already at highest difficulty
                reason = f"Excellent answer (score: {answer_score:.1f}) - maintaining highest difficulty"
                logger.info(f"Q{question_number}: Staying at {current_difficulty} ({reason})")
                return current_difficulty, reason
                
        elif answer_score < cls.DECREASE_THRESHOLD:
            # Poor performance - decrease difficulty
            if current_index > 0:
                next_difficulty = cls.DIFFICULTY_LEVELS[current_index - 1]
                reason = f"Struggling (score: {answer_score:.1f}) - decreasing difficulty"
                logger.info(f"Q{question_number}: {current_difficulty} → {next_difficulty} ({reason})")
                return next_difficulty, reason
            else:
                # Already at lowest difficulty
                reason = f"Struggling (score: {answer_score:.1f}) - maintaining lowest difficulty"
                logger.info(f"Q{question_number}: Staying at {current_difficulty} ({reason})")
                return current_difficulty, reason
        else:
            # Average performance - maintain difficulty
            reason = f"Good answer (score: {answer_score:.1f}) - maintaining difficulty"
            logger.info(f"Q{question_number}: Staying at {current_difficulty} ({reason})")
            return current_difficulty, reason
    
    @classmethod
    def get_difficulty_description(cls, difficulty: str, score: float = None) -> str:
        """
        Get user-friendly description of difficulty level
        
        Args:
            difficulty: Difficulty level
            score: Optional score that led to this difficulty
            
        Returns:
            User-friendly description
        """
        descriptions = {
            'easy': 'Easy - Fundamental concepts and basic questions',
            'medium': 'Medium - Intermediate topics and practical scenarios',
            'hard': 'Hard - Advanced concepts and complex problem-solving'
        }
        
        base_desc = descriptions.get(difficulty.lower(), 'Medium difficulty')
        
        if score is not None:
            if score >= cls.INCREASE_THRESHOLD:
                return f"{base_desc} (You're doing great! 🎯)"
            elif score < cls.DECREASE_THRESHOLD:
                return f"{base_desc} (Let's build your confidence 💪)"
            else:
                return f"{base_desc} (Keep it up! 👍)"
        
        return base_desc
    
    @classmethod
    def calculate_performance_trend(
        cls,
        recent_scores: list,
        window_size: int = 3
    ) -> str:
        """
        Calculate performance trend over recent questions
        
        Args:
            recent_scores: List of recent scores (most recent last)
            window_size: Number of recent scores to consider
            
        Returns:
            Trend description: 'improving', 'declining', or 'stable'
        """
        if len(recent_scores) < 2:
            return 'stable'
        
        # Get recent window
        window = recent_scores[-window_size:]
        
        if len(window) < 2:
            return 'stable'
        
        # Calculate trend
        first_half_avg = sum(window[:len(window)//2]) / (len(window)//2)
        second_half_avg = sum(window[len(window)//2:]) / (len(window) - len(window)//2)
        
        diff = second_half_avg - first_half_avg
        
        if diff > 10:
            return 'improving'
        elif diff < -10:
            return 'declining'
        else:
            return 'stable'
    
    @classmethod
    def get_encouragement_message(cls, score: float, difficulty: str) -> str:
        """
        Get encouraging message based on performance
        
        Args:
            score: Answer score
            difficulty: Current difficulty level
            
        Returns:
            Encouraging message
        """
        if score >= 90:
            messages = [
                "Outstanding! You're mastering this topic! 🌟",
                "Excellent work! Your understanding is impressive! 🎯",
                "Perfect! You're ready for more challenges! 🚀"
            ]
        elif score >= 80:
            messages = [
                "Great job! You're doing really well! 👏",
                "Very good! Keep up the excellent work! 💪",
                "Nice! You've got a solid grasp of this! ✨"
            ]
        elif score >= 60:
            messages = [
                "Good effort! You're on the right track! 👍",
                "Not bad! Keep practicing and you'll improve! 📈",
                "Decent answer! Let's build on this! 💡"
            ]
        elif score >= 40:
            messages = [
                "Keep trying! You're learning! 🌱",
                "Don't worry, practice makes perfect! 💪",
                "Good attempt! Let's work on this together! 🤝"
            ]
        else:
            messages = [
                "That's okay! Let's try something easier! 🌟",
                "No problem! We'll build your confidence! 💪",
                "Don't give up! Everyone starts somewhere! 🚀"
            ]
        
        # Return first message (can be randomized if needed)
        return messages[0]


# Singleton instance
adaptive_difficulty_manager = AdaptiveDifficultyManager()
