import subprocess
import sys
import unittest

from support import ROOT, load

ci = load("oguzdows_ci_run", "scripts/ci-run.py")


class CIRunTests(unittest.TestCase):
    def command(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts/ci-run.py"), *args],
                              capture_output=True, text=True, check=False)

    def test_success_keeps_output_and_emits_no_failure_annotation(self):
        result = self.command("--", sys.executable, "-c", "print('tamam')")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "tamam\n")

    def test_failure_preserves_exit_code_and_reports_stderr(self):
        result = self.command("--title", "GTK, kontrolü", "--", sys.executable, "-c",
                              "import sys; print('asıl hata %', file=sys.stderr); sys.exit(7)")
        self.assertEqual(result.returncode, 7)
        self.assertIn("asıl hata %\n", result.stdout)
        self.assertIn("::error title=GTK%2C kontrolü::asıl hata %25%0A", result.stdout)

    def test_missing_program_is_reported_without_a_traceback(self):
        result = self.command("--", "/nonexistent/oguzdows-ci-command")
        self.assertEqual(result.returncode, 127)
        self.assertIn("::error", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_an_empty_command_is_rejected(self):
        self.assertEqual(self.command("--").returncode, 2)

    def test_workflow_command_escaping(self):
        self.assertEqual(ci.escape_data("%\r\n::x"), "%25%0D%0A::x")


if __name__ == "__main__":
    unittest.main()
