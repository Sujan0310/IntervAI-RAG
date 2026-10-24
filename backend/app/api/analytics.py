"""
Analytics API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.interview import Interview, InterviewQuestion

router = APIRouter()


@router.get("/performance")
async def get_performance_analytics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user performance analytics"""
    # Get all user interviews
    interviews = db.query(Interview).filter(
        Interview.user_id == current_user.id
    ).all()
    
    # Calculate statistics
    total_interviews = len(interviews)
    completed_interviews = len([i for i in interviews if i.status == "completed"])
    
    # Get all questions
    all_questions = []
    for interview in interviews:
        all_questions.extend(interview.questions)
    
    total_questions = len(all_questions)
    answered_questions = len([q for q in all_questions if q.user_answer])
    
    # Calculate average score
    scores = [q.score for q in all_questions if q.score is not None]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # Domain-wise performance
    domain_stats = {}
    for interview in interviews:
        domain = interview.domain
        if domain not in domain_stats:
            domain_stats[domain] = {
                "count": 0,
                "avg_score": 0,
                "scores": []
            }
        
        domain_stats[domain]["count"] += 1
        interview_scores = [q.score for q in interview.questions if q.score is not None]
        if interview_scores:
            domain_stats[domain]["scores"].extend(interview_scores)
    
    # Calculate domain averages
    for domain in domain_stats:
        scores = domain_stats[domain]["scores"]
        domain_stats[domain]["avg_score"] = sum(scores) / len(scores) if scores else 0
        del domain_stats[domain]["scores"]
    
    return {
        "total_interviews": total_interviews,
        "completed_interviews": completed_interviews,
        "total_questions": total_questions,
        "answered_questions": answered_questions,
        "average_score": round(avg_score, 2),
        "domain_performance": domain_stats
    }


@router.get("/skills")
async def get_skill_analysis(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get skill-based analysis"""
    # Get user's resume
    if current_user.resumes:
        latest_resume = current_user.resumes[-1]
        skills = latest_resume.skills or []
    else:
        skills = []
    
    # Get interview domains
    interviews = db.query(Interview).filter(
        Interview.user_id == current_user.id
    ).all()
    
    domains_covered = list(set([i.domain for i in interviews]))
    
    return {
        "identified_skills": skills,
        "domains_practiced": domains_covered,
        "skill_count": len(skills)
    }
