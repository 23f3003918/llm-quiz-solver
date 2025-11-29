import logging
import httpx
import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin
from browser import get_browser_manager
from llm_client import get_llm_client
import config

logger = logging.getLogger(__name__)


class QuizSolver:
    """Main quiz solver that chains through multiple quizzes"""
    
    def __init__(self, email: str, secret: str):
        self.email = email
        self.secret = secret
        self.start_time = None
        self.llm_client = get_llm_client()
    
    def time_remaining(self) -> float:
        """Get remaining time in seconds"""
        if not self.start_time:
            return config.TIMEOUT_SECONDS
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return config.TIMEOUT_SECONDS - elapsed
    
    async def solve_chain(self, start_url: str):
        """
        Main method to solve the quiz chain
        """
        self.start_time = datetime.now()
        logger.info(f"Starting quiz chain at {self.start_time}")
        
        current_url = start_url
        question_count = 0
        
        while current_url and self.time_remaining() > 10:  # Keep 10s buffer
            question_count += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"Question {question_count}: {current_url}")
            logger.info(f"Time remaining: {self.time_remaining():.1f}s")
            logger.info(f"{'='*60}\n")
            
            try:
                # Solve the current quiz
                next_url = await self.solve_single_quiz(current_url)
                
                if next_url:
                    logger.info(f"Moving to next quiz: {next_url}")
                    current_url = next_url
                else:
                    logger.info("Quiz chain completed!")
                    break
                    
            except Exception as e:
                logger.error(f"Error solving quiz {current_url}: {e}", exc_info=True)
                break
        
        if self.time_remaining() <= 10:
            logger.warning("Timeout approaching, stopping quiz chain")
        
        logger.info(f"Solved {question_count} questions in total")
    
    async def solve_single_quiz(self, quiz_url: str) -> Optional[str]:
        """
        Solve a single quiz question
        Returns the next quiz URL if any
        """
        # Step 1: Fetch the quiz page content
        browser = await get_browser_manager()
        question_text = await browser.fetch_page_content(quiz_url)
        
        logger.info(f"Question text:\n{question_text[:500]}...")
        
        # Step 2: Analyze the question
        analysis = await self.llm_client.analyze_question(question_text)
        logger.info(f"Analysis: {analysis}")
        
        # Step 3: Extract submit URL from question or analysis
        submit_url = self.extract_submit_url(question_text, analysis, quiz_url)
        
        if not submit_url:
            logger.error("Could not find submit URL!")
            return None
        
        logger.info(f"Submit URL: {submit_url}")
        
        # Step 4: Solve the question
        answer = await self.solve_question(question_text, analysis)
        logger.info(f"Answer: {answer}")
        
        # Step 5: Submit the answer
        next_url = await self.submit_answer(submit_url, quiz_url, answer)
        
        return next_url
    
    def extract_submit_url(self, question_text: str, analysis: dict, current_url: str) -> Optional[str]:
        """Extract the submit URL from the question text and convert relative URLs to absolute"""
        
        # First try from analysis
        if "submit_url" in analysis and analysis["submit_url"]:
            submit_url = analysis["submit_url"]
            # Convert relative URL to absolute
            if not submit_url.startswith('http'):
                submit_url = urljoin(current_url, submit_url)
            return submit_url
        
        # Try to find URL pattern in question text
        # Look for "Post your answer to https://..."
        patterns = [
            r'POST.*?to\s+(https?://[^\s]+)',
            r'submit.*?(https?://[^\s]+submit[^\s]*)',
            r'POST.*?(https?://[^\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, question_text, re.IGNORECASE)
            if match:
                url = match.group(1).rstrip('.,;:')
                return url
        
        # Look for any URL that contains "submit"
        urls = re.findall(r'https?://[^\s<>"]+', question_text)
        for url in urls:
            if 'submit' in url.lower():
                return url.rstrip('.,;:')
        
        # Look for relative URLs like "/submit"
        relative_match = re.search(r'(?:POST|submit).*?to\s+(/[^\s]+)', question_text, re.IGNORECASE)
        if relative_match:
            relative_url = relative_match.group(1).rstrip('.,;:')
            return urljoin(current_url, relative_url)
        
        return None
    
    async def solve_question(self, question_text: str, analysis: dict) -> any:
        """
        Solve the question based on its type
        """
        task_type = analysis.get("task_type", "unknown")
        
        # For now, let's try the direct approach with LLM
        # In a production system, you'd route to different processors
        # based on task_type
        
        try:
            # Try direct solving first (works for simple questions)
            answer = await self.llm_client.solve_question_direct(question_text)
            return answer
        except Exception as e:
            logger.error(f"Direct solving failed: {e}")
            
            # Fallback: generate and execute code
            # (This would need sandboxing in production)
            try:
                code = await self.llm_client.generate_solution_code(question_text, analysis)
                logger.info("Generated code:")
                logger.info(code)
                
                # For safety, we're not auto-executing arbitrary code
                # In production, you'd use a sandbox
                logger.warning("Code execution not implemented for safety")
                return "Unable to solve automatically"
                
            except Exception as e2:
                logger.error(f"Code generation failed: {e2}")
                raise
    
    async def submit_answer(self, submit_url: str, quiz_url: str, answer: any) -> Optional[str]:
        """
        Submit the answer to the quiz endpoint
        Returns next quiz URL if any
        """
        payload = {
            "email": self.email,
            "secret": self.secret,
            "url": quiz_url,
            "answer": answer
        }
        
        logger.info(f"Submitting answer to {submit_url}")
        logger.info(f"Payload: {payload}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(submit_url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Submission result: {result}")
                
                is_correct = result.get("correct", False)
                reason = result.get("reason", "")
                next_url = result.get("url", None)
                
                if is_correct:
                    logger.info("✓ Answer is CORRECT!")
                else:
                    logger.warning(f"✗ Answer is INCORRECT: {reason}")
                
                return next_url
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error submitting answer: {e}")
                logger.error(f"Response: {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Error submitting answer: {e}")
                return None