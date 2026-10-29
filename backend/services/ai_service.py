"""
AI Service - Provider-independent AI integration for code analysis and repair.
"""
import os
from typing import Dict, Any, Optional

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from google import genai
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False


class AIService:
    """Provider-independent AI service."""

    @staticmethod
    def is_configured() -> bool:
        """Check if AI service is properly configured."""
        # Check for OpenAI first
        if os.environ.get('OPENAI_API_KEY') and OPENAI_AVAILABLE:
            return True
        # Check for Google Gemini
        if os.environ.get('GOOGLE_API_KEY') and GOOGLE_GENAI_AVAILABLE:
            return True
        # Check for generic AI provider
        return bool(os.environ.get('AI_PROVIDER') and os.environ.get('AI_API_KEY'))

    @staticmethod
    async def analyze_error(
        error_message: str,
        traceback: str,
        source_code: str,
        language: str
    ) -> Dict[str, Any]:
        """Use AI to analyze an error."""
        # Try OpenAI first if configured
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if openai_api_key and OPENAI_AVAILABLE:
            try:
                return await AIService._analyze_with_openai(error_message, traceback, source_code, language)
            except Exception as e:
                print(f"OpenAI analysis failed: {e}, trying Gemini...")
        
        # Try Google Gemini
        google_api_key = os.environ.get('GOOGLE_API_KEY')
        if google_api_key and GOOGLE_GENAI_AVAILABLE:
            try:
                return await AIService._analyze_with_gemini(error_message, traceback, source_code, language)
            except Exception as e:
                print(f"Gemini analysis failed: {e}")
        
        # Fall back to generic AI provider
        if not AIService.is_configured():
            return {
                "error": "AI service not configured",
                "message": "AI analysis requires OPENAI_API_KEY, GOOGLE_API_KEY, or AI_PROVIDER/AI_API_KEY configuration"
            }

        provider = os.environ.get('AI_PROVIDER')
        
        if provider == 'anthropic':
            return await AIService._analyze_with_anthropic(error_message, traceback, source_code, language)
        else:
            return {
                "error": "Unsupported AI provider",
                "message": f"Provider '{provider}' is not supported"
            }

    @staticmethod
    async def _analyze_with_openai(
        error_message: str,
        traceback: str,
        source_code: str,
        language: str
    ) -> Dict[str, Any]:
        """Analyze error using OpenAI."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=os.environ.get('OPENAI_API_KEY'),
            )

            prompt = f"""Analyze this programming error and provide a diagnosis.

Language: {language}

Error Message:
{error_message}

Traceback:
{traceback}

Source Code:
{source_code}

Provide a JSON response with:
- error_category: Type of error (e.g., NameError, TypeError, SyntaxError)
- summary: Brief explanation of what went wrong
- affected_file: Which file has the error (if known)
- affected_line: Which line has the error (if known)
- possible_causes: List of possible causes
- confidence: Your confidence in this diagnosis (0-100)
"""

            response = await client.chat.completions.create(
                model=os.environ.get('OPENAI_MODEL', 'gpt-4'),
                messages=[
                    {"role": "system", "content": "You are a code debugging expert. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )

            import json
            content = response.choices[0].message.content
            return json.loads(content)

        except ImportError:
            return {
                "error": "OpenAI library not installed",
                "message": "Install with: pip install openai"
            }
        except Exception as e:
            return {
                "error": "OpenAI API error",
                "message": str(e)
            }

    @staticmethod
    async def _analyze_with_gemini(
        error_message: str,
        traceback: str,
        source_code: str,
        language: str
    ) -> Dict[str, Any]:
        """Analyze error using Google Gemini."""
        try:
            api_key = os.environ.get('GOOGLE_API_KEY')
            model_name = os.environ.get('GEMINI_MODEL', 'gemini-1.5-pro')
            
            # Use the new google.genai API with Client
            client = genai.Client(api_key=api_key)
            
            prompt = f"""Analyze this programming error and provide a diagnosis.

Language: {language}

Error Message:
{error_message}

Traceback:
{traceback}

Source Code:
{source_code}

Provide a JSON response with:
- error_category: Type of error (e.g., NameError, TypeError, SyntaxError)
- summary: Brief explanation of what went wrong
- affected_file: Which file has the error (if known)
- affected_line: Which line has the error (if known)
- possible_causes: List of possible causes
- confidence: Your confidence in this diagnosis (0-100)
"""

            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            content = response.text.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```'):
                lines = content.split('\n')
                if lines[0].startswith('```'):
                    content = '\n'.join(lines[1:-1]) if lines[-1] == '```' else '\n'.join(lines[1:])
            
            import json
            return json.loads(content)
            
        except Exception as e:
            return {
                "error": "Gemini API error",
                "message": str(e)
            }

    @staticmethod
    async def _analyze_with_anthropic(
        error_message: str,
        traceback: str,
        source_code: str,
        language: str
    ) -> Dict[str, Any]:
        """Analyze error using Anthropic Claude."""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(
                api_key=os.environ.get('AI_API_KEY'),
            )

            prompt = f"""Analyze this programming error and provide a diagnosis.

Language: {language}

Error Message:
{error_message}

Traceback:
{traceback}

Source Code:
{source_code}

Provide a JSON response with:
- error_category: Type of error (e.g., NameError, TypeError, SyntaxError)
- summary: Brief explanation of what went wrong
- affected_file: Which file has the error (if known)
- affected_line: Which line has the error (if known)
- possible_causes: List of possible causes
- confidence: Your confidence in this diagnosis (0-100)
"""

            response = await client.messages.create(
                model=os.environ.get('AI_MODEL', 'claude-3-opus-20240229'),
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            import json
            content = response.content[0].text
            return json.loads(content)

        except ImportError:
            return {
                "error": "Anthropic library not installed",
                "message": "Install with: pip install anthropic"
            }
        except Exception as e:
            return {
                "error": "Anthropic API error",
                "message": str(e)
            }

    @staticmethod
    async def _analyze_with_openai(
        error_message: str,
        traceback: str,
        source_code: str,
        language: str
    ) -> Dict[str, Any]:
        """Analyze error using OpenAI."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=os.environ.get('AI_API_KEY'),
                base_url=os.environ.get('AI_BASE_URL')
            )

            prompt = f"""Analyze this programming error and provide a diagnosis.

Language: {language}

Error Message:
{error_message}

Traceback:
{traceback}

Source Code:
{source_code}

Provide a JSON response with:
- error_category: Type of error (e.g., NameError, TypeError, SyntaxError)
- summary: Brief explanation of what went wrong
- affected_file: Which file has the error (if known)
- affected_line: Which line has the error (if known)
- possible_causes: List of possible causes
- confidence: Your confidence in this diagnosis (0-100)
"""

            response = await client.chat.completions.create(
                model=os.environ.get('AI_MODEL', 'gpt-4'),
                messages=[
                    {"role": "system", "content": "You are a code debugging expert. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )

            import json
            content = response.choices[0].message.content
            return json.loads(content)

        except ImportError:
            return {
                "error": "OpenAI library not installed",
                "message": "Install with: pip install openai"
            }
        except Exception as e:
            return {
                "error": "OpenAI API error",
                "message": str(e)
            }

    @staticmethod
    async def _analyze_with_anthropic(
        error_message: str,
        traceback: str,
        source_code: str,
        language: str
    ) -> Dict[str, Any]:
        """Analyze error using Anthropic Claude."""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(
                api_key=os.environ.get('AI_API_KEY'),
                base_url=os.environ.get('AI_BASE_URL')
            )

            prompt = f"""Analyze this programming error and provide a diagnosis.

Language: {language}

Error Message:
{error_message}

Traceback:
{traceback}

Source Code:
{source_code}

Provide a JSON response with:
- error_category: Type of error (e.g., NameError, TypeError, SyntaxError)
- summary: Brief explanation of what went wrong
- affected_file: Which file has the error (if known)
- affected_line: Which line has the error (if known)
- possible_causes: List of possible causes
- confidence: Your confidence in this diagnosis (0-100)
"""

            response = await client.messages.create(
                model=os.environ.get('AI_MODEL', 'claude-3-opus-20240229'),
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            import json
            content = response.content[0].text
            return json.loads(content)

        except ImportError:
            return {
                "error": "Anthropic library not installed",
                "message": "Install with: pip install anthropic"
            }
        except Exception as e:
            return {
                "error": "Anthropic API error",
                "message": str(e)
            }
