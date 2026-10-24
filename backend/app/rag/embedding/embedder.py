"""
Embedding service for text vectorization
Supports local and API-based embeddings
"""
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import openai
from app.core.config import settings


class EmbeddingService:
    """Unified embedding service supporting multiple backends"""
    
    def __init__(self):
        self.embedding_type = settings.EMBEDDING_TYPE
        self.model = None
        
        if self.embedding_type == "local":
            self._initialize_local_model()
        elif self.embedding_type == "openai":
            self._initialize_openai()
    
    def _initialize_local_model(self):
        """Initialize local SentenceTransformer model"""
        print(f"Loading local embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"Model loaded. Embedding dimension: {self.embedding_dim}")
    
    def _initialize_openai(self):
        """Initialize OpenAI embeddings"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set for OpenAI embeddings")
        openai.api_key = settings.OPENAI_API_KEY
        self.embedding_dim = 1536  # OpenAI embedding dimension
    
    def embed_text(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for text
        
        Args:
            text: Single text string or list of texts
            
        Returns:
            Numpy array of embeddings
        """
        if isinstance(text, str):
            text = [text]
        
        if self.embedding_type == "local":
            return self._embed_local(text)
        elif self.embedding_type == "openai":
            return self._embed_openai(text)
        else:
            raise ValueError(f"Unknown embedding type: {self.embedding_type}")
    
    def _embed_local(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using local model"""
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True  # L2 normalization for cosine similarity
        )
        return embeddings
    
    def _embed_openai(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using OpenAI API"""
        response = openai.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=texts
        )
        
        embeddings = np.array([item.embedding for item in response.data])
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension"""
        return self.embedding_dim
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score
        """
        # Normalize vectors
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        # Compute cosine similarity
        similarity = np.dot(embedding1, embedding2)
        return float(similarity)
    
    def batch_embed(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Embed texts in batches for efficiency
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            Numpy array of all embeddings
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.embed_text(batch)
            all_embeddings.append(embeddings)
        
        return np.vstack(all_embeddings)
