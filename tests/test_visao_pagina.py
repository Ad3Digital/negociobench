"""Contrato das trilhas de imagem e de página renderizada. Nenhuma inferência acontece aqui."""

import base64
import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import bench
from suites import BUILTIN, validate_suite


class VisaoTests(unittest.TestCase):
    def test_toda_imagem_referenciada_existe_e_e_png(self):
        for cid in bench.PROFILES["visao"]:
            task = bench.BY_ID[cid]
            with self.subTest(task=cid):
                bruto = base64.b64decode(BUILTIN["images"][task["image"]], validate=True)
                self.assertTrue(bruto.startswith(base64.b64decode("iVBORw0KGgo=")))
                self.assertLess(len(bruto), 1_000_000)

    def test_prompt_multimodal_carrega_a_imagem_embutida(self):
        task = bench.BY_ID["VI01"]
        partes = bench.task_messages(task)[0][1]["content"]
        self.assertIsInstance(partes, list)
        tipos = [p["type"] for p in partes]
        self.assertEqual(tipos, ["text", "image_url"])
        self.assertTrue(partes[1]["image_url"]["url"].startswith("data:image/png;base64,"))
        # O caso sem imagem continua mandando texto puro, como antes.
        self.assertIsInstance(bench.task_messages(bench.BY_ID["AT01"])[0][1]["content"], str)

    def test_imagem_inexistente_e_recusada_na_bateria(self):
        suite = json.loads(json.dumps(BUILTIN))
        suite["tasks"][0]["image"] = "nao-existe"
        with self.assertRaises(ValueError):
            validate_suite(suite)

    def test_base64_que_nao_e_png_e_recusado(self):
        suite = json.loads(json.dumps(BUILTIN))
        suite["images"] = {"falsa": base64.b64encode(b"GIF89a isto nao e png").decode()}
        with self.assertRaises(ValueError):
            validate_suite(suite)


class PaginaTests(unittest.TestCase):
    def test_campo_html_vale_por_forma_nao_por_igualdade(self):
        task = bench.BY_ID["PG01"]
        self.assertEqual(task["expected"]["html"], None)
        completo = bench.evaluate(task, bench.dump(bench.control_answer(task)))
        self.assertEqual(completo["score"], 100)
        checagem = next(c for c in completo["checks"] if c["field"] == "html")
        self.assertTrue(checagem["passed"])
        self.assertIn("caracteres de HTML", checagem["actual"])

    def test_html_vazio_ou_sem_marcacao_reprova(self):
        task = bench.BY_ID["PG01"]
        for valor in ("", "   ", None, "so texto sem marcacao nenhuma " * 10, "<p>curto</p>"):
            with self.subTest(valor=repr(valor)[:40]):
                resposta = {**bench.control_answer(task), "html": valor}
                avaliacao = bench.evaluate(task, bench.dump(resposta))
                self.assertLess(avaliacao["score"], 100)

    def test_render_html_exige_campo_html_no_gabarito(self):
        suite = json.loads(json.dumps(BUILTIN))
        suite["tasks"][0]["render"] = "html"
        with self.assertRaises(ValueError):
            validate_suite(suite)


class RenderEndpointTests(unittest.TestCase):
    """A página do modelo sai por rota própria, nunca injetada no documento do painel."""

    HTML = "<!doctype html><html><body><h1>ok</h1><p>" + "z" * 250 + "</p></body></html>"

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.tmp = tempfile.TemporaryDirectory()
        cls.app = bench.server(0, Path(cls.tmp.name))
        cls.base = f"http://127.0.0.1:{cls.app.server_port}"
        threading.Thread(target=cls.app.serve_forever, daemon=True).start()
        cls.app.store.runs.insert(0, {
            "id": "abc123", "status": "completed", "suite_hash": bench.SUITE_HASH,
            "results": [{"task_id": "PG01", "evaluation": {"answer": {"html": cls.HTML}}},
                        {"task_id": "AT01", "evaluation": {"answer": {"horario": "16:00"}}}]})

    @classmethod
    def tearDownClass(cls):
        cls.app.shutdown()
        cls.tmp.cleanup()

    def buscar(self, caminho):
        req = urllib.request.Request(self.base + caminho, headers={"Host": f"127.0.0.1:{self.app.server_port}"})
        return urllib.request.urlopen(req, timeout=10)

    def test_entrega_html_isolado_com_csp_de_sandbox(self):
        resposta = self.buscar("/api/render/abc123/0")
        corpo = resposta.read().decode()
        self.assertEqual(corpo, self.HTML)
        csp = resposta.headers["Content-Security-Policy"]
        self.assertTrue(csp.startswith("sandbox;"))
        for regra in ("default-src 'none'", "style-src 'unsafe-inline'", "img-src data:"):
            self.assertIn(regra, csp)
        self.assertNotIn("script-src 'self'", csp)

    def test_resposta_sem_html_e_indice_invalido_dao_404(self):
        for caminho in ("/api/render/abc123/1", "/api/render/abc123/9", "/api/render/naoexiste/0",
                        "/api/render/abc123/x", "/api/render/abc123"):
            with self.subTest(caminho=caminho), self.assertRaises(urllib.error.HTTPError) as erro:
                self.buscar(caminho)
            self.assertEqual(erro.exception.code, 404)
            erro.exception.close()


if __name__ == "__main__":
    unittest.main()
