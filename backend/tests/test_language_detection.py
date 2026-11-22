"""Language detection and multi-language routing tests.

Covers the five required scenarios (Java, C, Python, C++, JavaScript) plus
C/C++ header disambiguation and compiler-error dispatch. These tests assert
that source is never routed to the Python parser just because Python is the
default selection.
"""
import shutil
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from sandbox.runners import get_runner, supported_execution_languages
from services.code_analyzer import CodeAnalyzer
from services.language_detector import LanguageDetector

JAVA_SOURCE = """import java.util.*;

public class StudentManagement {
    public static void main(String[] args) {
        System.out.println("Hello, students");
    }
}
"""

C_SOURCE = """#include <stdio.h>

int main(void) {
    printf("Hello, C\\n");
    return 0;
}
"""

PYTHON_SOURCE = """def calculate_average(numbers):
    return sum(numbers) / len(numbers)


print(calculate_average([10, 20, 30]))
"""

CPP_SOURCE = """#include <iostream>
using namespace std;

int main() {
    cout << "Hello, C++" << endl;
    return 0;
}
"""

JAVASCRIPT_SOURCE = """function greet(name) {
    console.log("Hello, " + name);
}

greet("students");
"""


class LanguageDetectionTests(SimpleTestCase):
    def test_java_is_detected(self):
        result = LanguageDetector.detect(JAVA_SOURCE)
        self.assertTrue(result.confident)
        self.assertEqual(result.language, 'java')

    def test_c_is_detected(self):
        result = LanguageDetector.detect(C_SOURCE)
        self.assertTrue(result.confident)
        self.assertEqual(result.language, 'c')

    def test_python_is_detected(self):
        result = LanguageDetector.detect(PYTHON_SOURCE)
        self.assertTrue(result.confident)
        self.assertEqual(result.language, 'python')

    def test_cpp_is_detected(self):
        result = LanguageDetector.detect(CPP_SOURCE)
        self.assertTrue(result.confident)
        self.assertEqual(result.language, 'cpp')

    def test_javascript_is_detected(self):
        result = LanguageDetector.detect(JAVASCRIPT_SOURCE)
        self.assertTrue(result.confident)
        self.assertEqual(result.language, 'javascript')

    def test_java_detected_without_extension(self):
        # No filename is provided; detection must be driven purely by the source.
        result = LanguageDetector.detect(JAVA_SOURCE, filename=None)
        self.assertEqual(result.language, 'java')

    def test_extension_is_a_hint_not_a_decision(self):
        # A filename alone, with no recognisable code, must not force a language.
        result = LanguageDetector.detect('', filename='main.java')
        self.assertFalse(result.confident)

    def test_ambiguous_source_requests_clarification(self):
        result = LanguageDetector.detect('x = 1\ny = 2\n')
        self.assertFalse(result.confident)
        self.assertIsNone(result.language)

    def test_c_and_cpp_disambiguated_by_headers(self):
        self.assertEqual(LanguageDetector.detect(C_SOURCE).language, 'c')
        self.assertEqual(LanguageDetector.detect(CPP_SOURCE).language, 'cpp')

    def test_detection_result_serialises(self):
        payload = LanguageDetector.detect(JAVA_SOURCE).to_dict()
        self.assertEqual(payload['language'], 'java')
        self.assertTrue(payload['confident'])
        self.assertIn('evidence', payload)


class ExecutionRoutingTests(SimpleTestCase):
    def test_all_languages_have_a_runner(self):
        for language in ('python', 'java', 'c', 'cpp', 'javascript'):
            with self.subTest(language=language):
                self.assertIsNotNone(get_runner(language))

    def test_supported_languages_registry(self):
        self.assertCountEqual(
            supported_execution_languages(),
            ['python', 'java', 'c', 'cpp', 'javascript'],
        )

    def test_unknown_language_has_no_runner(self):
        self.assertIsNone(get_runner('ruby'))


class CompilerDispatchTests(SimpleTestCase):
    def test_java_errors_come_from_javac_not_python(self):
        with patch(
            'sandbox.runners.JavaRunner.execute',
            return_value=(1, '', 'Main.java:5: error: \';\' expected', 12.0),
        ):
            errors = CodeAnalyzer.check_syntax_for_language(JAVA_SOURCE, 'java')
        self.assertTrue(errors)
        self.assertEqual(errors[0].line, 5)
        self.assertIn('expected', errors[0].message)

    def test_c_errors_come_from_gcc(self):
        with patch(
            'sandbox.runners.CRunner.execute',
            return_value=(1, '', 'main.c:3:5: error: expected initializer', 8.0),
        ):
            errors = CodeAnalyzer.check_syntax_for_language(C_SOURCE, 'c')
        self.assertTrue(errors)
        self.assertEqual(errors[0].line, 3)

    def test_cpp_errors_come_from_gpp(self):
        with patch(
            'sandbox.runners.CppRunner.execute',
            return_value=(1, '', 'main.cpp:4:12: error: expected primary-expression', 9.0),
        ):
            errors = CodeAnalyzer.check_syntax_for_language(CPP_SOURCE, 'cpp')
        self.assertTrue(errors)
        self.assertEqual(errors[0].line, 4)

    def test_clean_compilation_reports_no_errors(self):
        with patch(
            'sandbox.runners.JavaRunner.execute',
            return_value=(0, '', '', 10.0),
        ):
            errors = CodeAnalyzer.check_syntax_for_language(JAVA_SOURCE, 'java')
        self.assertEqual(errors, [])

    def test_python_dispatch_does_not_invoke_compilers(self):
        with patch('sandbox.runners.JavaRunner.execute') as java_exec:
            errors = CodeAnalyzer.check_syntax_for_language(PYTHON_SOURCE, 'python')
        self.assertEqual(errors, [])
        java_exec.assert_not_called()


class AnalysisRoutingTests(SimpleTestCase):
    def test_java_error_is_analyzed_as_java(self):
        context = CodeAnalyzer.analyze_error_context(
            JAVA_SOURCE, "Main.java:5: error: ';' expected", language='java'
        )
        self.assertEqual(context.get('programming_language'), 'java')

    def test_python_error_is_analyzed_as_python(self):
        context = CodeAnalyzer.analyze_error_context(
            "print(1/0)", 'ZeroDivisionError: division by zero', language='python'
        )
        self.assertEqual(context.get('programming_language'), 'python')


class ExecutionToolchainTests(SimpleTestCase):
    """End-to-end execution through the real toolchains, when available.

    These tests run only when a toolchain is installed locally and execution is
    enabled, so CI machines without compilers still pass (they skip instead of
    failing). Each runner must use its own toolchain — never the Python parser.
    """

    def setUp(self):
        if not getattr(settings, 'EXECUTION_ENABLED', False):
            self.skipTest('EXECUTION_ENABLED is false in this environment')

    def test_python_runs_through_python_runner(self):
        runner = get_runner('python')
        exit_code, stdout, _stderr, _duration = runner.execute(PYTHON_SOURCE, timeout=10)
        self.assertEqual(exit_code, 0)
        self.assertIn('20.0', stdout)

    def test_java_runs_through_javac_and_java(self):
        if not (shutil.which('javac') and shutil.which('java')):
            self.skipTest('javac/java not installed')
        exit_code, stdout, stderr, _duration = get_runner('java').execute(JAVA_SOURCE, timeout=30)
        self.assertEqual(exit_code, 0, msg=stderr)
        self.assertIn('Hello, students', stdout)

    def test_javascript_runs_through_node(self):
        if not shutil.which('node'):
            self.skipTest('node not installed')
        exit_code, stdout, stderr, _duration = get_runner('javascript').execute(JAVASCRIPT_SOURCE, timeout=15)
        self.assertEqual(exit_code, 0, msg=stderr)
        self.assertIn('Hello, students', stdout)

    def test_c_runs_through_gcc(self):
        if not (shutil.which('gcc') or shutil.which('cc')):
            self.skipTest('gcc not installed')
        exit_code, stdout, stderr, _duration = get_runner('c').execute(C_SOURCE, timeout=15)
        self.assertEqual(exit_code, 0, msg=stderr)
        self.assertIn('Hello, C', stdout)

    def test_cpp_runs_through_gpp(self):
        if not (shutil.which('g++') or shutil.which('c++')):
            self.skipTest('g++ not installed')
        exit_code, stdout, stderr, _duration = get_runner('cpp').execute(CPP_SOURCE, timeout=15)
        self.assertEqual(exit_code, 0, msg=stderr)
        self.assertIn('Hello, C++', stdout)

    def test_java_compile_error_is_reported_by_javac(self):
        if not (shutil.which('javac') and shutil.which('java')):
            self.skipTest('javac/java not installed')
        broken = JAVA_SOURCE.replace('System.out.println("Hello, students");', 'System.out.println("Hello, students")')
        exit_code, _stdout, stderr, _duration = get_runner('java').execute(broken, timeout=30)
        self.assertNotEqual(exit_code, 0)
        self.assertIn('error:', stderr.lower())
