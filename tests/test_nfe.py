"""Recalcula os gabaritos da trilha de documento longo a partir do XML da propria nota.

Se a NF-e ficticia mudar, estes testes falham antes de um modelo ser cobrado por um
gabarito desatualizado. Nenhuma inferencia acontece aqui.
"""

import math
import re
import unittest
import xml.etree.ElementTree as ET

import bench
from cases import NFE

ST_CST = {"10", "30", "60", "70"}
ST_CSOSN = {"201", "202", "203", "500"}
AMBIGUO = {"90", "900"}
PARCELAS = ("vProd", "vFrete", "vSeg", "vOutro", "vIPI", "vICMSST", "vFCPST")


def valor(no, tag):
    achado = no.find(f".//{tag}")
    return float(achado.text) if achado is not None else 0.0


def texto(no, tag):
    achado = no.find(f".//{tag}")
    return achado.text if achado is not None else None


def itens():
    raiz = ET.fromstring(NFE)
    for det in raiz.findall(".//det"):
        prod = det.find("prod")
        imposto = det.find("imposto")
        yield {
            "cProd": prod.find("cProd").text,
            "xProd": prod.find("xProd").text,
            "qCom": float(prod.find("qCom").text),
            "pICMS": valor(imposto, "pICMS"),
            "vICMSST": valor(imposto, "vICMSST"),
            "CST": texto(imposto, "CST"),
            "CSOSN": texto(imposto, "CSOSN"),
            "custo": sum(valor(det, t) for t in PARCELAS) - valor(prod, "vDesc"),
        }


def em_st(item):
    return item["vICMSST"] > 0 or item["CST"] in ST_CST or item["CSOSN"] in ST_CSOSN


def complemento(item):
    if em_st(item) or item["CST"] in AMBIGUO or item["CSOSN"] in AMBIGUO:
        return 0.0
    return max(0.0, 17.0 - item["pICMS"])


def preco(reposicao, pontos):
    return math.ceil(round(reposicao * 2.20 * (1 + pontos / 100) * 20, 6)) / 20


class NotaFiscalTests(unittest.TestCase):
    def setUp(self):
        self.itens = {item["cProd"]: item for item in itens()}
        self.casos = {t["id"]: t for t in bench.TASKS}

    def gabarito(self, cid):
        return self.casos[cid]["expected"]

    def test_a_nota_esta_inteira_no_briefing(self):
        for cid in bench.PROFILES["contexto"]:
            self.assertIn("<nfeProc", self.casos[cid]["brief"])
            self.assertIn("</nfeProc>", self.casos[cid]["brief"])
        self.assertEqual(len(self.itens), 12)

    def test_nf01_rateio(self):
        item = self.itens["PIN1001"]
        esperado = self.gabarito("NF01")
        self.assertAlmostEqual(item["custo"], esperado["custo_total_item"], places=2)
        self.assertAlmostEqual(item["custo"] / item["qCom"], esperado["reposicao_unitaria"], places=2)

    def test_nf02_substituicao_tributaria(self):
        esperado = self.gabarito("NF02")
        calculados = sorted(c for c, i in self.itens.items() if em_st(i))
        self.assertEqual(calculados, sorted(esperado["itens_com_st"]))
        ambiguos = [c for c, i in self.itens.items() if i["CST"] in AMBIGUO or i["CSOSN"] in AMBIGUO]
        self.assertEqual(ambiguos, [esperado["item_ambiguo"]])
        self.assertAlmostEqual(complemento(self.itens["PIN1002"]), esperado["complemento_PIN1002"], places=2)
        # O item 1002 carrega CST 60 com vICMSST zerado: decidir pelo valor erraria aqui.
        self.assertEqual(self.itens["PIN1002"]["vICMSST"], 0.0)
        self.assertTrue(em_st(self.itens["PIN1002"]))

    def test_nf03_margem_complemento_e_piso_de_preco(self):
        item = self.itens["PIN1001"]
        esperado = self.gabarito("NF03")
        reposicao = item["custo"] / item["qCom"]
        sugerido = preco(reposicao, complemento(item))
        self.assertAlmostEqual(sugerido, esperado["preco_sugerido"], places=2)
        cadastrado = esperado["preco_final"]
        self.assertTrue(esperado["manter_preco_anterior"] is (cadastrado > sugerido))
        self.assertAlmostEqual(max(sugerido, cadastrado), cadastrado, places=2)

    def test_nf04_dado_ausente_continua_ausente(self):
        esperado = self.gabarito("NF04")
        self.assertIsNone(esperado["preco_venda_anterior"])
        self.assertIsNone(esperado["estoque_atual"])
        for termo in ("PRECO_VENDA", "ESTOQUE", "QUANTIDADE_ATUAL"):
            self.assertNotIn(termo, NFE.upper())

    def test_nf05_conversao_de_rolo_para_metro(self):
        esperado = self.gabarito("NF05")
        item = self.itens[esperado["codigo_produto"]]
        self.assertIn("CORDA", item["xProd"].upper())
        metros = float(re.search(r"(\d+)M\b", item["xProd"].upper()).group(1))
        custo_metro = item["custo"] / metros
        self.assertAlmostEqual(custo_metro, esperado["custo_metro"], places=2)
        self.assertAlmostEqual(preco(custo_metro, complemento(item)), esperado["preco_metro"], places=2)


if __name__ == "__main__":
    unittest.main()
