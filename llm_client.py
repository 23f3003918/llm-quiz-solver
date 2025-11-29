from anthropic import AsyncAnthropic
import logging
import json
import config

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with Claude API"""
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = "claude-3-haiku-20240307"  # Most basic, widely available model
    
    async def analyze_question(self, question_text: str) -> dict:
        """
        Analyze the quiz question and extract:
        - What data needs to be fetched
        - What analysis needs to be performed
        - What format the answer should be in
        """
        
        prompt = f"""You are analyzing a data quiz question. Extract the following information:

Question:
{question_text}

Provide your analysis in JSON format with these fields:
{{
    "task_type": "pdf_analysis|web_scraping|api_call|data_analysis|visualization|other",
    "data_source": "URL or description of where to get data",
    "operations": ["list of operations to perform"],
    "answer_format": "number|string|boolean|json|base64_image",
    "submit_url": "URL where answer should be submitted"
}}

Respond ONLY with valid JSON, no other text."""
        
        logger.info("Analyzing question with LLM...")
        
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            logger.info(f"LLM response: {response_text[:200]}...")
            
            # Strip markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '', 1)
            if response_text.startswith('```'):
                response_text = response_text.replace('```', '', 1)
            if response_text.endswith('```'):
                response_text = response_text.rsplit('```', 1)[0]
            
            # Try to extract just the JSON object
            # Find first { and last }
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1:
                response_text = response_text[start:end+1]
            
            response_text = response_text.strip()
            
            # Parse JSON response
            analysis = json.loads(response_text)
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response_text}")
            raise
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise
    
    async def generate_solution_code(self, question_text: str, analysis: dict) -> str:
        """
        Generate Python code to solve the quiz question
        """
        
        prompt = f"""You are a data analysis expert. Generate Python code to solve this quiz question.

Question:
{question_text}

Analysis:
{json.dumps(analysis, indent=2)}

Generate a complete Python script that:
1. Fetches/downloads the required data
2. Processes and analyzes it
3. Returns the final answer

The code should:
- Use common libraries (requests, pandas, PyPDF2, etc.)
- Handle errors gracefully
- Return the answer in a variable called 'answer'
- Be ready to execute as-is

Respond with ONLY the Python code, no explanation or markdown formatting."""
        
        logger.info("Generating solution code with LLM...")
        
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            code = message.content[0].text
            logger.info(f"Generated code ({len(code)} chars)")
            
            return code
            
        except Exception as e:
            logger.error(f"Error generating solution code: {e}")
            raise
    
    async def solve_question_direct(self, question_text: str) -> any:
        """
        Ask LLM to directly solve the question if it's simple enough
        """
        
        prompt = f"""Solve this data quiz question directly. Provide ONLY the final answer, nothing else.

Question:
{question_text}

Answer (just the value, no explanation):"""
        
        logger.info("Asking LLM to solve directly...")
        
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            answer = message.content[0].text.strip()
            logger.info(f"Direct answer: {answer}")
            
            # Try to parse as number if possible
            try:
                return int(answer)
            except ValueError:
                try:
                    return float(answer)
                except ValueError:
                    return answer
            
        except Exception as e:
            logger.error(f"Error getting direct answer: {e}")
            raise


# Singleton instance
_llm_client = None


def get_llm_client() -> LLMClient:
    """Get or create LLM client singleton"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client