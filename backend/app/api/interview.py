"""
Interview API endpoints with question pre-generation cache
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import re
import logging

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.interview import Interview, InterviewQuestion, Resume
from app.rag.retrieval.hybrid_retriever import HybridRetriever
from app.rag.generation.rag_generator import StrictRAGGenerator
from app.rag.ingestion.document_processor import DocumentProcessor
from app.services.question_cache import question_cache
from app.utils.score_validation import (
    normalize_confidence_score,
    normalize_retrieval_contexts,
    calculate_average_confidence,
    validate_confidence_score,
    validate_answer_score,
    extract_score_from_llm_response,
    estimate_score_from_answer
)
from app.utils.resume_validator import resume_validator
from app.utils.adaptive_difficulty import adaptive_difficulty_manager
from app.utils.semantic_evaluator import semantic_evaluator
import os
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize RAG components
retriever = HybridRetriever()
generator = StrictRAGGenerator()
doc_processor = DocumentProcessor()


class InterviewCreate(BaseModel):
    title: str
    domain: str
    difficulty: str = "medium"
    resume_id: Optional[int] = None
    eval_mode: str = "semantic"  # semantic or llm


class InterviewResponse(BaseModel):
    id: int
    title: str
    domain: str
    difficulty: str
    status: str
    overall_score: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class QuestionRequest(BaseModel):
    interview_id: int
    domain: str
    difficulty: str


class AnswerSubmit(BaseModel):
    question_id: int
    answer: str


class QuestionResponse(BaseModel):
    id: int
    question_text: str
    question_type: str
    difficulty: str
    retrieved_context: dict
    confidence_score: float

    class Config:
        from_attributes = True


def generate_question_background(
    interview_id: int,
    domain: str,
    difficulty: str,
    count: int = 2
):
    """
    Background task to pre-generate questions
    
    Args:
        interview_id: Interview ID
        domain: Interview domain
        difficulty: Difficulty level
        count: Number of questions to generate
    """
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Mark as generating
        question_cache.set_generating(interview_id, True)
        logger.info(f"Starting background question generation for interview {interview_id}: {count} questions")
        
        # Get previous questions to avoid repetition
        previous_questions = db.query(InterviewQuestion).filter(
            InterviewQuestion.interview_id == interview_id
        ).all()
        prev_q_texts = [q.question_text for q in previous_questions]
        
        # Generate multiple questions
        for i in range(count):
            # Check if cache is full
            if question_cache.get_cache_size(interview_id) >= 3:
                logger.info(f"Cache full for interview {interview_id}, stopping generation")
                break
            
            try:
                # Retrieve relevant context
                query = f"{domain} interview question {difficulty} difficulty"
                logger.debug(f"Retrieving context for query: {query}")
                retrieved_contexts = retriever.retrieve(query, top_k=5)
                
                if not retrieved_contexts:
                    logger.warning(f"No contexts retrieved for interview {interview_id}")
                    continue
                
                # Normalize retrieval scores
                logger.debug(f"Raw retrieval scores: {[ctx.get('score') for ctx in retrieved_contexts]}")
                normalized_contexts = normalize_retrieval_contexts(retrieved_contexts)
                logger.debug(f"Normalized scores: {[ctx.get('score') for ctx in normalized_contexts]}")
                
                # Generate question
                question_text = generator.generate_interview_question(
                    domain=domain,
                    difficulty=difficulty,
                    context=normalized_contexts,
                    previous_questions=prev_q_texts
                )
                
                # Calculate confidence with normalized scores
                avg_confidence = calculate_average_confidence(normalized_contexts)
                
                # Validate confidence score
                avg_confidence = validate_confidence_score(avg_confidence, "background_generation_confidence")
                
                logger.info(f"Generated question {i+1}/{count} with confidence {avg_confidence:.4f}")
                
                # Add to cache (not saved to DB yet)
                question_data = {
                    'question_text': question_text,
                    'difficulty': difficulty,
                    'retrieved_context': {"contexts": normalized_contexts},
                    'confidence_score': avg_confidence,
                    'question_type': 'technical'
                }
                
                question_cache.add_question(interview_id, question_data)
                prev_q_texts.append(question_text)
                
            except Exception as e:
                logger.error(f"Error generating background question {i+1}: {e}", exc_info=True)
                continue
    
    except Exception as e:
        logger.error(f"Fatal error in background generation for interview {interview_id}: {e}", exc_info=True)
    finally:
        # Mark as not generating
        question_cache.set_generating(interview_id, False)
        db.close()
        logger.info(f"Completed background generation for interview {interview_id}")


@router.post("/create", response_model=InterviewResponse)
async def create_interview(
    interview_data: InterviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create new interview session"""
    # Coding Round doesn't require a resume
    is_coding_round = interview_data.domain.lower() == 'coding round'

    if not is_coding_round:
        # Check if user has uploaded resume
        resume_count = db.query(Resume).filter(Resume.user_id == current_user.id).count()
        if resume_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Please upload your resume before starting an interview"
            )
    
    # If resume_id provided, verify it belongs to user
    if interview_data.resume_id:
        resume = db.query(Resume).filter(
            Resume.id == interview_data.resume_id,
            Resume.user_id == current_user.id
        ).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
    
    interview = Interview(
        user_id=current_user.id,
        title=interview_data.title,
        domain=interview_data.domain,
        difficulty=interview_data.difficulty,
        resume_id=interview_data.resume_id,
        eval_mode=interview_data.eval_mode
    )
    
    db.add(interview)
    db.commit()
    db.refresh(interview)
    
    return interview


@router.get("/list", response_model=List[InterviewResponse])
async def list_interviews(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user's interviews"""
    interviews = db.query(Interview).filter(
        Interview.user_id == current_user.id
    ).order_by(Interview.created_at.desc()).all()
    
    return interviews


@router.post("/question/generate", response_model=QuestionResponse)
async def generate_question(
    request: QuestionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate interview question using RAG with caching"""
    logger.info(f"Generating question for interview {request.interview_id}, domain={request.domain}, difficulty={request.difficulty}")
    
    # Verify interview belongs to user
    interview = db.query(Interview).filter(
        Interview.id == request.interview_id,
        Interview.user_id == current_user.id
    ).first()
    
    if not interview:
        logger.warning(f"Interview {request.interview_id} not found for user {current_user.id}")
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Try to get from cache first — only use if difficulty matches current interview difficulty
    cached_question = question_cache.get_question(request.interview_id)
    
    if cached_question and cached_question.get('difficulty') != interview.difficulty:
        logger.info(f"Discarding cached question: difficulty mismatch (cached={cached_question.get('difficulty')}, current={interview.difficulty})")
        question_cache.clear_interview(request.interview_id)
        cached_question = None
    
    if cached_question:
        logger.info(f"Using cached question for interview {request.interview_id}")
        
        # Validate cached confidence score
        confidence = validate_confidence_score(
            cached_question.get('confidence_score', 0.0),
            "cached_question_confidence"
        )
        
        # Use cached question - save to database
        question = InterviewQuestion(
            interview_id=request.interview_id,
            question_text=cached_question['question_text'],
            question_type=cached_question.get('question_type', 'technical'),
            difficulty=cached_question['difficulty'],
            retrieved_context=cached_question['retrieved_context'],
            confidence_score=confidence
        )
        
        db.add(question)
        db.commit()
        db.refresh(question)
        
        logger.info(f"Saved cached question {question.id} with confidence {confidence:.4f}")
        
        # Trigger background generation to refill cache
        if not question_cache.is_generating(request.interview_id):
            background_tasks.add_task(
                generate_question_background,
                request.interview_id,
                request.domain,
                request.difficulty,
                2
            )
        
        return question
    
    # No cached question - generate now
    logger.info(f"No cached question available, generating new question for interview {request.interview_id}")

    # Get previous questions to avoid repetition
    previous_questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == request.interview_id
    ).all()
    prev_q_texts = [q.question_text for q in previous_questions]

    try:
        # Standard RAG flow
        query = f"{request.domain} interview question {request.difficulty} difficulty"
        retrieved_contexts = retriever.retrieve(query, top_k=5)

        if not retrieved_contexts:
            raise HTTPException(
                status_code=400,
                detail="Insufficient context to generate question. Please upload interview materials."
            )

        normalized_contexts = normalize_retrieval_contexts(retrieved_contexts)
        question_text = generator.generate_interview_question(
            domain=request.domain,
            difficulty=request.difficulty,
            context=normalized_contexts,
            previous_questions=prev_q_texts
        )
        avg_confidence = calculate_average_confidence(normalized_contexts)
        avg_confidence = validate_confidence_score(avg_confidence, "generated_question_confidence")
        context_payload = {"contexts": normalized_contexts}
        question_type = "technical"

        logger.info(f"Generated question with confidence {avg_confidence:.4f}")
        
        # Save question
        question = InterviewQuestion(
            interview_id=request.interview_id,
            question_text=question_text,
            question_type=question_type,
            difficulty=request.difficulty,
            retrieved_context=context_payload,
            confidence_score=avg_confidence
        )
        
        db.add(question)
        db.commit()
        db.refresh(question)
        
        logger.info(f"Saved new question {question.id}")
        
        # Trigger background generation for next questions
        if not question_cache.is_generating(request.interview_id):
            background_tasks.add_task(
                generate_question_background,
                request.interview_id,
                request.domain,
                request.difficulty,
                2
            )
        
        return question
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating question for interview {request.interview_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating question: {str(e)}"
        )


@router.post("/answer/submit")
async def submit_answer(
    answer_data: AnswerSubmit,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Submit answer and get evaluation"""
    logger.info(f"Submitting answer for question {answer_data.question_id}")
    
    # Get question
    question = db.query(InterviewQuestion).filter(
        InterviewQuestion.id == answer_data.question_id
    ).first()
    
    if not question:
        logger.warning(f"Question {answer_data.question_id} not found")
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Verify ownership
    interview = db.query(Interview).filter(
        Interview.id == question.interview_id,
        Interview.user_id == current_user.id
    ).first()
    
    if not interview:
        logger.warning(f"Unauthorized access to question {answer_data.question_id} by user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # Check if this is a Coding Round — use LLM evaluation instead of semantic
        is_coding_round = interview.domain.lower() == 'coding round'
        use_llm_eval = is_coding_round or interview.eval_mode == 'llm'

        if use_llm_eval:
            # LLM-based evaluation
            eval_result = generator.evaluate_coding_answer(
                question=question.question_text,
                answer=answer_data.answer
            )
            score = eval_result["score"]
            feedback_text = eval_result["feedback"]
            logger.info(f"LLM evaluation: score={score}")
        else:
            # Retrieve reference context for the question (used by semantic evaluator)
            eval_query = f"{question.question_text}"
            reference_contexts = retriever.retrieve(eval_query, top_k=5)
            normalized_contexts = normalize_retrieval_contexts(reference_contexts) if reference_contexts else []

            # Evaluate using semantic similarity — no LLM needed
            evaluation = semantic_evaluator.evaluate(
                question=question.question_text,
                candidate_answer=answer_data.answer,
                reference_contexts=normalized_contexts,
            )

            score = evaluation["score"]
            feedback_text = evaluation["feedback"]
            logger.info(f"Semantic evaluation: score={score}, semantic={evaluation['semantic_score']}, keyword={evaluation['keyword_score']}")

        # Validate score
        score = validate_answer_score(score, "answer_evaluation_score")
        
        logger.info(f"Answer evaluated with score: {score}")
        
        # Calculate confidence as percentage (0-1 scale)
        confidence = score / 100.0
        confidence = validate_confidence_score(confidence, "answer_confidence")
        
        # Update question
        question.user_answer = answer_data.answer
        question.score = score
        question.feedback = feedback_text
        question.answered_at = datetime.utcnow()
        
        # Calculate adaptive difficulty for next question
        question_count = db.query(InterviewQuestion).filter(
            InterviewQuestion.interview_id == interview.id
        ).count()
        
        next_difficulty, adjustment_reason = adaptive_difficulty_manager.calculate_next_difficulty(
            current_difficulty=interview.difficulty,
            answer_score=score,
            question_number=question_count
        )
        
        # Update interview difficulty if changed
        difficulty_changed = False
        if next_difficulty != interview.difficulty:
            old_difficulty = interview.difficulty
            interview.difficulty = next_difficulty
            difficulty_changed = True
            logger.info(f"Interview {interview.id}: Difficulty adjusted from {old_difficulty} to {next_difficulty}")
        
        # Get encouragement message
        encouragement = adaptive_difficulty_manager.get_encouragement_message(score, next_difficulty)
        
        db.commit()
        
        logger.info(f"Answer saved for question {question.id} with score {score} and confidence {confidence:.4f}")
        
        # Clear stale cached questions (they were generated at old difficulty)
        # then pre-generate at the new adaptive difficulty
        question_cache.clear_interview(interview.id)
        background_tasks.add_task(
            generate_question_background,
            interview.id,
            interview.domain,
            next_difficulty,
            2
        )
        
        return {
            "score": score,
            "feedback": feedback_text,
            "confidence": confidence,
            "citations": [],  # No citations needed for direct evaluation
            "adaptive_difficulty": {
                "current_difficulty": next_difficulty,
                "difficulty_changed": difficulty_changed,
                "adjustment_reason": adjustment_reason,
                "encouragement": encouragement
            }
        }
        
    except Exception as e:
        logger.error(f"Error evaluating answer for question {answer_data.question_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error evaluating answer: {str(e)}"
        )


@router.post("/end/{interview_id}")
async def end_interview(
    interview_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark interview as completed"""
    # Verify interview belongs to user
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Update status
    interview.status = "completed"
    interview.completed_at = datetime.utcnow()
    
    # Calculate overall score from answered questions
    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id,
        InterviewQuestion.user_answer.isnot(None)
    ).all()
    
    if questions:
        avg_score = sum(q.score for q in questions) / len(questions)
        interview.overall_score = avg_score
    
    db.commit()
    db.refresh(interview)
    
    # Clear cache for this interview
    question_cache.clear_interview(interview_id)
    
    return {
        "message": "Interview completed successfully",
        "status": interview.status,
        "overall_score": interview.overall_score
    }


@router.post("/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload and process resume with strict validation"""
    
    # Create upload directory
    upload_dir = Path("./data/uploads") / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize filename
    safe_filename = resume_validator._sanitize_filename(file.filename)
    file_path = upload_dir / safe_filename
    
    # Save file temporarily for validation
    try:
        content = await file.read()
        file_size = len(content)
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Perform comprehensive validation
        is_valid, validation_result = resume_validator.validate_resume(
            str(file_path),
            safe_filename,
            file_size
        )
        
        if not is_valid:
            # Delete invalid file
            if file_path.exists():
                os.remove(file_path)
            
            raise HTTPException(
                status_code=400,
                detail={
                    "error": validation_result.get("error"),
                    "details": validation_result.get("details", []),
                    "message": "Resume validation failed. Please upload a valid resume."
                }
            )
        
        # Process document (validation already extracted text, but we need structured info)
        processed_doc = doc_processor.process_document(str(file_path))
        resume_info = doc_processor.extract_resume_info(processed_doc['text'])
        
        # Save to database
        resume = Resume(
            user_id=current_user.id,
            filename=safe_filename,
            file_path=str(file_path),
            extracted_text=processed_doc['text'],
            skills=resume_info['skills'],
            experience_years=resume_info['experience_years']
        )
        
        db.add(resume)
        db.commit()
        db.refresh(resume)
        
        return {
            "id": resume.id,
            "message": "Resume uploaded and validated successfully",
            "filename": safe_filename,
            "extracted_skills": resume_info['skills'],
            "experience_years": resume_info['experience_years'],
            "validation": {
                "quality_score": validation_result.get("quality_score", 0),
                "word_count": validation_result.get("word_count", 0),
                "detected_sections": validation_result.get("detected_sections", [])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            os.remove(file_path)
        
        logger.error(f"Resume upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process resume: {str(e)}"
        )



@router.get("/resume/{resume_id}/domains")
async def get_resume_domains(
    resume_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Return domains matched from resume skills + always include Coding Round"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    skills = [s.lower() for s in (resume.skills or [])]

    # Map skills → domains
    SKILL_DOMAIN_MAP = {
        'machine learning':  'Machine Learning',
        'deep learning':     'Machine Learning',
        'tensorflow':        'Machine Learning',
        'pytorch':           'Machine Learning',
        'nlp':               'Machine Learning',
        'computer vision':   'Machine Learning',
        'data science':      'Machine Learning',
        'algorithms':        'Data Structures & Algorithms',
        'data structures':   'Data Structures & Algorithms',
        'javascript':        'Web Development',
        'react':             'Web Development',
        'node':              'Web Development',
        'api':               'Web Development',
        'rest':              'Web Development',
        'system design':     'System Design',
        'python':            'Python Programming',
        'sql':               'Databases & SQL',
        'mongodb':           'Databases & SQL',
        'aws':               'Cloud & DevOps',
        'docker':            'Cloud & DevOps',
        'kubernetes':        'Cloud & DevOps',
        'ci/cd':             'Cloud & DevOps',
        'devops':            'Cloud & DevOps',
    }

    matched = set()
    for skill in skills:
        if skill in SKILL_DOMAIN_MAP:
            matched.add(SKILL_DOMAIN_MAP[skill])

    # Always include General + Coding Round
    matched.add('General Interview')
    matched.add('Coding Round')

    all_domains = [
        'Machine Learning', 'Data Structures & Algorithms', 'Web Development',
        'System Design', 'Python Programming', 'Databases & SQL',
        'Cloud & DevOps', 'General Interview', 'Coding Round'
    ]

    return {
        "resume_skills": resume.skills or [],
        "matched_domains": sorted(matched),
        "all_domains": all_domains
    }



@router.post("/resume/manual")
async def create_manual_profile(
    profile_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a resume record from manually selected skills"""
    skills = profile_data.get("skills", [])
    experience_years = profile_data.get("experience_years", 0)
    role = profile_data.get("role", "Software Developer")

    if not skills:
        raise HTTPException(status_code=400, detail="Please select at least one skill")

    # Build a synthetic resume text
    extracted_text = (
        f"Role: {role}\n"
        f"Experience: {experience_years} years\n"
        f"Skills: {', '.join(skills)}\n"
        f"This is a manually created profile for interview preparation."
    )

    resume = Resume(
        user_id=current_user.id,
        filename=f"manual_profile_{role.replace(' ', '_')}.txt",
        file_path="manual",
        extracted_text=extracted_text,
        skills=skills,
        experience_years=float(experience_years)
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {
        "id": resume.id,
        "message": "Manual profile created successfully",
        "filename": resume.filename,
        "extracted_skills": skills,
        "experience_years": experience_years
    }


@router.get("/resume/list")
async def list_resumes(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user's resumes"""
    resumes = db.query(Resume).filter(
        Resume.user_id == current_user.id
    ).order_by(Resume.uploaded_at.desc()).all()
    
    return [{
        "id": r.id,
        "filename": r.filename,
        "skills": r.skills,
        "experience_years": r.experience_years,
        "uploaded_at": r.uploaded_at
    } for r in resumes]


@router.get("/resume/{resume_id}")
async def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get resume details"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    return {
        "id": resume.id,
        "filename": resume.filename,
        "skills": resume.skills,
        "experience_years": resume.experience_years,
        "uploaded_at": resume.uploaded_at,
        "extracted_text": resume.extracted_text[:500] + "..." if len(resume.extracted_text) > 500 else resume.extracted_text
    }


@router.delete("/resume/{resume_id}")
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete resume"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Delete file
    try:
        Path(resume.file_path).unlink(missing_ok=True)
    except Exception:
        pass
    
    db.delete(resume)
    db.commit()
    
    return {"message": "Resume deleted successfully"}


@router.post("/anticheat/report")
async def report_violation(
    data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Report an anti-cheat violation from the frontend"""
    from app.models.interview import AntiCheatViolation, SystemSetting

    # Check if anti-cheat is enabled
    setting = db.query(SystemSetting).filter(SystemSetting.key == "anticheat_enabled").first()
    if not setting or setting.value != "true":
        return {"recorded": False, "reason": "anticheat_disabled"}

    interview_id = data.get("interview_id")
    violation_type = data.get("violation_type", "unknown")
    details = data.get("details", "")

    violation = AntiCheatViolation(
        interview_id=interview_id,
        user_id=current_user.id,
        violation_type=violation_type,
        details=details,
    )
    db.add(violation)
    db.commit()
    return {"recorded": True}


@router.get("/anticheat/status")
async def get_anticheat_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Check if anti-cheat is enabled (for frontend)"""
    from app.models.interview import SystemSetting
    setting = db.query(SystemSetting).filter(SystemSetting.key == "anticheat_enabled").first()
    return {"anticheat_enabled": setting.value == "true" if setting else False}


@router.delete("/delete/{interview_id}")
async def delete_interview(
    interview_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an interview and all its questions"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    question_cache.clear_interview(interview_id)
    db.delete(interview)
    db.commit()
    return {"message": "Interview deleted successfully"}


@router.get("/history/{interview_id}")
async def get_interview_history(
    interview_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get complete interview history with all questions and answers"""
    logger.info(f"Fetching interview history for interview {interview_id}, user {current_user.id}")
    
    # Verify interview belongs to user
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id
    ).first()
    
    if not interview:
        logger.warning(f"Interview {interview_id} not found for user {current_user.id}")
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Get all questions for this interview, ordered by creation time
    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id
    ).order_by(InterviewQuestion.created_at).all()
    
    # Format questions data
    questions_data = []
    for q in questions:
        questions_data.append({
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "user_answer": q.user_answer,
            "score": q.score if q.score is not None else 0.0,
            "feedback": q.feedback,
            "confidence_score": q.confidence_score if q.confidence_score is not None else 0.0,
            "created_at": q.created_at,
            "answered_at": q.answered_at
        })
    
    # Return complete interview history
    return {
        "interview": {
            "id": interview.id,
            "title": interview.title,
            "domain": interview.domain,
            "difficulty": interview.difficulty,
            "status": interview.status,
            "overall_score": interview.overall_score if interview.overall_score is not None else 0.0,
            "created_at": interview.created_at,
            "completed_at": interview.completed_at
        },
        "questions": questions_data,
        "total_questions": len(questions_data),
        "answered_questions": len([q for q in questions_data if q["user_answer"] is not None])
    }
