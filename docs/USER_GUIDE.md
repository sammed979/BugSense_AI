# BugSense AI - User Guide

## Welcome to BugSense AI

BugSense AI is an AI-assisted debugging platform that helps you identify, analyze, and fix code errors. This guide will walk you through the six main modules of the system.

## Getting Started

### Prerequisites
- Modern web browser (Chrome, Firefox, Edge, Safari)
- Internet connection (for AI features)
- BugSense AI server running

### Accessing the Application
1. Open your browser and navigate to the BugSense AI URL
2. Click "Register" to create an account
3. Enter your username, email, and password
4. Click "Login" to access the system

---

## Module 1: Accounts Management

### Purpose
Manage your user account and configure AI provider settings.

### Features

#### User Registration
- Click "Register" on the login page
- Fill in username, email, and password
- Your account is created instantly

#### User Login
- Enter your username and password
- Click "Login"
- Your session is maintained using secure tokens

#### Profile Management
- Navigate to your profile from the dashboard
- Update your email or username
- Change your password

#### AI Provider Settings
- Configure your preferred AI provider (Gemini or OpenAI)
- Set provider priority (which AI to try first)
- Automatic fallback if primary provider fails

### Quick Tips
- Your session automatically refreshes in the background
- If your session expires, you'll be prompted to log in again
- AI provider settings affect analysis and repair quality

---

## Module 2: Debugging Workspace

### Purpose
Write, execute, and debug code in an isolated environment.

### Features

#### Code Editor
- Monaco Editor integration (VS Code-like experience)
- Syntax highlighting for Python
- Auto-indentation and bracket matching
- Line numbers and word wrap

#### Code Execution
- Click "Run Code" to execute your Python code
- Output appears in the terminal panel
- Errors are captured and displayed
- Execution is limited to 5 seconds for safety

#### Terminal Panel
- Shows execution output
- Displays error messages
- Shows exit codes
- Multiple tabs: Output, Errors, AI Analysis, Repair Diff, Verification

#### Session History
- All debugging sessions are saved automatically
- Access previous sessions from the history page
- Reload code from any past session
- Track your debugging progress

### Example Workflow

1. **Write Code:**
```python
def calculate_total(price, quantity):
    return price * quantity

price = 100
quantity = 5
print(total_price)  # This will cause an error
```

2. **Run Code:**
   - Click "Run Code"
   - You'll see: `NameError: name 'total_price' is not defined`

3. **Analyze:**
   - Click "Analyze" to get AI diagnosis
   - The system will explain the error and suggest a fix

4. **Repair:**
   - Click "Repair" to get AI-generated fix
   - Review the diff
   - Click "Apply" to fix the code

### Quick Tips
- Use Ctrl+Enter to run code quickly
- All code execution is isolated and safe
- Sessions are saved automatically
- You can reload any previous session

---

## Module 3: AI Analysis

### Purpose
Get intelligent error diagnosis and code analysis using AI.

### Features

#### Static Analysis
- Always runs automatically
- Detects syntax errors
- Finds undefined variables
- Identifies common code issues
- Works even without AI providers

#### AI-Powered Diagnosis
- Analyzes error messages and tracebacks
- Explains root causes
- Suggests fixes
- Provides confidence scores
- Works with OpenAI or Gemini

#### Error Types Detected
- NameError - Variable used before definition
- TypeError - Wrong type operation
- SyntaxError - Invalid Python syntax
- IndexError - List index out of range
- KeyError - Dictionary key not found
- ZeroDivisionError - Division by zero

#### AI Provider Selection
- System tries Gemini first (if configured)
- Falls back to OpenAI if Gemini fails
- Falls back to heuristic analysis if both fail
- Static analysis always available

### Example AI Diagnosis

**Error:** `NameError: name 'total_price' is not defined`

**AI Analysis:**
- **Error Type:** NameError
- **Severity:** High
- **Summary:** A variable is used before being defined
- **Possible Causes:** Variable not defined, typo in variable name
- **Undefined Variable:** total_price
- **Available Functions:** calculate_total
- **Suggested Fix:** Call calculate_total(price, quantity) instead of using undefined total_price
- **Corrected Code:**
```python
total = calculate_total(price, quantity)
print(total)
```
- **Confidence:** 95%

### Quick Tips
- Enable AI sharing for better analysis
- Static analysis works without AI
- AI diagnosis provides detailed explanations
- Confidence scores indicate reliability

---

## Module 4: Project Management

### Purpose
Upload, manage, and analyze entire projects with multiple files.

### Features

#### Project Upload
- **Single File:** Upload individual source files
- **Multiple Files:** Upload several files at once
- **ZIP Archive:** Upload entire project folders as ZIP
- **Drag and Drop:** Easy file upload interface

#### Project Explorer
- View project file tree
- Navigate folders
- Select files to view/edit
- File preview with syntax highlighting

#### Project Analysis
- **Static Analysis:** Analyze all files for issues
- **AI Analysis:** Get AI-powered project insights
- **Cross-File Analysis:** Detect dependencies between files
- **Issue Tracking:** List all detected issues by severity

#### File Management
- Create new files in projects
- Save changes to files
- Delete files
- File history tracking

### Project Upload Workflow

1. **Create Project:**
   - Click "New Project"
   - Enter project name
   - Project is created with a workspace

2. **Upload Files:**
   - Click "Upload File" for single file
   - Click "Upload ZIP" for project archive
   - Select files from your computer
   - Files are extracted and stored safely

3. **Analyze Project:**
   - Click "Analyze Project"
   - System scans all files
   - Issues are listed by severity
   - Click on issues to see details

4. **Fix Issues:**
   - Select an issue
   - View suggested fix
   - Apply or reject the fix
   - Track changes in history

### Supported File Types
- Python (.py)
- JavaScript (.js)
- HTML (.html)
- CSS (.css)
- JSON (.json)
- Text files (.txt, .md)

### Security Features
- ZIP path traversal protection
- File size limits
- Virus scanning (basic)
- Workspace isolation
- Automatic cleanup

### Quick Tips
- ZIP uploads preserve folder structure
- Projects can be downloaded as repaired ZIP
- Workspace cleanup runs automatically
- Large projects are analyzed in stages

---

## Module 5: Code Repair and Verification

### Purpose
Generate, review, apply, and verify code repairs automatically.

### Features

#### Repair Generation
- **AI Repair:** Uses AI to generate fixes
- **Quick Fix:** Uses heuristic (local) analysis
- **Diff View:** Shows original vs proposed code
- **Confidence Scores:** Indicates repair reliability

#### Repair Review
- See line-by-line changes
- Review before applying
- Understand the fix
- Compare with original code

#### Repair Application
- Apply approved repairs
- Keep original code
- Track all changes
- Rollback if needed

#### Verification
- Automatic syntax checking
- Execute repaired code
- Compare output
- Verify fix works

### Repair Workflow

1. **Generate Repair:**
   - Click "Repair" for AI-powered fix
   - Click "Quick Fix" for heuristic fix
   - System analyzes the error
   - Repair is generated

2. **Review Repair:**
   - View the diff (original vs proposed)
   - Read the explanation
   - Check the confidence score
   - Understand the changes

3. **Apply Repair:**
   - Click "Apply" to accept the fix
   - Click "Reject" to discard
   - If applied, code is updated in editor

4. **Verify Repair:**
   - Click "Verify" to test the fix
   - System executes the repaired code
   - Syntax is checked
   - Output is verified
   - Success/failure is reported

5. **Rollback (if needed):**
   - If verification fails, rollback
   - Original code is restored
   - Try a different approach

### Example Repair

**Original Code:**
```python
def calculate_total(price, quantity):
    return price * quantity

print(total_price)  # Error
```

**Repair:**
```python
def calculate_total(price, quantity):
    return price * quantity

total = calculate_total(100, 5)
print(total)  # Fixed
```

**Diff:**
```diff
- print(total_price)
+ total = calculate_total(100, 5)
+ print(total)
```

### Quick Tips
- Always review repairs before applying
- Quick Fix is faster but less accurate
- AI Repair is more accurate but slower
- Verification ensures the fix works
- Rollback is always available

---

## Module 6: Learning Centre

### Purpose
Learn debugging skills through interactive lessons and practice problems.

### Features

#### Structured Curriculum
- Organized by error type
- Progressive difficulty levels
- Real-world examples
- Step-by-step explanations

#### Interactive Lessons
- Code examples with errors
- Practice problems
- Solutions with explanations
- Follow-up questions

#### Error Pattern Learning
- Common error patterns
- How to identify them
- How to fix them
- How to prevent them

#### Learning Recommendations
- AI-powered suggestions
- Based on your recent errors
- Personalized learning path
- Progress tracking

### Lesson Structure

1. **Error Introduction:**
   - What is this error?
   - When does it occur?
   - Why does it happen?

2. **Code Example:**
   - Code with the error
   - Try to identify the issue
   - Run to see the error

3. **Explanation:**
   - Step-by-step breakdown
   - Root cause analysis
   - Prevention tips

4. **Practice:**
   - Similar error to fix
   - Apply what you learned
   - Check your solution

5. **Quiz:**
   - Test your understanding
   - Multiple choice questions
   - Instant feedback

### Available Lessons

**Beginner:**
- NameError: Undefined variables
- SyntaxError: Basic syntax mistakes
- IndentationError: Python indentation

**Intermediate:**
- TypeError: Type mismatches
- IndexError: List operations
- KeyError: Dictionary operations

**Advanced:**
- ZeroDivisionError: Division issues
- AttributeError: Object attributes
- ImportError: Module imports

### Learning Workflow

1. **Browse Lessons:**
   - Navigate to Learning Centre
   - Browse by category or difficulty
   - Read lesson descriptions

2. **Start Lesson:**
   - Click on a lesson
   - Read the introduction
   - Study the code example

3. **Practice:**
   - Try the practice problem
   - Apply the fix
   - Run to verify

4. **Take Quiz:**
   - Answer quiz questions
   - Get instant feedback
   - Review incorrect answers

5. **Track Progress:**
   - View completed lessons
   - See your learning path
   - Get recommendations

### Quick Tips
- Start with beginner lessons
- Practice regularly
- Use lessons alongside real debugging
- Ask follow-up questions for clarification

---

## Common Workflows

### Workflow 1: Fix a Simple Error

1. Go to Debugging Workspace
2. Write or paste your code
3. Click "Run Code" to see the error
4. Click "Analyze" to get diagnosis
5. Click "Repair" to get a fix
6. Review the diff
7. Click "Apply" to fix the code
8. Click "Verify" to test the fix

### Workflow 2: Analyze a Project

1. Go to Project Management
2. Click "New Project"
3. Upload your project as ZIP
4. Wait for extraction
5. Click "Analyze Project"
6. Review detected issues
7. Click on issues to see details
8. Apply fixes as needed
9. Download repaired project

### Workflow 3: Learn Debugging

1. Go to Learning Centre
2. Browse lessons by category
3. Start a lesson
4. Read the explanation
5. Practice with examples
6. Take the quiz
7. Track your progress
8. Move to next lesson

---

## Troubleshooting

### Common Issues

**"Session expired" error:**
- Your session token expired
- Click "Login" to refresh
- This is normal after inactivity

**"AI provider unavailable" error:**
- AI provider is down or quota exceeded
- System falls back to static analysis
- Check your AI provider settings

**"Execution timeout" error:**
- Code took too long to run
- Maximum is 5 seconds
- Optimize your code or split into smaller parts

**"File too large" error:**
- File exceeds size limit
- Maximum is 1 MB for analysis
- Split large files or upload as project

**"ZIP extraction failed" error:**
- ZIP file is corrupted
- ZIP contains invalid paths
- Check the ZIP file and try again

### Getting Help

1. Check the error message for details
2. Review the relevant section in this guide
3. Try the troubleshooting steps
4. Contact support if issues persist

---

## Tips for Effective Debugging

1. **Start Simple:** Begin with the simplest test case
2. **Read Errors:** Error messages tell you what's wrong
3. **Use Analysis:** Let AI help you understand the error
4. **Review Fixes:** Always review before applying
5. **Verify:** Always test after applying fixes
6. **Learn:** Use the Learning Centre to improve skills
7. **Save Sessions:** Save debugging sessions for reference
8. **Use Projects:** Organize related code in projects

---

## Keyboard Shortcuts

### Workspace
- `Ctrl+Enter` - Run code
- `Ctrl+A` - Select all code
- `Ctrl+Z` - Undo
- `Ctrl+Y` - Redo

### Navigation
- `#/dashboard` - Go to dashboard
- `#/workspace` - Go to workspace
- `#/projects` - Go to projects
- `#/learning` - Go to learning centre

---

## Best Practices

### Code Quality
- Write clear, readable code
- Use meaningful variable names
- Add comments for complex logic
- Follow PEP 8 style guide

### Debugging
- Start with the error message
- Reproduce the error consistently
- Simplify the problem
- Test fixes incrementally

### Project Management
- Organize code in logical folders
- Use descriptive file names
- Keep project size manageable
- Document your code

### Learning
- Practice regularly
- Learn from your mistakes
- Teach others what you learn
- Build a debugging toolkit

---

## Conclusion

BugSense AI is designed to make debugging easier and more efficient. By understanding the six modules and their workflows, you can leverage the full power of AI-assisted debugging to become a better developer.

For more technical details, see the [System Architecture](SYSTEM_ARCHITECTURE.md) documentation.
