"""
Strict RAG Response Generator with Hallucination Prevention
Ensures all responses are grounded in retrieved context
"""
from typing import List, Dict, Optional
import re
import openai
import httpx
from app.core.config import settings


class StrictRAGGenerator:
    """
    Strict RAG generator that enforces context-grounded responses
    No hallucination - all answers must cite retrieved sources
    """
    
    def __init__(self):
        self.llm_type = settings.LLM_TYPE
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM based on configuration"""
        if self.llm_type == "lmstudio":
            # LM Studio uses OpenAI-compatible API
            openai.api_key = settings.LMSTUDIO_API_KEY
            # Ensure base_url ends with /v1/ for proper endpoint construction
            base_url = settings.LMSTUDIO_BASE_URL.rstrip('/')
            openai.base_url = f"{base_url}/v1/"
            self.model = settings.LMSTUDIO_MODEL
            print(f"Initialized LM Studio: {openai.base_url} with model {self.model}")
        
        elif self.llm_type == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set")
            openai.api_key = settings.OPENAI_API_KEY
            self.model = settings.OPENAI_MODEL
        
        elif self.llm_type == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.model = settings.ANTHROPIC_MODEL
        
        elif self.llm_type == "ollama":
            self.ollama_url = settings.OLLAMA_BASE_URL
            self.model = settings.OLLAMA_MODEL
        
        else:
            raise ValueError(f"Unknown LLM type: {self.llm_type}")
    
    def generate_response(
        self,
        query: str,
        retrieved_contexts: List[Dict],
        system_prompt: Optional[str] = None
    ) -> Dict:
        """
        Generate response using strict RAG principles
        
        Args:
            query: User query
            retrieved_contexts: List of retrieved context chunks
            system_prompt: Optional system prompt override
            
        Returns:
            Dictionary with response, confidence, and citations
        """
        # Check if sufficient context is available
        if not retrieved_contexts:
            return self._insufficient_context_response()
        
        # Calculate confidence based on retrieval scores
        avg_score = sum(ctx['score'] for ctx in retrieved_contexts) / len(retrieved_contexts)
        
        if avg_score < settings.MIN_CONFIDENCE_THRESHOLD:
            return self._low_confidence_response(avg_score)
        
        # Build context string with citations
        context_str = self._build_context_string(retrieved_contexts)
        
        # Build strict RAG prompt
        prompt = self._build_strict_rag_prompt(query, context_str, system_prompt)
        
        # Generate response
        response_text = self._call_llm(prompt)
        
        # Validate response against context
        validation_result = self._validate_response(response_text, retrieved_contexts)
        
        # Extract citations
        citations = self._extract_citations(response_text, retrieved_contexts)
        
        return {
            'response': response_text,
            'confidence': avg_score,
            'citations': citations,
            'retrieved_contexts': retrieved_contexts,
            'validation': validation_result,
            'grounded': validation_result['is_grounded']
        }
    
    def _build_context_string(self, contexts: List[Dict]) -> str:
        """Build formatted context string with source IDs"""
        context_parts = []
        
        for idx, ctx in enumerate(contexts):
            source_id = f"[Source {idx + 1}]"
            text = ctx['text']
            metadata = ctx.get('metadata', {})
            
            # Add metadata if available
            meta_str = ""
            if metadata:
                meta_parts = []
                if 'file_name' in metadata:
                    meta_parts.append(f"File: {metadata['file_name']}")
                if 'chunk_id' in metadata:
                    meta_parts.append(f"Chunk: {metadata['chunk_id']}")
                
                if meta_parts:
                    meta_str = f" ({', '.join(meta_parts)})"
            
            context_parts.append(f"{source_id}{meta_str}:\n{text}\n")
        
        return "\n".join(context_parts)
    
    def _build_strict_rag_prompt(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Build strict RAG prompt that enforces grounding"""
        
        if system_prompt is None:
            system_prompt = """You are an AI interview assistant that STRICTLY follows these rules:

1. ONLY use information from the provided context to answer questions
2. DO NOT use any external knowledge or make assumptions
3. ALWAYS cite sources using [Source N] notation
4. If the context doesn't contain enough information, say: "Based on the provided context, I don't have sufficient information to answer this question."
5. Be precise and factual - no speculation or hallucination
6. Include relevant source citations after each claim
7. If multiple sources support a point, cite all of them

Your goal is accuracy and transparency, not completeness."""
        
        prompt = f"""{system_prompt}

CONTEXT:
{context}

QUESTION: {query}

ANSWER (with source citations):"""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM based on configured type"""
        try:
            if self.llm_type == "lmstudio":
                return self._call_lmstudio(prompt)
            elif self.llm_type == "openai":
                return self._call_openai(prompt)
            elif self.llm_type == "anthropic":
                return self._call_anthropic(prompt)
            elif self.llm_type == "ollama":
                return self._call_ollama(prompt)
        except Exception as e:
            return f"Error generating response: {str(e)}"

    def _call_llm_chat(self, system: str, user: str) -> str:
        """Call LLM with explicit system + user messages"""
        try:
            if self.llm_type in ("lmstudio", "openai"):
                response = openai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user}
                    ],
                    temperature=0.7,
                    max_tokens=600
                )
                return response.choices[0].message.content or ""
            elif self.llm_type == "ollama":
                return self._call_ollama(f"{system}\n\n{user}")
            else:
                return self._call_llm(f"{system}\n\n{user}")
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _call_lmstudio(self, prompt: str) -> str:
        """Call LM Studio API (OpenAI-compatible)"""
        try:
            print(f"🔵 Calling LM Studio at {openai.base_url} with model {self.model}")
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=settings.MAX_CONTEXT_LENGTH
            )
            
            print(f"🔵 Response type: {type(response)}")
            print(f"🔵 Response: {response}")
            
            # Handle different response types
            if response is None:
                print("❌ Response is None")
                return "Error: LLM returned None response"
            
            # Check if response has choices attribute
            if not hasattr(response, 'choices'):
                print(f"❌ Response has no 'choices' attribute. Available attributes: {dir(response)}")
                return "Error: Invalid response structure - no choices"
            
            if not response.choices or len(response.choices) == 0:
                print("❌ Response choices is empty")
                return "Error: LLM returned empty choices"
            
            # Get the first choice
            choice = response.choices[0]
            print(f"🔵 Choice type: {type(choice)}")
            print(f"🔵 Choice: {choice}")
            
            # Check if choice has message attribute
            if not hasattr(choice, 'message'):
                print(f"❌ Choice has no 'message' attribute. Available attributes: {dir(choice)}")
                return "Error: Invalid choice structure - no message"
            
            message = choice.message
            print(f"🔵 Message type: {type(message)}")
            print(f"🔵 Message: {message}")
            
            # Check if message has content attribute
            if not hasattr(message, 'content'):
                print(f"❌ Message has no 'content' attribute. Available attributes: {dir(message)}")
                return "Error: Invalid message structure - no content"
            
            content = message.content
            print(f"🔵 Content type: {type(content)}")
            print(f"🔵 Content length: {len(content) if content else 0}")
            
            if content:
                print(f"✅ Successfully got content: {content[:100]}...")
                return content
            else:
                print("❌ Content is empty or None")
                return "Error: LLM returned empty content"
                
        except Exception as e:
            print(f"❌ Exception in _call_lmstudio: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error calling LM Studio: {str(e)}"
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Low temperature for factual responses
            max_tokens=settings.MAX_CONTEXT_LENGTH
        )
        return response.choices[0].message.content
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API"""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=settings.MAX_CONTEXT_LENGTH,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    
    def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama API"""
        url = f"{self.ollama_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }
        
        response = httpx.post(url, json=payload, timeout=60.0)
        response.raise_for_status()
        
        return response.json()['response']
    
    def _validate_response(self, response: str, contexts: List[Dict]) -> Dict:
        """
        Validate that response is grounded in retrieved context
        
        Returns:
            Validation result with grounding score
        """
        # Extract claims from response (simplified)
        sentences = re.split(r'[.!?]+', response)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Check for citation markers
        has_citations = bool(re.search(r'\[Source \d+\]', response))
        
        # Check for "insufficient information" response
        is_insufficient = "don't have sufficient information" in response.lower()
        
        # Simple grounding check: response should not be too long without context
        context_text = " ".join([ctx['text'] for ctx in contexts])
        response_words = set(response.lower().split())
        context_words = set(context_text.lower().split())
        
        # Calculate word overlap
        overlap = len(response_words & context_words)
        overlap_ratio = overlap / len(response_words) if response_words else 0
        
        is_grounded = (
            has_citations or
            is_insufficient or
            overlap_ratio > 0.3  # At least 30% word overlap
        )
        
        return {
            'is_grounded': is_grounded,
            'has_citations': has_citations,
            'overlap_ratio': overlap_ratio,
            'is_insufficient_response': is_insufficient
        }
    
    def _extract_citations(self, response: str, contexts: List[Dict]) -> List[Dict]:
        """Extract citation information from response"""
        citations = []
        
        # Find all [Source N] patterns
        citation_pattern = r'\[Source (\d+)\]'
        matches = re.finditer(citation_pattern, response)
        
        for match in matches:
            source_num = int(match.group(1))
            if 0 < source_num <= len(contexts):
                ctx = contexts[source_num - 1]
                citations.append({
                    'source_id': source_num,
                    'text': ctx['text'][:200] + "...",  # Preview
                    'metadata': ctx.get('metadata', {}),
                    'score': ctx['score']
                })
        
        return citations
    
    def _insufficient_context_response(self) -> Dict:
        """Return response when no context is available"""
        return {
            'response': "I don't have sufficient retrieved evidence to answer this question. Please provide more context or rephrase your question.",
            'confidence': 0.0,
            'citations': [],
            'retrieved_contexts': [],
            'validation': {
                'is_grounded': True,
                'has_citations': False,
                'is_insufficient_response': True
            },
            'grounded': True
        }
    
    def _low_confidence_response(self, confidence: float) -> Dict:
        """Return response when confidence is too low"""
        return {
            'response': f"The retrieved context has low relevance (confidence: {confidence:.2f}). I cannot provide a reliable answer based on the available information.",
            'confidence': confidence,
            'citations': [],
            'retrieved_contexts': [],
            'validation': {
                'is_grounded': True,
                'has_citations': False,
                'is_insufficient_response': True
            },
            'grounded': True
        }
    
    def evaluate_coding_answer(self, question: str, answer: str) -> dict:
        """Use LLM to evaluate a coding answer. Returns score (0-100) and feedback."""
        raw = self._call_llm_chat(
            system=(
                "You are a strict technical interviewer evaluating a coding answer. "
                "Always respond in exactly this format and nothing else:\n"
                "SCORE: <number 0-100>\n"
                "FEEDBACK: <2-4 sentences of specific feedback>"
            ),
            user=(
                f"PROBLEM: {question}\n\n"
                f"CANDIDATE'S ANSWER:\n{answer}\n\n"
                f"Evaluate on: correctness, code quality, edge cases, time/space complexity."
            )
        )
        raw = re.sub(r'<\|.*?\|>', '', raw).strip()
        score_match = re.search(r'SCORE[:\s]+(\d+(?:\.\d+)?)', raw, re.IGNORECASE)
        score = float(score_match.group(1)) if score_match else 50.0
        score = max(0.0, min(100.0, score))
        feedback_match = re.search(r'FEEDBACK[:\s]+(.+)', raw, re.IGNORECASE | re.DOTALL)
        if feedback_match:
            feedback = feedback_match.group(1).strip()
            feedback = re.split(r'\n(SCORE|Question|User will|You are)', feedback)[0].strip()
        else:
            lines = [l.strip() for l in raw.splitlines() if l.strip() and not re.match(r'SCORE', l, re.IGNORECASE)]
            feedback = ' '.join(lines[:3]) if lines else "Answer evaluated."
        return {"score": score, "feedback": feedback}

    def generate_interview_question(
        self,
        domain: str,
        difficulty: str,
        context: List[Dict],
        previous_questions: List[str] = None
    ) -> str:
        """
        Generate a single, difficulty-appropriate interview question.
        Enforces strict rules: no multi-part questions, no diagrams, 1-2 sentences max.
        """
        if not context:
            return "Unable to generate question without context."

        context_str = self._build_context_string(context)

        # Only pass last 5 previous questions to avoid token bloat
        prev_q_list = (previous_questions or [])[-5:]
        prev_q_str = ""
        if prev_q_list:
            prev_q_str = "Previously asked questions (do NOT repeat these):\n" + "\n".join(f"- {q}" for q in prev_q_list) + "\n\n"

        # Difficulty-specific rules
        coding_domains = {'python', 'data structures', 'data-structures', 'web development', 'web-development', 'databases', 'coding round'}
        is_coding = any(cd in domain.lower() for cd in coding_domains)

        difficulty_rules = {
            "easy": (
                "EASY level rules:\n"
                "- Ask about a single basic concept, definition, or simple fact\n"
                + ("- You MAY ask to write a short code snippet (e.g. 'Write a Python function to reverse a string')\n" if is_coding else "")
                + "- Example style: 'What is X?' or 'What does X mean?' or 'Name one use of X'\n"
                "- Do NOT ask about system design, architecture, or trade-offs\n"
                "- Do NOT ask the candidate to compare multiple approaches"
            ),
            "medium": (
                "MEDIUM level rules:\n"
                "- Ask how something works or why it is used\n"
                + ("- You MAY ask to write or explain a code snippet (e.g. 'Write a function to check if a string is a palindrome')\n" if is_coding else "")
                + "- Example style: 'How does X work?' or 'Why would you use X over Y?'\n"
                "- May involve one comparison or one practical scenario\n"
                "- Do NOT ask for full system designs or architecture diagrams"
            ),
            "hard": (
                "HARD level rules:\n"
                "- Ask about trade-offs, edge cases, or deep internals\n"
                + ("- You MAY ask to write an optimized algorithm or explain time/space complexity (e.g. 'Implement LRU cache' or 'Optimize this function for O(n) time')\n" if is_coding else "")
                + "- Example style: 'What are the trade-offs of X?' or 'How would you handle X at scale?'\n"
                "- May involve one specific design decision, but keep it focused\n"
                "- Do NOT ask for multi-part design documents or diagrams"
            ),
        }

        diff_rule = difficulty_rules.get(difficulty.lower(), difficulty_rules["medium"])

        # For Coding Round — pure open-ended algorithm/data structure problems only
        if domain.lower() == 'coding round':
            avoid = ', '.join(prev_q_list) if prev_q_list else 'none'
            difficulty_constraints = {
                "easy": (
                    "EASY: simple array/string manipulation, basic loops, simple math.\n"
                    "Examples: reverse a string, find max in array, check palindrome, count vowels, FizzBuzz.\n"
                    "NEVER ask about system design, distributed systems, concurrency, or architecture."
                ),
                "medium": (
                    "MEDIUM: data structures, recursion, sorting, hash maps, stacks/queues.\n"
                    "Examples: two sum, valid parentheses, binary search, merge sorted arrays, group anagrams.\n"
                    "NEVER ask about system design, distributed systems, or architecture."
                ),
                "hard": (
                    "HARD: dynamic programming, graph algorithms, tree problems, advanced data structures.\n"
                    "Examples: LRU cache implementation, longest increasing subsequence, word ladder, "
                    "trapping rain water, serialize/deserialize binary tree.\n"
                    "NEVER ask about distributed systems, system design, or architecture. "
                    "The question MUST require writing an algorithm or data structure in code."
                ),
            }
            constraint = difficulty_constraints.get(difficulty.lower(), difficulty_constraints["medium"])
            raw = self._call_llm_chat(
                system=(
                    "You are a coding interviewer. You ask ALGORITHM and DATA STRUCTURE problems only. "
                    "You NEVER ask system design, architecture, distributed systems, or design questions. "
                    "Output ONLY the problem statement in plain English. No code, no solution, no preamble."
                ),
                user=(
                    f"Give me a {difficulty.upper()} difficulty coding problem.\n\n"
                    f"{constraint}\n\n"
                    f"The problem must be solvable by writing a single function or algorithm.\n"
                    f"2-3 sentences max, plain English.\n"
                    f"Do not repeat: {avoid}"
                )
            )
            raw = re.sub(r'<\|.*?\|>', '', raw).strip()
            question = re.sub(
                r'^(problem[:\s]+|here\s+is\s+\S+.*?:|sure[,!.\s]+|certainly[,!.\s]+)',
                '', raw, flags=re.IGNORECASE
            ).strip()
            bad_keywords = ['distributed', 'system design', 'architecture', 'microservice',
                            'design a', 'design an', 'scalab', 'concurrent', 'thread-safe']
            if re.match(r'^(import |from |def |class |#|```)', question) or \
               any(w in question.lower() for w in bad_keywords):
                fallbacks = {
                    "easy": "Given an array of integers, return the indices of the two numbers that add up to a given target value.",
                    "medium": "Given a string, find the length of the longest substring that contains no repeating characters.",
                    "hard": "Given the head of a linked list, reverse the nodes of the list k at a time and return the modified list."
                }
                question = fallbacks.get(difficulty.lower(), fallbacks["medium"])
            lines = [l.strip() for l in question.splitlines() if l.strip()]
            return lines[0] if lines else question

        prompt = f"""You are an interviewer generating a single interview question for the domain: {domain}.
Difficulty level: {difficulty.upper()}

{diff_rule}

ABSOLUTE RULES (never break these):
- Output ONLY the question itself — no preamble, no "Here is a question:", no explanation
- The question MUST be 1 to 2 sentences maximum
- Do NOT use numbered sub-parts (no "1.", "2.", "3." inside the question)
- Do NOT ask the candidate to draw, sketch, or provide a diagram
- Do NOT ask for a "design document" or "detailed design"
- Do NOT ask multiple things in one question
- The question must be answerable in a text box (no visual aids needed)

{prev_q_str}CONTEXT (use this to inspire the question topic):
{context_str}

OUTPUT (the question only, nothing else):"""

        raw = self._call_llm(prompt)

        # Strip any LLM preamble like "Here is a question:" or "Question:"
        question = re.sub(
            r'^(here\s+is\s+(a|an|your)\s+question[:\s]*|question[:\s]+|sure[,!\s]+|certainly[,!\s]+)',
            '',
            raw.strip(),
            flags=re.IGNORECASE
        ).strip()

        # If LLM still returned multi-line / multi-part, take only the first sentence
        lines = [l.strip() for l in question.splitlines() if l.strip()]
        if lines:
            question = lines[0]

        return question
