"""
RAG API endpoints for testing and evaluation
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional

from app.core.security import get_current_active_user
from app.models.user import User
from app.rag.retrieval.hybrid_retriever import HybridRetriever
from app.rag.generation.rag_generator import StrictRAGGenerator

router = APIRouter()

retriever = HybridRetriever()
generator = StrictRAGGenerator()


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10
    use_hybrid: Optional[bool] = True


class GenerateRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


@router.post("/retrieve")
async def retrieve_contexts(
    request: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve relevant contexts for a query"""
    results = retriever.retrieve(
        query=request.query,
        top_k=request.top_k,
        use_hybrid=request.use_hybrid
    )
    
    return {
        "query": request.query,
        "num_results": len(results),
        "results": results
    }


@router.post("/generate")
async def generate_response(
    request: GenerateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Generate RAG response with strict grounding"""
    # Retrieve contexts
    contexts = retriever.retrieve(request.query, top_k=request.top_k)
    
    # Generate response
    result = generator.generate_response(
        query=request.query,
        retrieved_contexts=contexts
    )
    
    return result


@router.get("/health")
async def rag_health_check():
    """Check RAG system health"""
    return {
        "status": "healthy",
        "indexed_documents": len(retriever.documents),
        "strict_rag_mode": True,
        "retrieval_method": "hybrid",
        "llm_type": generator.llm_type
    }
