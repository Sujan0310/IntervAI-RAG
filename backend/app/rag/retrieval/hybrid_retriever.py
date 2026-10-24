"""
Hybrid Retrieval System: Dense (FAISS) + Sparse (BM25) + Cross-Encoder Re-ranking
Implements strict RAG retrieval with source attribution
"""
from typing import List, Dict, Tuple
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
import pickle
from pathlib import Path

from app.core.config import settings
from app.rag.embedding.embedder import EmbeddingService


class HybridRetriever:
    """
    Hybrid retrieval combining dense and sparse methods
    with cross-encoder re-ranking for optimal precision
    """
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.faiss_index = None
        self.bm25_index = None
        self.documents = []
        self.document_metadata = []
        self.cross_encoder = None
        self.index_path = Path(settings.VECTOR_STORE_PATH)
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing index if available
        self._load_index()
    
    def index_documents(self, documents: List[Dict]):
        """
        Index documents for hybrid retrieval
        
        Args:
            documents: List of document dictionaries with 'text' and 'metadata'
        """
        if not documents:
            return
        
        self.documents = [doc['text'] for doc in documents]
        self.document_metadata = [doc.get('metadata', {}) for doc in documents]
        
        # Build dense index (FAISS)
        self._build_dense_index()
        
        # Build sparse index (BM25)
        self._build_sparse_index()
        
        # Save index
        self._save_index()
        
        print(f"Indexed {len(self.documents)} documents")
    
    def _build_dense_index(self):
        """Build FAISS dense vector index"""
        print("Building dense FAISS index...")
        
        # Generate embeddings
        embeddings = self.embedding_service.batch_embed(self.documents)
        embeddings = embeddings.astype('float32')
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.faiss_index = faiss.IndexFlatIP(dimension)  # Inner product for cosine
        self.faiss_index.add(embeddings)
        
        print(f"FAISS index built with {self.faiss_index.ntotal} vectors")
    
    def _build_sparse_index(self):
        """Build BM25 sparse index"""
        print("Building BM25 sparse index...")
        
        # Tokenize documents
        tokenized_docs = [doc.lower().split() for doc in self.documents]
        
        # Create BM25 index
        self.bm25_index = BM25Okapi(tokenized_docs)
        
        print("BM25 index built")
    
    def retrieve(
        self,
        query: str,
        top_k: int = None,
        use_hybrid: bool = None,
        alpha: float = None
    ) -> List[Dict]:
        """
        Retrieve relevant documents using hybrid search
        
        Args:
            query: Search query
            top_k: Number of results to return
            use_hybrid: Whether to use hybrid retrieval
            alpha: Weight for dense vs sparse (0=sparse only, 1=dense only)
            
        Returns:
            List of retrieved documents with scores and metadata
        """
        if top_k is None:
            top_k = settings.TOP_K_RETRIEVAL
        
        if use_hybrid is None:
            use_hybrid = settings.USE_HYBRID_RETRIEVAL
        
        if alpha is None:
            alpha = settings.HYBRID_ALPHA
        
        # If no documents loaded, try reloading from disk (index may have been built after startup)
        if not self.documents:
            self._load_index()
        
        if not self.documents:
            return []
        
        if use_hybrid:
            results = self._hybrid_retrieve(query, top_k, alpha)
        else:
            results = self._dense_retrieve(query, top_k)
        
        # Apply re-ranking if configured
        if settings.RERANK_TOP_K > 0 and len(results) > 0:
            results = self._rerank(query, results)
        
        # Filter by similarity threshold
        results = [
            r for r in results
            if r['score'] >= settings.SIMILARITY_THRESHOLD
        ]
        
        return results[:top_k]
    
    def _dense_retrieve(self, query: str, top_k: int) -> List[Dict]:
        """Dense retrieval using FAISS"""
        if self.faiss_index is None:
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        query_embedding = query_embedding.astype('float32').reshape(1, -1)
        faiss.normalize_L2(query_embedding)
        
        # Search FAISS index
        scores, indices = self.faiss_index.search(query_embedding, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.documents):
                results.append({
                    'text': self.documents[idx],
                    'score': float(score),
                    'metadata': self.document_metadata[idx],
                    'retrieval_method': 'dense'
                })
        
        return results
    
    def _sparse_retrieve(self, query: str, top_k: int) -> List[Dict]:
        """Sparse retrieval using BM25"""
        if self.bm25_index is None:
            return []
        
        # Tokenize query
        query_tokens = query.lower().split()
        
        # Get BM25 scores
        scores = self.bm25_index.get_scores(query_tokens)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if idx < len(self.documents):
                results.append({
                    'text': self.documents[idx],
                    'score': float(scores[idx]),
                    'metadata': self.document_metadata[idx],
                    'retrieval_method': 'sparse'
                })
        
        return results
    
    def _hybrid_retrieve(self, query: str, top_k: int, alpha: float) -> List[Dict]:
        """
        Hybrid retrieval combining dense and sparse methods
        Uses Reciprocal Rank Fusion (RRF)
        """
        # Get results from both methods
        dense_results = self._dense_retrieve(query, top_k * 2)
        sparse_results = self._sparse_retrieve(query, top_k * 2)
        
        # Reciprocal Rank Fusion
        k = 60  # RRF constant
        doc_scores = {}
        
        # Add dense scores
        for rank, result in enumerate(dense_results):
            doc_text = result['text']
            rrf_score = alpha / (k + rank + 1)
            doc_scores[doc_text] = doc_scores.get(doc_text, 0) + rrf_score
        
        # Add sparse scores
        for rank, result in enumerate(sparse_results):
            doc_text = result['text']
            rrf_score = (1 - alpha) / (k + rank + 1)
            doc_scores[doc_text] = doc_scores.get(doc_text, 0) + rrf_score
        
        # Sort by combined score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Build result list
        results = []
        for doc_text, score in sorted_docs[:top_k]:
            # Find metadata
            idx = self.documents.index(doc_text)
            results.append({
                'text': doc_text,
                'score': float(score),
                'metadata': self.document_metadata[idx],
                'retrieval_method': 'hybrid'
            })
        
        return results
    
    def _rerank(self, query: str, results: List[Dict]) -> List[Dict]:
        """
        Re-rank results using cross-encoder for better precision
        """
        if not results:
            return results
        
        # Load cross-encoder if not loaded
        if self.cross_encoder is None:
            print("Loading cross-encoder for re-ranking...")
            self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        # Prepare pairs for cross-encoder
        pairs = [[query, result['text']] for result in results]
        
        # Get cross-encoder scores
        ce_scores = self.cross_encoder.predict(pairs)
        
        # Update scores
        for result, ce_score in zip(results, ce_scores):
            result['rerank_score'] = float(ce_score)
            result['original_score'] = result['score']
            result['score'] = float(ce_score)
        
        # Sort by new scores
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:settings.RERANK_TOP_K]
    
    def _save_index(self):
        """Save index to disk"""
        # Save FAISS index
        if self.faiss_index is not None:
            faiss_path = self.index_path / "faiss.index"
            faiss.write_index(self.faiss_index, str(faiss_path))
        
        # Save BM25 and documents
        data = {
            'bm25_index': self.bm25_index,
            'documents': self.documents,
            'document_metadata': self.document_metadata
        }
        
        data_path = self.index_path / "retrieval_data.pkl"
        with open(data_path, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"Index saved to {self.index_path}")
    
    def _load_index(self):
        """Load index from disk"""
        try:
            # Load FAISS index
            faiss_path = self.index_path / "faiss.index"
            if faiss_path.exists():
                self.faiss_index = faiss.read_index(str(faiss_path))
            
            # Load BM25 and documents
            data_path = self.index_path / "retrieval_data.pkl"
            if data_path.exists():
                with open(data_path, 'rb') as f:
                    data = pickle.load(f)
                    self.bm25_index = data['bm25_index']
                    self.documents = data['documents']
                    self.document_metadata = data['document_metadata']
                
                print(f"Loaded index with {len(self.documents)} documents")
        except Exception as e:
            print(f"Could not load existing index: {e}")
    
    def compute_retrieval_metrics(self, query: str, relevant_docs: List[str], k: int = 10) -> Dict:
        """
        Compute retrieval evaluation metrics
        
        Args:
            query: Search query
            relevant_docs: List of ground truth relevant document texts
            k: Top-k for metrics
            
        Returns:
            Dictionary with precision, recall, MRR, NDCG
        """
        retrieved = self.retrieve(query, top_k=k)
        retrieved_texts = [r['text'] for r in retrieved]
        
        # Precision@K
        relevant_retrieved = len(set(retrieved_texts) & set(relevant_docs))
        precision = relevant_retrieved / len(retrieved_texts) if retrieved_texts else 0
        
        # Recall@K
        recall = relevant_retrieved / len(relevant_docs) if relevant_docs else 0
        
        # Mean Reciprocal Rank (MRR)
        mrr = 0
        for i, doc in enumerate(retrieved_texts):
            if doc in relevant_docs:
                mrr = 1 / (i + 1)
                break
        
        # NDCG@K (simplified)
        dcg = sum([1 / np.log2(i + 2) for i, doc in enumerate(retrieved_texts) if doc in relevant_docs])
        idcg = sum([1 / np.log2(i + 2) for i in range(min(len(relevant_docs), k))])
        ndcg = dcg / idcg if idcg > 0 else 0
        
        return {
            'precision@k': precision,
            'recall@k': recall,
            'mrr': mrr,
            'ndcg@k': ndcg
        }
