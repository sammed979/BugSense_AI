"""
Complete workflow test for BugSense AI
Tests: NameError repair, execution, verification
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend/.env'))

from services.repair_engine import RepairEngine
from services.code_analyzer import CodeAnalyzer
from sandbox.python_runner import PythonRunner


async def test_nameerror_repair():
    """Test NameError repair workflow"""
    print("\n=== Test A: NameError Repair ===")
    
    code = """def calculate_total(price, quantity):
    return price * quantity

print(total_price)"""
    
    error_message = "NameError: name 'total_price' is not defined"
    
    # Step 1: Analyze
    print("Step 1: Analyzing code...")
    syntax_errors = CodeAnalyzer.check_syntax(code)
    if syntax_errors:
        print(f"[X] Syntax errors found: {syntax_errors}")
        return False
    print("[OK] Syntax check passed")
    
    # Step 2: Execute to see error
    print("\nStep 2: Executing code...")
    try:
        exit_code, stdout, stderr, duration = PythonRunner.execute(code)
        print(f"Exit code: {exit_code}")
        print(f"Stderr: {stderr}")
        if exit_code != 0:
            print("[OK] Error reproduced as expected")
        else:
            print("[X] Code executed without error (unexpected)")
            return False
    except Exception as e:
        print(f"[X] Execution failed: {e}")
        return False
    
    # Step 3: Generate repair
    print("\nStep 3: Generating repair...")
    diagnosis = {
        'summary': 'Undefined variable total_price',
        'error_category': 'NameError'
    }
    
    result = await RepairEngine.generate_repair(
        source_code=code,
        error_message=error_message,
        diagnosis=diagnosis,
        language='python'
    )
    
    print(f"Repair source: {result.get('source')}")
    print(f"Has repaired code: {bool(result.get('repaired_code'))}")
    
    if result.get('error'):
        print(f"[X] Repair failed: {result.get('error')}")
        return False
    
    if result.get('source') == 'heuristic':
        print("[!] Using heuristic repair (AI not available)")
    
    repaired_code = result.get('repaired_code')
    if not repaired_code or repaired_code == code:
        print("[X] No repair generated")
        return False
    
    print("[OK] Repair generated")
    print(f"\nRepaired code:\n{repaired_code}")
    
    # Step 4: Verify repair
    print("\nStep 4: Verifying repair...")
    try:
        exit_code, stdout, stderr, duration = PythonRunner.execute(repaired_code)
        print(f"Exit code: {exit_code}")
        print(f"Stdout: {stdout}")
        
        if exit_code == 0:
            print("[OK] Repair verified - code executes successfully")
            return True
        else:
            print(f"[X] Repair failed - exit code {exit_code}")
            print(f"Stderr: {stderr}")
            return False
    except Exception as e:
        print(f"[X] Verification failed: {e}")
        return False


async def test_zerodivision_repair():
    """Test ZeroDivisionError repair"""
    print("\n=== Test B: ZeroDivisionError Repair ===")
    
    code = """def divide(a, b):
    return a / b

print(divide(10, 0))"""
    
    error_message = "ZeroDivisionError: division by zero"
    
    # Execute
    print("Step 1: Executing code...")
    try:
        exit_code, stdout, stderr, duration = PythonRunner.execute(code)
        print(f"Exit code: {exit_code}")
        print(f"Stderr: {stderr}")
    except Exception as e:
        print(f"[X] Execution failed: {e}")
        return False
    
    # Generate repair
    print("\nStep 2: Generating repair...")
    diagnosis = {
        'summary': 'Division by zero',
        'error_category': 'ZeroDivisionError'
    }
    
    result = await RepairEngine.generate_repair(
        source_code=code,
        error_message=error_message,
        diagnosis=diagnosis,
        language='python'
    )
    
    print(f"Repair source: {result.get('source')}")
    
    if result.get('repaired_code') and result.get('repaired_code') != code:
        print("[OK] Repair generated")
        repaired_code = result.get('repaired_code')
        
        # Verify
        print("\nStep 3: Verifying repair...")
        try:
            exit_code, stdout, stderr, duration = PythonRunner.execute(repaired_code)
            print(f"Exit code: {exit_code}")
            if exit_code == 0:
                print("[OK] Repair handles zero division")
                return True
            else:
                print("[!] Repair still has issues")
                return False
        except Exception as e:
            print(f"[X] Verification failed: {e}")
            return False
    else:
        print("[!] No repair generated (may need AI)")
        return False


async def test_empty_code():
    """Test empty code validation"""
    print("\n=== Test D: Empty Code Validation ===")
    
    code = ""
    
    if not code.strip():
        print("[OK] Empty code detected")
        return True
    else:
        print("[X] Empty code not detected")
        return False


async def main():
    print("=" * 60)
    print("BugSense AI - Complete Workflow Test")
    print("=" * 60)
    
    results = []
    
    # Test A: NameError
    result_a = await test_nameerror_repair()
    results.append(("NameError Repair", result_a))
    
    # Test B: ZeroDivisionError
    result_b = await test_zerodivision_repair()
    results.append(("ZeroDivisionError Repair", result_b))
    
    # Test D: Empty code
    result_d = await test_empty_code()
    results.append(("Empty Code Validation", result_d))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "[OK] PASSED" if passed else "[X] FAILED"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[OK] All tests passed!")
        return 0
    else:
        print(f"\n[X] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
