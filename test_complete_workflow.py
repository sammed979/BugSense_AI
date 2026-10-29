import requests
import json

# Test the complete debugging workflow
print("=" * 60)
print("Testing Complete BugSense AI Workflow")
print("=" * 60)

# Step 1: Login
print("\n1. Logging in...")
r = requests.post('http://localhost:8000/api/v1/auth/login/', json={'username':'testuser','password':'TestPassword123!'})
print(f"   Login status: {r.status_code}")
if r.status_code != 200:
    print(f"   Error: {r.text}")
    exit(1)
token = r.json()['access']
print("   [OK] Login successful")

# Test code with NameError
test_code = 'print(total_price)'
error_message = 'NameError: name total_price is not defined'
terminal_logs = '''Traceback (most recent call last):
  File "<string>", line 1, in <module>
NameError: name total_price is not defined'''

# Step 2: Analyze the error
print("\n2. Analyzing error...")
analysis_data = {
    'source_code': test_code,
    'error_message': error_message,
    'terminal_logs': terminal_logs,
    'language': 'python'
}

r = requests.post('http://localhost:8000/api/v1/analysis/analyze/', 
                   headers={'Authorization':f'Bearer {token}'}, 
                   json=analysis_data)
print(f"   Analysis status: {r.status_code}")
if r.status_code != 200:
    print(f"   Error: {r.text}")
    exit(1)
analysis_result = r.json()
print(f"   [OK] Analysis complete")
print(f"   - Undefined names: {analysis_result['static_analysis']['undefined_names']}")
print(f"   - Exception type: {analysis_result['traceback_analysis']['exception_type']}")

# Step 3: Generate repair
print("\n3. Generating repair...")
repair_data = {
    'source_code': test_code,
    'error_message': error_message,
    'diagnosis': {
        'error_category': analysis_result['traceback_analysis']['exception_type'],
        'summary': f'Variable {analysis_result["static_analysis"]["undefined_names"][0]} is not defined'
    },
    'language': 'python'
}

r = requests.post('http://localhost:8000/api/v1/repair/', 
                   headers={'Authorization':f'Bearer {token}'}, 
                   json=repair_data)
print(f"   Repair status: {r.status_code}")
if r.status_code != 200:
    print(f"   Error: {r.text}")
    exit(1)
repair_result = r.json()
print(f"   [OK] Repair generated")
print(f"   - Source: {repair_result['source']}")
print(f"   - Repaired code:")
for line in repair_result['repaired_code'].split('\n'):
    print(f"     {line}")

# Step 4: Verify the repair
print("\n4. Verifying repair...")
verification_data = {
    'original_code': test_code,
    'repaired_code': repair_result['repaired_code'],
    'language': 'python'
}

r = requests.post('http://localhost:8000/api/v1/verification/', 
                   headers={'Authorization':f'Bearer {token}'}, 
                   json=verification_data)
print(f"   Verification status: {r.status_code}")
if r.status_code != 200:
    print(f"   Error: {r.text}")
    exit(1)
verification_result = r.json()
print(f"   [OK] Verification complete")
print(f"   - Syntax check: {verification_result['syntax_check']}")
print(f"   - Lint check: {verification_result['lint_check']}")
print(f"   - Execution check: {verification_result['execution_check']}")
print(f"   - Overall: {'PASSED' if verification_result['passed'] else 'FAILED'}")

if verification_result['execution_check'] == 'PASSED':
    print(f"   - Execution result:")
    print(f"     Exit code: {verification_result['execution_result']['exit_code']}")
    print(f"     Stdout: {verification_result['execution_result']['stdout'].strip()}")
    print(f"     Duration: {verification_result['execution_result']['duration_ms']}ms")

# Step 5: Execute the repaired code directly
print("\n5. Executing repaired code...")
execution_data = {
    'code': repair_result['repaired_code']
}

r = requests.post('http://localhost:8000/api/v1/execution/execute/', 
                   headers={'Authorization':f'Bearer {token}'}, 
                   json=execution_data)
print(f"   Execution status: {r.status_code}")
if r.status_code != 200:
    print(f"   Error: {r.text}")
    exit(1)
execution_result = r.json()
print(f"   [OK] Execution complete")
print(f"   - Exit code: {execution_result['exit_code']}")
print(f"   - Stdout: {execution_result['stdout'].strip()}")
print(f"   - Stderr: {execution_result['stderr'].strip() if execution_result['stderr'] else '(empty)'}")
print(f"   - Duration: {execution_result['duration_ms']}ms")

print("\n" + "=" * 60)
print("Workflow Test Complete!")
print("=" * 60)
