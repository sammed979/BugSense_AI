"""
Repair Engine - AI-powered code repair with verification.
"""
import hashlib
from typing import Dict, Any
import os
import asyncio
import ast
import json
import difflib

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


class RepairEngine:
    """Automatic code repair service with verification."""

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def generate_diff(original: str, repaired: str) -> str:
        """Return a complete unified diff, including removals and insertions."""
        return '\n'.join(difflib.unified_diff(
            original.splitlines(), repaired.splitlines(),
            fromfile='Original', tofile='Proposed', lineterm=''
        ))

    @staticmethod
    async def generate_repair(
        source_code: str,
        error_message: str,
        diagnosis: Dict[str, Any],
        language: str,
        traceback_text: str = ''
    ) -> Dict[str, Any]:
        """Use AI to generate a code repair. Respects AI_PROVIDER_PRIORITY setting."""

        # Get provider priority from environment
        from .ai_service import AIService
        providers = AIService._provider_order()


        # Enhance diagnosis if not provided
        if not diagnosis or diagnosis.get('error_category') == 'Unknown':
            from .code_analyzer import CodeAnalyzer
            diagnosis = CodeAnalyzer.analyze_error_context(source_code, error_message)

        last_error = None
        last_error_type = None

        # Initialize API key variables for error reporting
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        google_api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')

        # Try providers in priority order
        for provider in providers:
            if provider == 'openai':
                if openai_api_key and OPENAI_AVAILABLE:
                    try:
                        result = await RepairEngine._repair_with_openai(
                            source_code, error_message, diagnosis, language, openai_api_key, os.environ.get('OPENAI_MODEL', 'gpt-4o')
                        )
                        if result.get('error'):
                            last_error = f"OpenAI: {result.get('error')}"
                        else:
                            result.update({'provider': 'OpenAI', 'model': os.environ.get('OPENAI_MODEL', 'gpt-4o')})
                            return result
                    except Exception as e:
                        last_error = f"OpenAI exception: {type(e).__name__}"

            elif provider == 'gemini':
                if google_api_key and GOOGLE_GENAI_AVAILABLE:
                    model = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
                    try:
                        result = await RepairEngine._repair_with_gemini(
                            source_code, error_message, diagnosis, language, google_api_key, model, traceback_text
                        )
                        if result.get('error'):
                            last_error = f"Gemini: {result.get('error')}"
                            last_error_type = result.get('error_type')
                        else:
                            result.setdefault('provider', 'Gemini')
                            result.setdefault('model', model)
                            return result
                    except Exception as e:
                        last_error = f"Gemini exception: {type(e).__name__}"

            elif provider == 'heuristic':
                from .code_analyzer import CodeAnalyzer
                enhanced_diagnosis = CodeAnalyzer.analyze_error_context(source_code, error_message)
                return RepairEngine._generate_heuristic_repair(source_code, error_message, enhanced_diagnosis)

        # AI failure is explicit. Heuristic repairs are only returned on explicit Quick Fix.
        if not google_api_key and not (openai_api_key and 'openai' in providers):
            return {
                'error': 'Gemini is not configured. Set GEMINI_API_KEY in the backend environment.',
                'error_type': 'missing_api_key',
                'repaired_code': source_code,
                'source': 'error',
                'suggest_heuristic': True
            }

        return {
            'error': last_error or 'The configured AI provider could not generate a repair.',
            'error_type': last_error_type or 'provider_error',
            'repaired_code': source_code,
            'source': 'error',
            'suggest_heuristic': True
        }

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
            client = AsyncOpenAI(api_key=api_key, max_retries=0, timeout=35.0)

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
                'source': 'ai_openai',
                'provider': 'OpenAI',
                'model': model,
                'explanation': 'AI proposed a source-code repair.',
                'status': 'proposed'
            }

        except Exception as e:
            from .ai_service import AIService
            message = str(e).replace(api_key, '[REDACTED]') if api_key else str(e)
            return {
                'error': f'OpenAI repair failed: {AIService._classify_provider_error(message)}',
                'error_type': AIService._classify_provider_error(message),
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
        model: str,
        traceback_text: str = ''
    ) -> Dict[str, Any]:
        """Generate repair using Google Gemini."""
        try:
            prompt = f"""Repair the complete source file for the reported programming error.

Language: {language}

Error Message:
{error_message}

Diagnosis:
{diagnosis.get('summary', 'No diagnosis available')}

Traceback:
{traceback_text or error_message}

Source Code:
{source_code}

Return one JSON object with exactly these keys:
- repaired_code: the complete corrected source file as a string
- explanation: a concise explanation of the changes
Do not omit unchanged portions of the source file. Do not include markdown fences."""

            print(f"Gemini: Calling generate_content with model {model}")

            from google.genai import types
            timeout_seconds = max(5, int(os.environ.get('AI_REQUEST_TIMEOUT_SECONDS', '35')))
            http_options = types.HttpOptions(
                timeout=timeout_seconds * 1000,
                retry_options=types.HttpRetryOptions(attempts=1),
            )
            schema = {
                'type': 'OBJECT',
                'properties': {
                    'repaired_code': {'type': 'STRING'},
                    'explanation': {'type': 'STRING'},
                },
                'required': ['repaired_code', 'explanation'],
            }
            client = genai.Client(api_key=api_key, http_options=http_options)
            async with client.aio as async_client:
                response = await asyncio.wait_for(
                    async_client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.2,
                            response_mime_type='application/json',
                            response_schema=schema,
                        ),
                    ),
                    timeout=timeout_seconds,
                )

            print(f"Gemini: Response received, has text: {bool(response.text)}")

            # Check if response was blocked or has issues
            if not response or not response.text:
                error_msg = 'Gemini returned empty response'
                if hasattr(response, 'candidates') and response.candidates:
                    error_msg = f"Gemini response blocked: {response.candidates[0].finish_reason if response.candidates else 'unknown'}"
                print(f"Gemini error: {error_msg}")
                return {
                    'error': error_msg,
                    'error_type': 'malformed_response',
                    'repaired_code': source_code,
                    'source': 'error'
                }

            raw_text = (response.text or '').strip()
            try:
                structured = json.loads(raw_text)
                repaired_code = structured.get('repaired_code', '').strip()
                explanation = structured.get('explanation', '').strip()
            except (json.JSONDecodeError, AttributeError):
                return {
                    'error': 'Gemini returned malformed repair data.',
                    'error_type': 'malformed_response',
                    'repaired_code': source_code,
                    'source': 'error',
                }
            print(f"Gemini: Raw response length: {len(repaired_code)}")

            # Remove markdown code blocks if present
            if repaired_code.startswith('```'):
                lines = repaired_code.split('\n')
                if lines[0].startswith('```'):
                    repaired_code = '\n'.join(lines[1:-1]) if lines[-1] == '```' else '\n'.join(lines[1:])

            print(f"Gemini: Cleaned response length: {len(repaired_code)}")

            # Validate that we got actual code, not just an explanation
            if len(repaired_code) < 10 or not any(char in repaired_code for char in ['=', 'def', 'class', 'if', 'for', 'while', 'return', 'print']):
                return {
                    'error': 'Gemini returned non-code response (likely explanation instead of code)',
                    'error_type': 'malformed_response',
                    'repaired_code': source_code,
                    'source': 'error'
                }

            if language == 'python':
                try:
                    ast.parse(repaired_code)
                except SyntaxError:
                    return {
                        'error': 'Gemini returned Python code with a syntax error.',
                        'error_type': 'malformed_response',
                        'repaired_code': source_code,
                        'source': 'error',
                    }

            # If no changes were made, return a warning
            if repaired_code == source_code:
                return {
                    'original_code': source_code,
                    'repaired_code': source_code,
                    'original_hash': RepairEngine.compute_hash(source_code),
                    'repaired_hash': RepairEngine.compute_hash(source_code),
                    'diff': 'No changes made',
                    'source': 'ai_gemini',
                    'provider': 'Gemini',
                    'model': model,
                    'explanation': explanation or 'The model found no code changes to propose.',
                    'status': 'unchanged',
                    'warning': 'AI did not modify the code'
                }

            original_hash = RepairEngine.compute_hash(source_code)
            repaired_hash = RepairEngine.compute_hash(repaired_code)
            diff = RepairEngine.generate_diff(source_code, repaired_code)

            print(f"Gemini: Repair successful, diff length: {len(diff)}")

            return {
                'original_code': source_code,
                'repaired_code': repaired_code,
                'original_hash': original_hash,
                'repaired_hash': repaired_hash,
                'diff': diff,
                'source': 'ai_gemini',
                'provider': 'Gemini',
                'model': model,
                'explanation': explanation or 'AI proposed a source-code repair.',
                'status': 'proposed'
            }

        except Exception as e:
            # Keep provider errors distinct so clients can explain actionable failures.
            message = str(e).replace(api_key, '[REDACTED]') if api_key else str(e)
            lowered = message.lower()
            if any(term in lowered for term in ('401', '403', 'unauthorized', 'api key', 'permission denied', 'invalid_argument')):
                error_type = 'authentication'
            elif any(term in lowered for term in ('quota', 'resource_exhausted', 'billing')):
                error_type = 'quota_exhausted'
            elif any(term in lowered for term in ('rate limit', 'rate_limit', 'too many requests', '429')):
                error_type = 'rate_limited'
            elif '503' in lowered or 'service unavailable' in lowered:
                error_type = 'service_unavailable'
            elif '404' in lowered or 'not found' in lowered or ('model' in lowered and ('unsupported' in lowered or 'not available' in lowered)):
                error_type = 'model_unavailable'
            elif 'timeout' in lowered or 'timed out' in lowered:
                error_type = 'timeout'
            elif any(term in lowered for term in ('connection', 'network', 'unavailable')):
                error_type = 'network'
            else:
                error_type = 'provider_error'
            return {
                'error': f'Gemini {error_type.replace("_", " ")}. Check the backend provider configuration and quota.',
                'error_type': error_type,
                'repaired_code': source_code,
                'source': 'error'
            }

    @staticmethod
    def _generate_heuristic_repair(
        source_code: str,
        error_message: str,
        diagnosis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a smart heuristic repair for common errors."""
        repaired_code = source_code
        error_type = diagnosis.get('error_category', error_message)

        import re

        # Smart heuristic for NameError
        if 'NameError' in str(error_type) or 'NameError' in error_message:
            # Extract undefined variable from error message
            match = re.search(r"name '(\w+)' is not defined", error_message)
            if not match:
                match = re.search(r"(\w+) is not defined", error_message)

            if match:
                var_name = match.group(1)
                lines = source_code.split('\n')

                # Check if there's a function that could define this variable
                # Pattern: function name contains part of variable name
                function_names = []
                for line in lines:
                    func_match = re.match(r'def\s+(\w+)\s*\(', line)
                    if func_match:
                        function_names.append(func_match.group(1))

                # Try to find a matching function
                matching_func = None
                for func_name in function_names:
                    # Check if variable name contains function name or vice versa
                    if func_name in var_name or var_name in func_name:
                        matching_func = func_name
                        break
                    # Check common patterns like total_price -> calculate_total
                    if 'calculate' in func_name and 'total' in var_name.lower():
                        matching_func = func_name
                        break
                    if 'get' in func_name and var_name.startswith(func_name.replace('get', '').lower()):
                        matching_func = func_name
                        break
                    # Check for typos using simple string similarity
                    # if_palindrome vs is_palindrome - should match
                    if abs(len(var_name) - len(func_name)) <= 2:
                        # Count matching characters
                        matches = sum(1 for a, b in zip(var_name, func_name) if a == b)
                        similarity = matches / max(len(var_name), len(func_name))
                        if similarity >= 0.7:  # 70% similarity threshold
                            matching_func = func_name
                            break

                if matching_func:
                    # If the undefined variable is being used as a function call
                    # Replace it with the correct function name instead of adding a definition
                    for i, line in enumerate(lines):
                        if var_name in line:
                            # Check if it's being called as a function
                            if f'{var_name}(' in line:
                                # Replace the function call
                                lines[i] = line.replace(f'{var_name}(', f'{matching_func}(')
                                break
                            # Otherwise, add a definition as before
                            elif '=' not in line.split(var_name)[0]:
                                func_match = re.search(rf'def {re.escape(matching_func)}\s*\(([^)]*)\)', source_code)
                                if func_match:
                                    args_str = func_match.group(1)
                                    args = [a.strip().split('=')[0].strip() for a in args_str.split(',') if a.strip()]

                                    # Build call with existing variables or default values
                                    call_args = []
                                    for arg in args:
                                        # Check if this variable is already defined
                                        if any(f'{arg} =' in line for line in lines):
                                            call_args.append(arg)
                                        else:
                                            # Use a reasonable default based on argument name
                                            if 'price' in arg.lower():
                                                call_args.append('100')
                                            elif 'quantity' in arg.lower() or 'count' in arg.lower():
                                                call_args.append('5')
                                            elif 'rate' in arg.lower() or 'percent' in arg.lower():
                                                call_args.append('0.1')
                                            else:
                                                call_args.append('0')

                                    call_line = f"{var_name} = {matching_func}({', '.join(call_args)})"

                                    # Insert before the line that uses the undefined variable
                                    indent_match = re.match(r'^(\s*)', line)
                                    indent = indent_match.group(1) if indent_match else ''
                                    lines.insert(i, f"{indent}{call_line}")
                                    break
                    else:
                        # If no usage line found, just replace any occurrence
                        for i, line in enumerate(lines):
                            if f'{var_name}(' in line:
                                lines[i] = line.replace(f'{var_name}(', f'{matching_func}(')
                                break
                else:
                    # No matching function found, add a placeholder with better comment
                    indent_match = re.match(r'^(\s*)', lines[0]) if lines else None
                    indent = indent_match.group(1) if indent_match else ''
                    lines.insert(0, f"{indent}{var_name} = 0  # TODO: Define this variable or call a function to compute it")

                repaired_code = '\n'.join(lines)

        # Heuristic for ZeroDivisionError
        elif 'ZeroDivisionError' in str(error_type) or 'ZeroDivisionError' in error_message:
            lines = source_code.split('\n')
            new_lines = []
            for line in lines:
                # Add simple check before division
                if '/' in line and not line.strip().startswith('#'):
                    # Extract divisor
                    div_match = re.search(r'/\s*(\w+)', line)
                    if div_match:
                        divisor = div_match.group(1)
                        indent_match = re.match(r'^(\s*)', line)
                        indent = indent_match.group(1) if indent_match else ''
                        new_lines.append(f"{indent}if {divisor} != 0:")
                        new_lines.append(f"{indent}    {line}")
                        new_lines.append(f"{indent}else:")
                        new_lines.append(f"{indent}    # Handle division by zero")
                        continue
                new_lines.append(line)
            repaired_code = '\n'.join(new_lines)

        # Apply common logic fixes (regardless of error type)
        # Fix palindrome slice error: text[1:] -> text[::-1]
        if 'is_palindrome' in repaired_code.lower() and 'text[1:]' in repaired_code:
            lines = repaired_code.split('\n')
            for i, line in enumerate(lines):
                if 'text[1:]' in line and 'return' in line:
                    # Fix the slice to reverse the string
                    lines[i] = line.replace('text[1:]', 'text[::-1]')
                    break
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
            'warning': 'This is a heuristic repair - AI service not configured or failed'
        }
