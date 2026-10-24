"""
Admin API endpoints for document and question management
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pathlib import Path
import os
import re

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.interview import Interview
from app.rag.ingestion.document_processor import DocumentProcessor
from app.rag.chunking.chunker import TextChunker
from app.rag.retrieval.hybrid_retriever import HybridRetriever

router = APIRouter()

doc_processor = DocumentProcessor()
chunker = TextChunker()
retriever = HybridRetriever()

# Knowledge base path
KNOWLEDGE_BASE_PATH = Path("./knowledge_base")


@router.post("/upload/documents")
async def upload_documents(
    files: List[UploadFile] = File(...),
    domain: str = "general",
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Upload and index interview documents (Admin only)"""
    results = []
    all_chunks = []

    for file in files:
        try:
            upload_dir = Path("./data/documents") / domain
            upload_dir.mkdir(parents=True, exist_ok=True)

            file_path = upload_dir / file.filename

            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            processed_doc = doc_processor.process_document(str(file_path))

            chunks = chunker.chunk_text(
                text=processed_doc['text'],
                strategy="semantic",
                metadata={
                    "file_name": file.filename,
                    "domain": domain,
                    "file_type": processed_doc['file_type']
                }
            )

            all_chunks.extend(chunks)

            results.append({
                "filename": file.filename,
                "status": "success",
                "chunks_created": len(chunks)
            })

        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })

    if all_chunks:
        retriever.index_documents(all_chunks)

    return {
        "message": f"Processed {len(files)} files",
        "total_chunks": len(all_chunks),
        "results": results
    }


@router.get("/documents/stats")
async def get_document_stats(
    current_user: User = Depends(get_current_admin_user)
):
    """Get document indexing statistics"""
    return {
        "total_documents": len(retriever.documents),
        "index_type": "hybrid",
        "embedding_model": "local",
        "vector_store": "faiss"
    }


@router.get("/questions/domains")
async def get_domains(
    current_user: User = Depends(get_current_admin_user)
):
    """Get all available domains"""
    domains = []
    if KNOWLEDGE_BASE_PATH.exists():
        for domain_dir in KNOWLEDGE_BASE_PATH.iterdir():
            if domain_dir.is_dir():
                domains.append({
                    "name": domain_dir.name,
                    "display_name": domain_dir.name.replace("-", " ").title()
                })
    return {"domains": domains}


@router.get("/questions/{domain}")
async def get_questions_by_domain(
    domain: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Get all questions from a specific domain"""
    domain_path = KNOWLEDGE_BASE_PATH / domain

    if not domain_path.exists():
        raise HTTPException(status_code=404, detail="Domain not found")

    questions = []

    for file_path in domain_path.glob("*.txt"):
        if file_path.name == "README.txt":
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            questions_in_file = []

            # Format A: "Q1: Question\nA: Answer"
            qa_blocks = re.split(r'\n(?=Q\d+:)', content)
            for block in qa_blocks:
                block = block.strip()
                m = re.match(r'^Q(\d+):\s*(.+?)(?:\nA:\s*(.+))?$', block, re.DOTALL)
                if m:
                    questions_in_file.append({
                        "id": f"{domain}_{file_path.stem}_{m.group(1)}",
                        "number": int(m.group(1)),
                        "question": m.group(2).strip(),
                        "answer": m.group(3).strip() if m.group(3) else "",
                        "file": file_path.name,
                        "domain": domain
                    })

            # Format B: "1. Question\nAnswer" (fallback)
            if not questions_in_file:
                for block in re.split(r'\n\n(?=\d+\.)', content):
                    block = block.strip()
                    if not block or block.startswith(("===", "DOMAIN:", "SECTION")):
                        continue
                    m = re.match(r'^(\d+)\.\s+(.+?)(?:\n(.+))?$', block, re.DOTALL)
                    if m:
                        questions_in_file.append({
                            "id": f"{domain}_{file_path.stem}_{m.group(1)}",
                            "number": int(m.group(1)),
                            "question": m.group(2).strip(),
                            "answer": m.group(3).strip() if m.group(3) else "",
                            "file": file_path.name,
                            "domain": domain
                        })

            questions.extend(questions_in_file)

        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue

    questions.sort(key=lambda x: x["number"])

    return {
        "domain": domain,
        "total_questions": len(questions),
        "questions": questions
    }


@router.post("/questions/{domain}/add")
async def add_question(
    domain: str,
    question_data: Dict = Body(...),
    current_user: User = Depends(get_current_admin_user)
):
    """Add a new question to a domain"""
    domain_path = KNOWLEDGE_BASE_PATH / domain

    if not domain_path.exists():
        raise HTTPException(status_code=404, detail="Domain not found")

    question = question_data.get("question", "").strip()
    answer = question_data.get("answer", "").strip()
    file_name = question_data.get("file", f"{domain}_interview_questions.txt")

    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    file_path = domain_path / file_name

    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find last Q<n>: number
        numbers = re.findall(r'^Q(\d+):', content, re.MULTILINE)
        if not numbers:
            numbers = re.findall(r'^(\d+)\.', content, re.MULTILINE)
        next_number = max([int(n) for n in numbers]) + 1 if numbers else 1
    else:
        content = f"{domain.upper().replace('-', ' ')} INTERVIEW QUESTIONS\n\n"
        next_number = 1

    new_question = f"\nQ{next_number}: {question}\nA: {answer}\n"

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(new_question)

    try:
        processed_doc = doc_processor.process_document(str(file_path))
        chunks = chunker.chunk_text(
            text=processed_doc['text'],
            strategy="semantic",
            metadata={"file_name": file_name, "domain": domain, "file_type": "txt"}
        )
        retriever.index_documents(chunks)
    except Exception as e:
        print(f"Error re-indexing: {e}")

    return {
        "message": "Question added successfully",
        "question_number": next_number,
        "domain": domain
    }


@router.delete("/questions/{domain}/{question_id}")
async def delete_question(
    domain: str,
    question_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a question from a domain"""
    domain_path = KNOWLEDGE_BASE_PATH / domain

    if not domain_path.exists():
        raise HTTPException(status_code=404, detail="Domain not found")

    parts = question_id.split("_")
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="Invalid question ID")

    question_num = int(parts[-1])
    file_name = "_".join(parts[1:-1]) + ".txt"
    file_path = domain_path / file_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Question file not found")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Remove Q<n>: block
    new_content = re.sub(
        r'\nQ' + str(question_num) + r':.*?(?=\nQ\d+:|\Z)',
        '',
        content,
        flags=re.DOTALL
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    try:
        processed_doc = doc_processor.process_document(str(file_path))
        chunks = chunker.chunk_text(
            text=processed_doc['text'],
            strategy="semantic",
            metadata={"file_name": file_name, "domain": domain, "file_type": "txt"}
        )
        retriever.index_documents(chunks)
    except Exception as e:
        print(f"Error re-indexing: {e}")

    return {"message": "Question deleted successfully"}


@router.put("/questions/{domain}/{question_id}")
async def update_question(
    domain: str,
    question_id: str,
    question_data: Dict = Body(...),
    current_user: User = Depends(get_current_admin_user)
):
    """Update an existing question"""
    domain_path = KNOWLEDGE_BASE_PATH / domain

    if not domain_path.exists():
        raise HTTPException(status_code=404, detail="Domain not found")

    parts = question_id.split("_")
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="Invalid question ID")

    question_num = int(parts[-1])
    file_name = "_".join(parts[1:-1]) + ".txt"
    file_path = domain_path / file_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Question file not found")

    new_question = question_data.get("question", "").strip()
    new_answer = question_data.get("answer", "").strip()

    if not new_question:
        raise HTTPException(status_code=400, detail="Question is required")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    replacement = f"\nQ{question_num}: {new_question}\nA: {new_answer}"
    new_content = re.sub(
        r'\nQ' + str(question_num) + r':.*?(?=\nQ\d+:|\Z)',
        replacement,
        content,
        flags=re.DOTALL
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    try:
        processed_doc = doc_processor.process_document(str(file_path))
        chunks = chunker.chunk_text(
            text=processed_doc['text'],
            strategy="semantic",
            metadata={"file_name": file_name, "domain": domain, "file_type": "txt"}
        )
        retriever.index_documents(chunks)
    except Exception as e:
        print(f"Error re-indexing: {e}")

    return {"message": "Question updated successfully"}


@router.get("/users/list")
async def list_users(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all non-admin users (Admin only)"""
    users = db.query(User).filter(User.is_admin == False).all()
    return {
        "total_users": len(users),
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ]
    }


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Enable or disable a user account (Admin only)"""
    user = db.query(User).filter(User.id == user_id, User.is_admin == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = not user.is_active
    db.commit()
    return {"id": user.id, "username": user.username, "is_active": user.is_active}


@router.get("/users/{user_id}/interviews")
async def get_user_interview_history(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get full interview history for a specific user (Admin only)"""
    from app.models.interview import Interview, InterviewQuestion

    user = db.query(User).filter(User.id == user_id, User.is_admin == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == user_id)
        .order_by(Interview.created_at.desc())
        .all()
    )

    result = []
    for iv in interviews:
        questions = (
            db.query(InterviewQuestion)
            .filter(InterviewQuestion.interview_id == iv.id)
            .order_by(InterviewQuestion.created_at)
            .all()
        )
        result.append({
            "id": iv.id,
            "title": iv.title,
            "domain": iv.domain,
            "difficulty": iv.difficulty,
            "status": iv.status,
            "overall_score": iv.overall_score or 0.0,
            "created_at": iv.created_at.isoformat() if iv.created_at else None,
            "completed_at": iv.completed_at.isoformat() if iv.completed_at else None,
            "total_questions": len(questions),
            "answered_questions": len([q for q in questions if q.user_answer]),
            "questions": [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "difficulty": q.difficulty,
                    "score": q.score or 0.0,
                    "user_answer": q.user_answer,
                    "feedback": q.feedback,
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                }
                for q in questions
            ]
        })

    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "interviews": result,
        "total_interviews": len(result),
    }


@router.get("/interviews/stats")
async def get_interview_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get interview statistics"""
    total_interviews = db.query(Interview).count()
    completed_interviews = db.query(Interview).filter(Interview.status == "completed").count()
    active_interviews = db.query(Interview).filter(Interview.status == "active").count()

    domain_stats = {}
    interviews = db.query(Interview).all()
    for interview in interviews:
        domain = interview.domain
        if domain not in domain_stats:
            domain_stats[domain] = 0
        domain_stats[domain] += 1

    return {
        "total_interviews": total_interviews,
        "completed_interviews": completed_interviews,
        "active_interviews": active_interviews,
        "domain_distribution": domain_stats
    }


# ─── Anti-Cheat Settings & Violations ───────────────────────────────────────

@router.get("/anticheat/settings")
async def get_anticheat_settings(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get anti-cheat enabled/disabled setting"""
    from app.models.interview import SystemSetting
    setting = db.query(SystemSetting).filter(SystemSetting.key == "anticheat_enabled").first()
    enabled = setting.value == "true" if setting else False
    return {"anticheat_enabled": enabled}


@router.post("/anticheat/settings")
async def update_anticheat_settings(
    data: dict,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Enable or disable anti-cheat"""
    from app.models.interview import SystemSetting
    from datetime import datetime
    enabled = bool(data.get("anticheat_enabled", False))
    setting = db.query(SystemSetting).filter(SystemSetting.key == "anticheat_enabled").first()
    if setting:
        setting.value = "true" if enabled else "false"
        setting.updated_at = datetime.utcnow()
    else:
        setting = SystemSetting(key="anticheat_enabled", value="true" if enabled else "false")
        db.add(setting)
    db.commit()
    return {"anticheat_enabled": enabled}


@router.get("/anticheat/violations")
async def get_all_violations(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all anti-cheat violations across all users"""
    from app.models.interview import AntiCheatViolation
    violations = (
        db.query(AntiCheatViolation)
        .order_by(AntiCheatViolation.occurred_at.desc())
        .limit(500)
        .all()
    )
    result = []
    for v in violations:
        user = db.query(User).filter(User.id == v.user_id).first()
        from app.models.interview import Interview as InterviewModel
        interview = db.query(InterviewModel).filter(InterviewModel.id == v.interview_id).first()
        result.append({
            "id": v.id,
            "interview_id": v.interview_id,
            "interview_title": interview.title if interview else "Unknown",
            "interview_domain": interview.domain if interview else "",
            "user_id": v.user_id,
            "username": user.username if user else "unknown",
            "violation_type": v.violation_type,
            "details": v.details,
            "occurred_at": v.occurred_at.isoformat() if v.occurred_at else None,
        })
    return {"violations": result, "total": len(result)}


@router.get("/anticheat/violations/{user_id}")
async def get_user_violations(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get violations for a specific user"""
    from app.models.interview import AntiCheatViolation
    violations = (
        db.query(AntiCheatViolation)
        .filter(AntiCheatViolation.user_id == user_id)
        .order_by(AntiCheatViolation.occurred_at.desc())
        .all()
    )
    return {
        "violations": [
            {
                "id": v.id,
                "interview_id": v.interview_id,
                "violation_type": v.violation_type,
                "details": v.details,
                "occurred_at": v.occurred_at.isoformat() if v.occurred_at else None,
            }
            for v in violations
        ],
        "total": len(violations)
    }
