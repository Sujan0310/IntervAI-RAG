"""
Strict Resume Upload Validation Module
Ensures only legitimate, high-quality resumes are accepted
"""
import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pypdf
import docx
import pdfplumber
from collections import Counter
import hashlib

# Try to import magic, but make it optional
try:
    import magic
    MAGIC_AVAILABLE = True
except (ImportError, OSError):
    MAGIC_AVAILABLE = False


class ResumeValidator:
    """Comprehensive resume validation with strict quality checks"""
    
    # File constraints
    MIN_FILE_SIZE = 1 * 1024  # 1KB
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx']
    
    # Content constraints
    MIN_WORD_COUNT = 100
    MIN_SECTION_WORDS = 10
    
    # Resume sections to detect
    REQUIRED_SECTIONS = {
        'education': [
            r'\b(?:education|academic|qualification|degree)\b',
            r'\b(?:bachelor|master|phd|b\.?tech|m\.?tech|b\.?sc|m\.?sc)\b'
        ],
        'experience': [
            r'\b(?:experience|employment|work\s+history|professional\s+experience)\b',
            r'\b(?:worked|employed|position|role)\b'
        ],
        'skills': [
            r'\b(?:skills|technical\s+skills|competencies|expertise)\b',
            r'\b(?:proficient|experienced\s+in|knowledge\s+of)\b'
        ],
        'projects': [
            r'\b(?:projects|portfolio|work\s+samples)\b',
            r'\b(?:developed|built|created|implemented)\b'
        ],
        'certifications': [
            r'\b(?:certifications?|certificates?|licenses?)\b',
            r'\b(?:certified|licensed)\b'
        ],
        'summary': [
            r'\b(?:summary|profile|objective|about\s+me)\b',
            r'\b(?:professional\s+summary|career\s+objective)\b'
        ]
    }
    
    # Spam patterns
    SPAM_PATTERNS = [
        r'(.)\1{10,}',  # Repeated characters
        r'\b(lorem\s+ipsum|placeholder|coming\s+soon|n/?a|tbd|xxx)\b',
        r'asdf+|qwert+|zxcv+',  # Keyboard mashing
        r'\b(test|sample|dummy|fake)\s+(resume|cv|document)\b',
        r'(?:click|buy|visit|download)\s+(?:here|now)',  # Spam keywords
        r'(?:act\s+now|limited\s+time|special\s+offer)',
    ]
    
    def __init__(self):
        """Initialize validator"""
        self.validation_errors = []
    
    def validate_resume(self, file_path: str, filename: str, file_size: int) -> Tuple[bool, Dict]:
        """
        Comprehensive resume validation
        
        Args:
            file_path: Path to uploaded file
            filename: Original filename
            file_size: File size in bytes
            
        Returns:
            Tuple of (is_valid, validation_result)
        """
        self.validation_errors = []
        
        try:
            # 1. File type validation
            if not self._validate_file_type(filename, file_path):
                return False, self._build_error_response("Invalid file type")
            
            # 2. File size validation
            if not self._validate_file_size(file_size):
                return False, self._build_error_response("Invalid file size")
            
            # 3. Security checks
            if not self._validate_security(file_path, filename):
                return False, self._build_error_response("Security validation failed")
            
            # 4. Extract text content
            text = self._extract_text(file_path, filename)
            if not text:
                return False, self._build_error_response("Failed to extract text from document")
            
            # 5. Text readability check
            if not self._validate_readability(text):
                return False, self._build_error_response("Document is not readable or contains insufficient content")
            
            # 6. Word count validation
            if not self._validate_word_count(text):
                return False, self._build_error_response(f"Document must contain at least {self.MIN_WORD_COUNT} meaningful words")
            
            # 7. Spam/rubbish detection
            if not self._validate_no_spam(text):
                return False, self._build_error_response("Document contains spam or invalid content")
            
            # 8. Section validation (strict)
            if not self._validate_sections(text):
                return False, self._build_error_response("Document does not meet resume structure requirements")
            
            # 9. Structural quality checks
            if not self._validate_structure(text):
                return False, self._build_error_response("Document does not resemble a valid resume format")
            
            # All validations passed
            return True, {
                "valid": True,
                "message": "Resume validation successful",
                "word_count": len(self._get_meaningful_words(text)),
                "detected_sections": self._get_detected_sections(text),
                "quality_score": self._calculate_quality_score(text)
            }
            
        except Exception as e:
            return False, self._build_error_response(f"Validation error: {str(e)}")
    
    def _validate_file_type(self, filename: str, file_path: str) -> bool:
        """Validate file extension and MIME type"""
        # Check extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            self.validation_errors.append(
                f"File type '{file_ext}' not allowed. Only PDF, DOC, and DOCX are accepted."
            )
            return False
        
        # Verify MIME type matches extension (if magic is available)
        if MAGIC_AVAILABLE:
            try:
                mime = magic.Magic(mime=True)
                file_mime = mime.from_file(file_path)
                
                valid_mimes = {
                    '.pdf': ['application/pdf'],
                    '.doc': ['application/msword', 'application/x-msword'],
                    '.docx': [
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'application/zip'  # DOCX is a zip file
                    ]
                }
                
                if file_ext in valid_mimes:
                    if not any(mime_type in file_mime for mime_type in valid_mimes[file_ext]):
                        self.validation_errors.append(
                            f"File extension '{file_ext}' does not match file content type"
                        )
                        return False
            except Exception:
                # If magic fails, continue with extension check only
                pass
        
        return True
    
    def _validate_file_size(self, file_size: int) -> bool:
        """Validate file size is within acceptable range"""
        if file_size < self.MIN_FILE_SIZE:
            self.validation_errors.append(
                f"File too small ({file_size} bytes). Minimum size is {self.MIN_FILE_SIZE} bytes (2KB)."
            )
            return False
        
        if file_size > self.MAX_FILE_SIZE:
            self.validation_errors.append(
                f"File too large ({file_size} bytes). Maximum size is {self.MAX_FILE_SIZE} bytes (5MB)."
            )
            return False
        
        return True
    
    def _validate_security(self, file_path: str, filename: str) -> bool:
        """Security validation checks"""
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            self.validation_errors.append("Filename contains invalid path characters")
            return False

        # Check for password-protected PDFs
        if file_path.endswith('.pdf'):
            try:
                with open(file_path, 'rb') as f:
                    pdf_reader = pypdf.PdfReader(f)
                    if pdf_reader.is_encrypted:
                        self.validation_errors.append("Password-protected PDFs are not allowed")
                        return False
            except Exception:
                pass

        return True
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent injection attacks"""
        # Remove path traversal attempts
        filename = os.path.basename(filename)
        
        # Allow only alphanumeric, spaces, hyphens, underscores, and dots
        sanitized = re.sub(r'[^\w\s\-\.]', '', filename)
        
        # Remove multiple dots (except for extension)
        parts = sanitized.rsplit('.', 1)
        if len(parts) == 2:
            sanitized = parts[0].replace('.', '_') + '.' + parts[1]
        
        return sanitized
    
    def _extract_text(self, file_path: str, filename: str) -> Optional[str]:
        """Extract text from document"""
        file_ext = Path(filename).suffix.lower()
        
        try:
            if file_ext == '.pdf':
                return self._extract_from_pdf(file_path)
            elif file_ext in ['.doc', '.docx']:
                return self._extract_from_docx(file_path)
        except Exception as e:
            self.validation_errors.append(f"Failed to extract text: {str(e)}")
            return None
        
        return None
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF"""
        text_parts = []
        
        try:
            # Try pdfplumber first (better for formatted documents)
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    
                    # Check if page has images but no text (image-only PDF)
                    if not page_text and page.images:
                        self.validation_errors.append(
                            "Image-only PDFs are not accepted. Please provide a text-based resume."
                        )
                        return ""
        except Exception:
            # Fallback to pypdf
            try:
                with open(file_path, 'rb') as f:
                    pdf_reader = pypdf.PdfReader(f)
                    for page in pdf_reader.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
            except Exception as e:
                self.validation_errors.append(f"PDF extraction failed: {str(e)}")
                return ""
        
        return "\n\n".join(text_parts)
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX"""
        try:
            doc = docx.Document(file_path)
            text_parts = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            # Extract from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text for cell in row.cells)
                    if row_text.strip():
                        text_parts.append(row_text)
            
            return "\n\n".join(text_parts)
        except Exception as e:
            self.validation_errors.append(f"DOCX extraction failed: {str(e)}")
            return ""
    
    def _validate_readability(self, text: str) -> bool:
        """Check if document is readable and not blank"""
        if not text or len(text.strip()) < 100:
            self.validation_errors.append("Document is blank or contains insufficient text")
            return False
        
        # Check for corrupted text (too many non-ASCII characters)
        non_ascii_ratio = sum(1 for c in text if ord(c) > 127) / len(text)
        if non_ascii_ratio > 0.3:
            self.validation_errors.append("Document contains unreadable or corrupted text")
            return False
        
        return True
    
    def _get_meaningful_words(self, text: str) -> List[str]:
        """Extract meaningful words (excluding symbols and filler)"""
        # Remove special characters and split
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        
        # Filter out common filler words
        filler_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        meaningful_words = [w for w in words if w not in filler_words and len(w) > 2]
        
        return meaningful_words
    
    def _validate_word_count(self, text: str) -> bool:
        """Validate minimum word count"""
        meaningful_words = self._get_meaningful_words(text)
        
        if len(meaningful_words) < self.MIN_WORD_COUNT:
            self.validation_errors.append(
                f"Document contains only {len(meaningful_words)} meaningful words. "
                f"Minimum required: {self.MIN_WORD_COUNT}"
            )
            return False
        
        return True
    
    def _validate_no_spam(self, text: str) -> bool:
        """Detect spam, rubbish, and invalid content"""
        text_lower = text.lower()
        
        # Check for spam patterns
        for pattern in self.SPAM_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                self.validation_errors.append(
                    "Document contains spam, placeholder text, or invalid content"
                )
                return False
        
        # Check for excessive repetition
        words = self._get_meaningful_words(text)
        if words:
            word_counts = Counter(words)
            most_common_word, count = word_counts.most_common(1)[0]
            repetition_ratio = count / len(words)
            
            if repetition_ratio > 0.15:  # More than 15% same word
                self.validation_errors.append(
                    f"Document contains excessive repetition of word '{most_common_word}'"
                )
                return False
        
        # Check for keyboard mashing patterns
        if re.search(r'[a-z]{15,}', text_lower):
            # Check if it's a long word without vowels (likely garbage)
            long_words = re.findall(r'\b[a-z]{15,}\b', text_lower)
            for word in long_words:
                vowel_count = sum(1 for c in word if c in 'aeiou')
                if vowel_count < len(word) * 0.2:  # Less than 20% vowels
                    self.validation_errors.append("Document contains random character strings")
                    return False
        
        return True
    
    def _validate_sections(self, text: str) -> bool:
        """Strict section validation - must have substantial content"""
        text_lower = text.lower()
        detected_sections = []
        
        for section_name, patterns in self.REQUIRED_SECTIONS.items():
            section_found = False
            section_has_content = False
            
            # Check if section heading exists
            for pattern in patterns:
                matches = list(re.finditer(pattern, text_lower, re.IGNORECASE))
                
                if matches:
                    section_found = True
                    
                    # Extract content after section heading
                    for match in matches:
                        start_pos = match.end()
                        # Get next 500 characters after heading
                        section_text = text[start_pos:start_pos + 500]
                        
                        # Check if there's substantial content
                        section_words = self._get_meaningful_words(section_text)
                        
                        if len(section_words) >= self.MIN_SECTION_WORDS:
                            section_has_content = True
                            break
                    
                    if section_has_content:
                        break
            
            if section_found and section_has_content:
                detected_sections.append(section_name)
            elif section_found and not section_has_content:
                self.validation_errors.append(
                    f"Section '{section_name}' detected but contains no substantial content "
                    f"(minimum {self.MIN_SECTION_WORDS} words required)"
                )
        
        # Must have at least 2 valid sections
        if len(detected_sections) < 2:
            self.validation_errors.append(
                f"Resume must contain at least 2 substantial sections. "
                f"Found only {len(detected_sections)}: {', '.join(detected_sections) if detected_sections else 'none'}. "
                f"Required sections: Education, Experience, Skills, Projects, Certifications, or Summary"
            )
            return False
        
        return True
    
    def _validate_structure(self, text: str) -> bool:
        """Validate resume structural quality — relaxed checks"""
        # Just verify there's some real text content (not all numbers/symbols)
        words = re.findall(r'[a-zA-Z]{2,}', text)
        if len(words) < 20:
            self.validation_errors.append("Document does not contain enough readable text")
            return False
        return True
    
    def _get_detected_sections(self, text: str) -> List[str]:
        """Get list of detected resume sections"""
        text_lower = text.lower()
        detected = []
        
        for section_name, patterns in self.REQUIRED_SECTIONS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    detected.append(section_name)
                    break
        
        return detected
    
    def _calculate_quality_score(self, text: str) -> float:
        """Calculate resume quality score (0-100)"""
        score = 0.0
        
        # Word count score (max 30 points)
        word_count = len(self._get_meaningful_words(text))
        score += min(30, (word_count / 500) * 30)
        
        # Section score (max 30 points)
        detected_sections = self._get_detected_sections(text)
        score += len(detected_sections) * 5
        
        # Structure score (max 20 points)
        has_name = bool(re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+', text))
        has_dates = bool(re.search(r'\b(19|20)\d{2}\b', text))
        has_email = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
        has_phone = bool(re.search(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', text))
        
        score += sum([has_name, has_dates, has_email, has_phone]) * 5
        
        # Content diversity score (max 20 points)
        unique_words = len(set(self._get_meaningful_words(text)))
        diversity_ratio = unique_words / max(word_count, 1)
        score += min(20, diversity_ratio * 30)
        
        return min(100.0, score)
    
    def _build_error_response(self, main_error: str) -> Dict:
        """Build error response with details"""
        return {
            "valid": False,
            "error": main_error,
            "details": self.validation_errors,
            "message": "Resume validation failed"
        }


# Singleton instance
resume_validator = ResumeValidator()
