"""Contract and end-to-end checks. Fake inference only; never load a real model."""

import copy
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import bench
from suites import BUILTIN, EXAMPLE, validate_suite


class FakeInference(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, value):
        body = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.endswith("/redirect"):
            self.send_response(302)
            self.send_header("Location", "https://example.invalid/")
            self.end_headers()
        else:
            self.reply({"data": [{"id": "fixture-only"}, {"id": "remote-cloud"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        task = next(t for t in bench.TASKS if body["messages"][1]["content"].startswith(t["brief"]))
        self.reply({"choices": [{"message": {"content": json.dumps({**task["expected"], "resposta": "Resposta sintética do teste de software."})},
                                  "finish_reason": "stop"}], "usage": {"prompt_tokens": 100, "completion_tokens": 40}})


class ContractTests(unittest.TestCase):
    def setUp(self):
        bench.configure_suite(BUILTIN)

    def tearDown(self):
        bench.configure_suite(BUILTIN)

    def test_all_gold_and_rag_sources(self):
        for task in bench.TASKS:
            with self.subTest(task=task["id"]):
                self.assertEqual(bench.evaluate(task, bench.dump({**task["expected"], "resposta": "Controle."}))["score"], 100)
                messages, sources = bench.task_messages(task)
                self.assertNotIn('"expected"', messages[1]["content"])
                if task.get("mode") == "rag":
                    self.assertLessEqual(set(task["expected"]["fontes"]), {d["id"] for d in sources})
        hostile = bench.task_messages(bench.BY_ID["RA06"])[1]
        self.assertIn("ticket-externo", {d["id"] for d in hostile})

    def test_scorer_critical_failure_and_strict_types(self):
        task = bench.BY_ID["AT01"]
        answer = {**task["expected"], "resposta": "A reserva foi feita."}
        answer["reservar"] = True
        self.assertEqual(bench.evaluate(task, bench.dump(answer))["score"], 0)
        self.assertTrue(bench.evaluate(task, bench.dump(answer))["critical_failure"])
        self.assertFalse(bench.equivalent(True, 1))
        self.assertFalse(bench.equivalent("5", 5))
        self.assertFalse(bench.equivalent(float("nan"), 5))
        self.assertTrue(bench.equivalent(81.6, 81.60))
        self.assertFalse(bench.equivalent(["a", "a"], ["a", "b"]))
        self.assertTrue(bench.equivalent(["b", "a"], ["a", "b"]))
        self.assertFalse(bench.equivalent(["b", "a"], ["a", "b"], True))

    def test_invalid_json_and_reasoning_envelopes(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '[]', '{"x":1} texto', 'true'):
            with self.subTest(raw=raw):
                self.assertFalse(bench.evaluate(bench.TASKS[0], raw)["valid_json"])
        self.assertEqual(bench.parse_answer('<think>raciocínio</think>```json\n{"a":1}\n```'), {"a": 1})

    def test_external_endpoints_are_rejected(self):
        for value in ('https://example.com/v1', 'http://192.168.1.2:1234/v1', 'http://127.0.0.1:1234/v1?token=x',
                      'http://user:pass@127.0.0.1:1234/v1', 'http://localhost.evil:1234/v1', 'file:///etc/passwd',
                      'http://127.0.0.1:80/v1', 'http://localhost:1234/admin'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bench.endpoint_url(value)
        self.assertEqual(bench.endpoint_url('http://localhost:1234/v1/'), 'http://127.0.0.1:1234/v1')

    def test_suite_validation_and_versioning(self):
        original = bench.SUITE_HASH
        self.assertEqual(len(validate_suite(EXAMPLE)["tasks"]), 2)
        for change in ("duplicate", "missing_field", "unknown_source", "object_expected", "large_k"):
            bad = copy.deepcopy(EXAMPLE)
            if change == "duplicate": bad["tasks"].append(bad["tasks"][0])
            if change == "missing_field": bad["tasks"][0]["expected"].pop("total")
            if change == "unknown_source": bad["tasks"][1]["expected"]["fontes"] = ["unknown"]
            if change == "object_expected": bad["tasks"][0]["expected"]["total"] = {"x": 36}
            if change == "large_k": bad["top_k"] = 99
            with self.subTest(change=change), self.assertRaises(ValueError): validate_suite(bad)
        bench.configure_suite(EXAMPLE)
        self.assertNotEqual(original, bench.SUITE_HASH)
        self.assertEqual(len(bench.TASKS), 2)
        self.assertEqual({d["id"] for d in bench.task_messages(bench.TASKS[1])[1]}, {"cardapio-v1", "horario-v1"})


class AppTests(unittest.TestCase):
    def setUp(self):
        bench.configure_suite(BUILTIN)
        self.tmp = tempfile.TemporaryDirectory()
        self.app = bench.server(0, Path(self.tmp.name) / "runs")
        self.fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeInference)
        for server in (self.app, self.fake):
            threading.Thread(target=server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.app.server_port}"
        self.endpoint = f"http://127.0.0.1:{self.fake.server_port}/v1"

    def tearDown(self):
        for server in (self.app, self.fake):
            server.shutdown()
            server.server_close()
        self.tmp.cleanup()
        bench.configure_suite(BUILTIN)

    def request(self, path, data=None, headers=None):
        h = {"Content-Type": "application/json", "X-Bench-Token": self.app.store.token}
        h.update(headers or {})
        req = urllib.request.Request(self.base + path, data=json.dumps(data).encode() if data is not None else None, headers=h)
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.load(response)

    def test_http_origin_token_and_static_boundary(self):
        self.assertEqual(len(self.request('/api/state')["tasks"]), 30)
        for headers in ({"X-Bench-Token": "wrong"}, {"Origin": "https://example.invalid"}, {"Host": "evil.invalid"}):
            with self.subTest(headers=headers), self.assertRaises(urllib.error.HTTPError) as cm:
                self.request('/api/cancel', {}, headers)
            self.assertEqual(cm.exception.code, 403)
            cm.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.request('/../bench.py')
        self.assertEqual(cm.exception.code, 404)
        cm.exception.close()

    def test_model_discovery_and_no_redirect(self):
        self.assertEqual(bench.list_models(self.endpoint, "llamacpp"), ["fixture-only"])
        with self.assertRaises(ValueError): bench.local_request(self.endpoint, '/redirect')

    def test_run_persist_export_and_human_review(self):
        self.request('/api/run', {"endpoint": self.endpoint, "runtime": "llamacpp", "models": ["fixture-only"], "profile": "quick", "repeats": 1})
        deadline = time.monotonic() + 10
        while self.app.store.active and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertIsNone(self.app.store.active)
        run = self.request('/api/state')["runs"][0]
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["summary"]["score"], 100)
        self.assertEqual(run["summary"]["finished"], 6)
        row = run["results"][0]
        self.request('/api/review', {"run_id": run["id"], "task_id": row["task_id"], "repeat": 1,
                                     "utilidade": 3, "clareza": 4, "fidelidade": 3, "note": "Controle sintético, não é avaliação de IA."})
        exported = self.request('/api/export/' + run["id"])
        self.assertEqual(exported["summary"]["human_reviewed"], 1)
        self.assertNotIn("token", exported)
        restored = bench.Store(Path(self.tmp.name) / "runs")
        self.assertEqual(restored.runs[0]["results"][0]["human_review"]["clareza"], 4)

    def test_import_and_switch_isolate_results(self):
        old_hash = bench.SUITE_HASH
        self.request('/api/suite', EXAMPLE)
        new_state = self.request('/api/state')
        self.assertEqual(len(new_state["tasks"]), 2)
        self.assertEqual(new_state["suite_name"], "Minha cafeteria")
        saved_id = new_state["suite_hash"]
        self.request('/api/suite/reset', {})
        self.assertEqual(self.request('/api/state')["suite_hash"], old_hash)
        self.request('/api/suite/select', {"id": saved_id})
        self.assertEqual(self.request('/api/state')["suite_name"], "Minha cafeteria")
        with self.assertRaises(urllib.error.HTTPError) as cm: self.request('/api/suite/select', {"id": "../../secret"})
        cm.exception.close()


if __name__ == '__main__':
    unittest.main()
