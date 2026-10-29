"""
Repair Engine - AI-powered code repair with verification.
"""
import hashlib
from typing import Dict, Any
import os
import asyncio

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False


class RepairEngine:
    """Automatic code repair service with verification."""

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def generate_diff(original: str, repaired: str) -> str:
        """Generate a simple diff between original and repaired code."""
        lines_original = original.splitlines()
        lines_repaired = repaired.splitlines()
        
        diff_lines = []
        diff_lines.append("--- Original")
        diff_lines.append("+++ Repaired")
        
        for i, (orig, rep) in enumerate(zip(lines_original, lines_repaired)):
            if orig != rep:
                diff_lines.append(f"@@ -{i+1} +{i+1} @@")
                diff_lines.append(f"-{orig}")
                diff_lines.append(f"+{rep}")
        
        if len(lines_repaired) > len(lines_original):
            for i in range(len(lines_original), len(lines_repaired)):
                diff_lines.append(f"@@ -{i} +{i+1} @@")
                diff_lines.append(f"+{lines_repaired[i]}")
        
        return "\n".join(diff_lines)

    @staticmethod
    async def generate_repair(
        source_code: str,
        error_message: str,
        diagnosis: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """Use AI to generate a code repair."""
        
        print(f"=== Repair Engine Debug ===")
        print(f"OpenAI available: {OPENAI_AVAILABLE}")
        print(f"OpenAI API key configured: {bool(os.environ.get('OPENAI_API_KEY'))}")
        print(f"Gemini available: {GOOGLE_GENAI_AVAILABLE}")
        print(f"Gemini API key configured: {bool(os.environ.get('GOOGLE_API_KEY'))}")
        
        # Try OpenAI first if configured
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        openai_model = os.environ.get('OPENAI_MODEL', 'gpt-4')
        
        if openai_api_key and OPENAI_AVAILABLE:
            print(f"Attempting OpenAI repair with model: {openai_model}")
            try:
                result = await RepairEngine._repair_with_openai(
                    source_code, error_message, diagnosis, language, openai_api_key, openai_model
                )
                print(f"OpenAI result source: {result.get('source')}")
                if result.get('error'):
                    print(f"OpenAI failed with error: {result.get('error')}, trying Gemini...")
                    pass
                else:
                    print(f"OpenAI repair successful")
                    return result
            except Exception as e:
                print(f"OpenAI repair failed with exception: {e}, trying Gemini...")
        
        # Try Google Gemini configuration
        google_api_key = os.environ.get('GOOGLE_API_KEY')
        gemini_model = os.environ.get('GEMINI_MODEL', 'gemini-1.5-pro')
        
        if google_api_key and GOOGLE_GENAI_AVAILABLE:
            print(f"Attempting Gemini repair with model: {gemini_model}")
            try:
                result = await RepairEngine._repair_with_gemini(
                    source_code, error_message, diagnosis, language, google_api_key, gemini_model
                )
                print(f"Gemini result source: {result.get('source')}")
                if result.get('error'):
                    print(f"Gemini failed with error: {result.get('error')}, falling back to heuristic")
                else:
                    print(f"Gemini repair successful")
                    return result
            except Exception as e:
                print(f"Gemini repair failed with exception: {e}, falling back to heuristic")
        
        # No AI configured or all failed - return a simple heuristic repair
        print(f"Both AI services failed or not configured, using heuristic repair")
        return RepairEngine._generate_heuristic_repair(source_code, error_message, diagnosis)

    @staticmethod
    async def _repair_with_openai(
        source_code: str,
        error_message: str,
        diagnosis: Dict[str, Any],
        language: str,
        api_key: str,
        model: str
    ) -> Dict[str, Any]:
        """Generate repair using OpenAI."""
        try:
            client = AsyncOpenAI(api_key=api_key)
            
            prompt = f"""Fix this programming error.

Language: {language}

Error Message:
{error_message}

Diagnosis:
{diagnosis.get('summary', 'No diagnosis available')}

Source Code:
{source_code}

Provide ONLY the fixed code, no explanations. Output just the corrected source code."""

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a code debugging expert. Always respond with valid code only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )

            repaired_code = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if repaired_code.startswith('```'):
                lines = repaired_code.split('\n')
                if lines[0].startswith('```'):
                    repaired_code = '\n'.join(lines[1:-1]) if lines[-1] == '```' else '\n'.join(lines[1:])
            
            # If no changes were made, return a warning
            if repaired_code == source_code:
                return {
                    'original_code': source_code,
                    'repaired_code': source_code,
                    'original_hash': RepairEngine.compute_hash(source_code),
                    'repaired_hash': RepairEngine.compute_hash(source_code),
                    'diff': 'No changes made',
                    'source': 'ai_openai',
                    'warning': 'AI did not modify the code'
                }
            
            original_hash = RepairEngine.compute_hash(source_code)
            repaired_hash = RepairEngine.compute_hash(repaired_code)
            diff = RepairEngine.generate_diff(source_code, repaired_code)
            
            return {
                'original_code': source_code,
                'repaired_code': repaired_code,
                'original_hash': original_hash,
                'repaired_hash': repaired_hash,
                'diff': diff,
                'source': 'ai_openai'
            }
            
        except Exception as e:
            return {
                'error': f'OpenAI repair failed: {str(e)}',
                'repaired_code': source_code,
                'source': 'error'
            }

    @staticmethod
    async def _repair_with_gemini(
        source_code: str,
        error_message: str,
        diagnosis: Dict[str, Any],
        language: str,
        api_key: str,
        model: str
    ) -> Dict[str, Any]:
        """Generate repair using Google Gemini."""
        try:
            # Configure API key globally (new API pattern)
            genai.configure(api_key=api_key)
            client = genai.GenerativeModel(model)
            
            prompt = f"""Fix this programming error.

Language: {language}

Error Message:
{error_message}

Diagnosis:
{diagnosis.get('summary', 'No diagnosis available')}

Source Code:
{source_code}

Provide ONLY the fixed code, no explanations. Output just the corrected source code."""

            response = await client.generate_content_async(prompt)
            
            # Check if response was blocked or has issues
            if not response or not response.text:
                return {
                    'error': 'Gemini returned empty response',
                    'repaired_code': source_code,
                    'source': 'error'
                }
            
            repaired_code = response.text.strip()
            
            # Remove markdown code blocks if present
            if repaired_code.startswith('```'):
                lines = repaired_code.split('\n')
                if lines[0].startswith('```'):
                    repaired_code = '\n'.join(lines[1:-1]) if lines[-1] == '```' else '\n'.join(lines[1:])
            
            # If no changes were made, return a warning
            if repaired_code == source_code:
                return {
                    'original_code': source_code,
                    'repaired_code': source_code,
                    'original_hash': RepairEngine.compute_hash(source_code),
                    'repaired_hash': RepairEngine.compute_hash(source_code),
                    'diff': 'No changes made',
                    'source': 'ai_gemini',
                    'warning': 'AI did not modify the code'
                }
            
            original_hash = RepairEngine.compute_hash(source_code)
            repaired_hash = RepairEngine.compute_hash(repaired_code)
            diff = RepairEngine.generate_diff(source_code, repaired_code)
            
            return {
                'original_code': source_code,
                'repaired_code': repaired_code,
                'original_hash': original_hash,
                'repaired_hash': repaired_hash,
                'diff': diff,
                'source': 'ai_gemini'
            }
            
        except Exception as e:
            # Fall back to heuristic repair on error
            print(f"Gemini error: {e}")
            return RepairEngine._generate_heuristic_repair(source_code, error_message, diagnosis)

    @staticmethod
    def _generate_heuristic_repair(
        source_code: str,
        error_message: str,
        diagnosis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a simple heuristic repair for common errors."""
        repaired_code = source_code
        error_type = diagnosis.get('error_category', error_message)
        
        # Simple heuristic for NameError
        if 'NameError' in str(error_type) or 'NameError' in error_message:
            # Extract undefined variable from error message
            import re
            match = re.search(r"name '(\w+)' is not defined", error_message)
            if not match:
                match = re.search(r"(\w+) is not defined", error_message)
            
            if match:
                var_name = match.group(1)
                # Add a placeholder definition at the top
                lines = source_code.split('\n')
                indent_match = re.match(r'^(\s*)', lines[0]) if lines else None
                indent = indent_match.group(1) if indent_match else ''
                lines.insert(0, f"{indent}{var_name} = None  # TODO: define this variable")
                repaired_code = '\n'.join(lines)
        
        original_hash = RepairEngine.compute_hash(source_code)
        repaired_hash = RepairEngine.compute_hash(repaired_code)
        diff = RepairEngine.generate_diff(source_code, repaired_code)
        
        return {
            'original_code': source_code,
            'repaired_code': repaired_code,
            'original_hash': original_hash,
            'repaired_hash': repaired_hash,
            'diff': diff,
            'source': 'heuristic',
            'warning': 'This is a heuristic repair - AI service not configured'
        }
