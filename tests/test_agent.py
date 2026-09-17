"""Agent CLI checks with fake local inference and isolated output folders."""

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import bench
from suites import EXAMPLE, BUILTIN
from test_bench import FakeInference


class AgentTests(unittest.TestCase):
    def setUp(self):
        bench.configure_suite(BUILTIN)
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeInference)
        threading.Thread(target=self.fake.serve_forever, daemon=True).start()
        self.endpoint = f"http://127.0.0.1:{self.fake.server_port}/v1"

    def tearDown(self):
        self.fake.shutdown()
        self.fake.server_close()
        self.tmp.cleanup()

    def call(self, *args):
        result = subprocess.run([sys.executable, str(bench.ROOT / "agent.py"), *map(str, args)],
                                cwd=bench.ROOT, capture_output=True, text=True, encoding="utf-8", timeout=20)
        return result.returncode, json.loads(result.stdout)

    def test_example_and_custom_validation(self):
        code, data = self.call("example")
        self.assertEqual(code, 0)
        self.assertEqual(data, EXAMPLE)
        suite = self.data / "custom.json"
        suite.write_text(json.dumps(data), encoding="utf-8")
        code, validated = self.call("validate", "--suite", suite)
        self.assertEqual(code, 0)
        self.assertTrue(validated["ok"])
        self.assertEqual(validated["case_count"], 2)
        data["tasks"][1]["query"] = "zzzzunknownword"
        suite.write_text(json.dumps(data), encoding="utf-8")
        code, bad = self.call("validate", "--suite", suite)
        self.assertEqual(code, 2)
        self.assertEqual(bad["cases"][1]["missing_sources"], ["cardapio-v1"])

    def test_run_and_report(self):
        code, models = self.call("models", "--runtime", "llamacpp", "--endpoint", self.endpoint)
        self.assertEqual(code, 0)
        self.assertEqual(models["models"], ["fixture-only"])
        code, result = self.call("run", "--runtime", "llamacpp", "--endpoint", self.endpoint, "--model", "fixture-only",
                                 "--data-dir", self.data, "--profile", "rag", "--quiet")
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        self.assertEqual(result["runs"][0]["summary"]["finished"], 6)
        self.assertEqual(result["runs"][0]["summary"]["score"], 100)
        code, report = self.call("report", "--run-id", result["runs"][0]["id"], "--data-dir", self.data)
        self.assertEqual(code, 0)
        self.assertEqual(report["run"]["results"][0]["retrieval_recall"], 1)
        self.assertTrue(Path(report["report_path"]).is_file())

    def test_cli_respects_other_process_run_lock(self):
        store = bench.Store(self.data / "runs")
        store.acquire_inference()
        try:
            code, result = self.call("run", "--runtime", "llamacpp", "--endpoint", self.endpoint, "--model", "fixture-only",
                                     "--data-dir", self.data, "--quiet")
            self.assertEqual(code, 2)
            self.assertFalse(result["ok"])
            self.assertIn("Outra execução", result["error"])
        finally:
            store.release_inference()
        self.assertEqual(len(list((self.data / "runs").glob("*.json"))), 0)

    def test_missing_report_is_machine_readable(self):
        code, result = self.call("report", "--run-id", "../secret", "--data-dir", self.data)
        self.assertEqual(code, 2)
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
