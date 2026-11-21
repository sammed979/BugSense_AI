from django.test import SimpleTestCase

from services.code_analyzer import CodeAnalyzer


class UndefinedNameScopeTests(SimpleTestCase):
    def test_function_parameter_is_not_undefined(self):
        code = "def check_result(marks):\n    return marks > 40\n"
        self.assertEqual(CodeAnalyzer.extract_undefined_names(code), [])

    def test_unbound_name_is_reported(self):
        code = "numbers = [10, 20]\nprint(number)\n"
        self.assertEqual(CodeAnalyzer.extract_undefined_names(code), ['number'])

    def test_imports_builtins_and_local_assignments_are_bound(self):
        code = "import math\ndef area(radius):\n    squared = radius * radius\n    return math.pi * squared\nprint(area(2))\n"
        self.assertEqual(CodeAnalyzer.extract_undefined_names(code), [])

    def test_nested_function_resolves_closure_variable(self):
        code = "def outer(value):\n    def inner():\n        return value\n    return inner()\n"
        self.assertEqual(CodeAnalyzer.extract_undefined_names(code), [])


class EducationalDiagnosisTests(SimpleTestCase):
    def test_python_traceback_matrix_keeps_exact_exception_and_location(self):
        cases = [
            ('KeyError', "return users['mark']", "KeyError: 'mark'"),
            ('TypeError', 'return 1 + "2"', "TypeError: unsupported operand type(s) for +: 'int' and 'str'"),
            ('NameError', 'return missing_total', "NameError: name 'missing_total' is not defined"),
            ('IndexError', 'return values[3]', 'IndexError: list index out of range'),
            ('ZeroDivisionError', 'return total / count', 'ZeroDivisionError: division by zero'),
            ('ImportError', 'import unknown_module', "ImportError: cannot import name 'x' from 'unknown_module'"),
            ('SyntaxError', 'def broken(:', 'SyntaxError: invalid syntax'),
        ]
        for exception_type, source_line, final_line in cases:
            with self.subTest(exception_type=exception_type):
                source = f'def run():\n    {source_line}\n'
                log = (
                    'Traceback (most recent call last):\n'
                    '  File "student.py", line 2, in run\n'
                    f'    {source_line}\n'
                    f'{final_line}'
                )
                diagnosis = CodeAnalyzer.analyze_error_context(source, log)
                self.assertEqual(diagnosis['error_category'], exception_type)
                self.assertEqual(diagnosis['affected_file'], 'student.py')
                self.assertEqual(diagnosis['affected_line'], 2)
                self.assertEqual(diagnosis['failing_source_line'].strip(), source_line)
                self.assertEqual(diagnosis['detection_source'], 'deterministic')
                self.assertTrue(diagnosis['fix_steps'])
                self.assertTrue(diagnosis['confirmed_findings'])
                self.assertTrue(diagnosis['likely_root_cause'])

    def test_keyerror_correction_uses_submitted_source_and_marks_uncertainty(self):
        code = "def find_user(users):\n    return users['mark']\n"
        traceback = (
            'Traceback (most recent call last):\n'
            '  File "users.py", line 2, in find_user\n'
            "    return users['mark']\n"
            "KeyError: 'mark'"
        )
        diagnosis = CodeAnalyzer.analyze_error_context(code, traceback)
        self.assertEqual(diagnosis['exception_type'], 'KeyError')
        self.assertIn("users.get('mark')", diagnosis['suggested_code'])
        self.assertIn('does not establish', diagnosis['likely_root_cause'])
        self.assertIn('optional', ' '.join(diagnosis['fix_steps']).lower())

    def test_source_without_runtime_error_still_reports_python_syntax_error(self):
        diagnosis = CodeAnalyzer.analyze_error_context('def broken(:\n    pass\n', 'No error message')
        self.assertEqual(diagnosis['error_category'], 'SyntaxError')
        self.assertEqual(diagnosis['detection_source'], 'deterministic')
        self.assertTrue(diagnosis['fix_steps'])
