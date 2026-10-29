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
        
        # Enhance diagnosis if not provided
        if not diagnosis or diagnosis.get('error_category') == 'Unknown':
            from .code_analyzer import CodeAnalyzer
            diagnosis = CodeAnalyzer.analyze_error_context(source_code, error_message)
        
        # Try OpenAI first if configured
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        openai_model = os.environ.get('OPENAI_MODEL', 'gpt-4o')
        
        if openai_api_key and OPENAI_AVAILABLE:
            print(f"Attempting OpenAI repair with model: {openai_model}")
            try:
                result = await RepairEngine._repair_with_openai(
                    source_code, error_message, diagnosis, language, openai_api_key, openai_model
                )
                print(f"OpenAI result source: {result.get('source')}")
                if result.get('error'):
                    print(f"OpenAI failed with error: {result.get('error')}, trying Gemini...")
                    # Don't return error yet, try Gemini
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
                    print(f"Gemini failed with error: {result.get('error')}")
                    # Return the error instead of falling back to heuristic
                    return result
                else:
                    print(f"Gemini repair successful")
                    return result
            except Exception as e:
                print(f"Gemini repair failed with exception: {e}")
                return {
                    'error': f'Gemini API exception: {str(e)}',
                    'repaired_code': source_code,
                    'source': 'error'
                }
        
        # No AI configured - return error, not heuristic
        if not openai_api_key and not google_api_key:
            return {
                'error': 'No AI provider configured. Please set OPENAI_API_KEY or GOOGLE_API_KEY in environment.',
                'repaired_code': source_code,
                'source': 'error'
            }
        
        # Both configured but failed - return last error
        return {
            'error': 'All AI providers failed. Check API keys and configuration.',
            'repaired_code': source_code,
            'source': 'error'
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
            # Use the new google.genai API with Client
            client = genai.Client(api_key=api_key)
            
            prompt = f"""Fix this programming error.

Language: {language}

Error Message:
{error_message}

Diagnosis:
{diagnosis.get('summary', 'No diagnosis available')}

Source Code:
{source_code}

Provide ONLY the fixed code, no explanations. Output just the corrected source code."""

            print(f"Gemini: Calling generate_content with model {model}")
            response = client.models.generate_content(
                model=model,
                contents=prompt
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
                    'repaired_code': source_code,
                    'source': 'error'
                }
            
            repaired_code = response.text.strip()
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
                    'repaired_code': source_code,
                    'source': 'error'
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
                'source': 'ai_gemini'
            }
            
        except Exception as e:
            # Fall back to heuristic repair on error
            print(f"Gemini exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'error': f'Gemini API error: {str(e)}',
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
                
                if matching_func:
                    # Add function call with reasonable arguments
                    # Try to find existing variable definitions for arguments
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
                        for i, line in enumerate(lines):
                            if var_name in line and '=' not in line.split(var_name)[0]:
                                # Found the line using the undefined variable
                                indent_match = re.match(r'^(\s*)', line)
                                indent = indent_match.group(1) if indent_match else ''
                                lines.insert(i, f"{indent}{call_line}")
                                break
                        else:
                            # Insert at the end if we couldn't find the usage line
                            lines.append(call_line)
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
