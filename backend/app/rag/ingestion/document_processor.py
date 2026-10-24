"""
Document ingestion and processing module
Handles PDF, DOCX, and TXT file parsing
"""
import os
from typing import Dict, List, Optional
from pathlib import Path
import pypdf
import docx
import pdfplumber
import re
from datetime import datetime


class DocumentProcessor:
    """Process and extract text from various document formats"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.docx', '.txt']
    
    def process_document(self, file_path: str) -> Dict:
        """
        Process document and extract text with metadata
        
        Args:
            file_path: Path to document file
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_ext = file_path.suffix.lower()
        
        if file_ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Extract text based on file type
        if file_ext == '.pdf':
            text = self._extract_from_pdf(file_path)
        elif file_ext == '.docx':
            text = self._extract_from_docx(file_path)
        elif file_ext == '.txt':
            text = self._extract_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported format: {file_ext}")
        
        # Clean and normalize text
        text = self._clean_text(text)
        
        # Extract metadata
        metadata = self._extract_metadata(file_path, text)
        
        return {
            "text": text,
            "metadata": metadata,
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_ext,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    def _extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF using pdfplumber for better accuracy"""
        text_parts = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
        except Exception as e:
            # Fallback to pypdf
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = pypdf.PdfReader(file)
                    for page in pdf_reader.pages:
                        text_parts.append(page.extract_text())
            except Exception as fallback_error:
                raise Exception(f"Failed to extract PDF: {e}, Fallback error: {fallback_error}")
        
        return "\n\n".join(text_parts)
    
    def _extract_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX"""
        doc = docx.Document(file_path)
        text_parts = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
        
        # Extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text for cell in row.cells)
                if row_text.strip():
                    text_parts.append(row_text)
        
        return "\n\n".join(text_parts)
    
    def _extract_from_txt(self, file_path: Path) -> str:
        """Extract text from TXT"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-\'"]+', '', text)
        
        # Normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    def _extract_metadata(self, file_path: Path, text: str) -> Dict:
        """Extract metadata from document"""
        return {
            "file_name": file_path.name,
            "file_size": os.path.getsize(file_path),
            "file_extension": file_path.suffix,
            "word_count": len(text.split()),
            "char_count": len(text),
            "created_at": datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
            "modified_at": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        }
    
    def extract_resume_info(self, text: str) -> Dict:
        """
        Extract structured information from resume text
        
        Args:
            text: Resume text content
            
        Returns:
            Dictionary with extracted resume information
        """
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Extract phone numbers
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, text)
        
        # Extract skills (common technical skills)
        skill_keywords = [
            'python', 'java', 'javascript', 'react', 'node', 'sql', 'mongodb',
            'aws', 'docker', 'kubernetes', 'machine learning', 'deep learning',
            'tensorflow', 'pytorch', 'nlp', 'computer vision', 'data science',
            'algorithms', 'data structures', 'system design', 'api', 'rest',
            'git', 'agile', 'scrum', 'ci/cd', 'devops'
        ]
        
        text_lower = text.lower()
        found_skills = [skill for skill in skill_keywords if skill in text_lower]
        
        # Extract experience years (rough estimation)
        experience_pattern = r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience)?'
        experience_matches = re.findall(experience_pattern, text_lower)
        experience_years = max([int(exp) for exp in experience_matches], default=0)
        
        return {
            "emails": emails,
            "phones": [phone[0] if isinstance(phone, tuple) else phone for phone in phones],
            "skills": found_skills,
            "experience_years": experience_years,
            "has_education": any(keyword in text_lower for keyword in ['bachelor', 'master', 'phd', 'degree', 'university'])
        }
