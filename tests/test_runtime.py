import subprocess
import sys
import os
import unittest
from pathlib import Path


class RuntimeTests(unittest.TestCase):
    def test_real_startup_migration_database_and_console(self):
        result = subprocess.run([sys.executable, '-m', 'tests.runtime_check'],
            cwd=Path(__file__).parents[1], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS legacy migration', result.stdout)

    def test_binding_commands_and_localstore_persistence(self):
        result = subprocess.run([sys.executable, '-m', 'tests.binding_runtime_check'],
            cwd=Path(__file__).parents[1], capture_output=True, text=True, timeout=60,
            env={**os.environ, 'APEX_TEST_DEFAULT_DB': '1'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS name/UID binding', result.stdout)
