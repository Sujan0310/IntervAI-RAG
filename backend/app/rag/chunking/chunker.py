"""
Advanced text chunking strategies for RAG
Implements: Fixed, Semantic, and Recursive chunking
"""
from typing import List, Dict
import re
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class TextChunker:
    """Advanced text chunking with multiple strategies"""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = None
    
    def chunk_text(self, text: str, strategy: str = "semantic", metadata: Dict = None) -> List[Dict]:
        """
        Chunk text using specified strategy
        
        Args:
            text: Input text to chunk
            strategy: Chunking strategy (fixed, semantic, recursive)
            metadata: Additional metadata to attach to chunks
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        if strategy == "fixed":
            chunks = self._fixed_chunking(text)
        elif strategy == "semantic":
            chunks = self._semantic_chunking(text)
        elif strategy == "recursive":
            chunks = self._recursive_chunking(text)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
        
        # Add metadata to chunks
        enriched_chunks = []
        for idx, chunk_text in enumerate(chunks):
            chunk_dict = {
                "text": chunk_text,
                "chunk_id": idx,
                "chunk_size": len(chunk_text),
                "word_count": len(chunk_text.split()),
                "strategy": strategy
            }
            
            if metadata:
                chunk_dict.update(metadata)
            
            enriched_chunks.append(chunk_dict)
        
        return enriched_chunks
    
    def _fixed_chunking(self, text: str) -> List[str]:
        """
        Fixed-size chunking with overlap
        Simple but effective for uniform content
        """
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            
            if chunk_text.strip():
                chunks.append(chunk_text)
        
        return chunks
    
    def _semantic_chunking(self, text: str) -> List[str]:
        """
        Semantic chunking based on sentence similarity
        Groups semantically similar sentences together
        """
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        if len(sentences) <= 1:
            return [text]
        
        # Load embedding model if not loaded
        if self.embedding_model is None:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Compute sentence embeddings
        embeddings = self.embedding_model.encode(sentences)
        
        # Compute similarity between consecutive sentences
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = cosine_similarity(
                embeddings[i].reshape(1, -1),
                embeddings[i + 1].reshape(1, -1)
            )[0][0]
            similarities.append(sim)
        
        # Find split points (low similarity = topic change)
        threshold = np.percentile(similarities, 30)  # Bottom 30% as split points
        split_indices = [0]
        
        for i, sim in enumerate(similarities):
            if sim < threshold:
                split_indices.append(i + 1)
        
        split_indices.append(len(sentences))
        
        # Create chunks from split points
        chunks = []
        for i in range(len(split_indices) - 1):
            start = split_indices[i]
            end = split_indices[i + 1]
            chunk_sentences = sentences[start:end]
            chunk_text = " ".join(chunk_sentences)
            
            # Ensure chunk doesn't exceed max size
            if len(chunk_text.split()) > self.chunk_size:
                # Further split large chunks
                sub_chunks = self._fixed_chunking(chunk_text)
                chunks.extend(sub_chunks)
            else:
                chunks.append(chunk_text)
        
        return chunks
    
    def _recursive_chunking(self, text: str, separators: List[str] = None) -> List[str]:
        """
        Recursive chunking with hierarchical separators
        Tries to split on paragraphs, then sentences, then words
        """
        if separators is None:
            separators = ["\n\n", "\n", ". ", " "]
        
        chunks = []
        
        def _split_recursive(text: str, sep_idx: int = 0):
            if len(text.split()) <= self.chunk_size:
                return [text]
            
            if sep_idx >= len(separators):
                # Fallback to fixed chunking
                return self._fixed_chunking(text)
            
            separator = separators[sep_idx]
            parts = text.split(separator)
            
            result = []
            current_chunk = ""
            
            for part in parts:
                test_chunk = current_chunk + separator + part if current_chunk else part
                
                if len(test_chunk.split()) <= self.chunk_size:
                    current_chunk = test_chunk
                else:
                    if current_chunk:
                        result.append(current_chunk)
                    
                    # If single part is too large, try next separator
                    if len(part.split()) > self.chunk_size:
                        result.extend(_split_recursive(part, sep_idx + 1))
                        current_chunk = ""
                    else:
                        current_chunk = part
            
            if current_chunk:
                result.append(current_chunk)
            
            return result
        
        return _split_recursive(text)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentence_endings = re.compile(r'(?<=[.!?])\s+')
        sentences = sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip()]
    
    def add_overlap(self, chunks: List[str]) -> List[str]:
        """Add overlap between chunks for context continuity"""
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = []
        overlap_words = self.chunk_overlap
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped_chunks.append(chunk)
            else:
                # Add last N words from previous chunk
                prev_words = chunks[i - 1].split()[-overlap_words:]
                current_words = chunk.split()
                overlapped_text = " ".join(prev_words + current_words)
                overlapped_chunks.append(overlapped_text)
        
        return overlapped_chunks
