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
