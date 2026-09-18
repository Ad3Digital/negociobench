"""Declarative suites: JSON data only. Imported files never execute code."""

import base64
import binascii
import math
import re
from cases import CASES, CATEGORIES, IMAGES, VERSION
from knowledge import DOCUMENTS, RAG_CASES

BUILTIN = {"schema_version": 1, "name": "Negócios locais & digitais", "description": "43 desafios sintéticos criados pela AD3.",
           "top_k": 4, "documents": DOCUMENTS, "images": IMAGES, "tasks": CASES + RAG_CASES}

EXAMPLE = {
    "schema_version": 1,
    "name": "Minha cafeteria",
    "description": "Exemplo fictício editável: oferta e atendimento com RAG.",
    "top_k": 3,
    "documents": [
        {"id": "cardapio-v1", "title": "Cardápio aprovado", "text": "Cafeteria fictícia Pátio. Combo café e pão: R$ 18. Disponível de segunda a sexta, 8h às 11h. Somente retirada. Preço de delivery não informado."},
        {"id": "horario-v1", "title": "Horário de funcionamento", "text": "A Cafeteria Pátio abre de segunda a sexta das 8h às 18h. Fecha sábado e domingo."}
    ],
    "tasks": [
        {"id": "MEU01", "title": "Calcular dois combos", "category": "vendas", "track": "local", "difficulty": "Essencial",
         "mode": "direct", "brief": "Cada combo custa R$ 18. Um cliente quer dois. Calcule o total e escreva a resposta.",
         "fields": {"quantidade": "número", "total": "número"}, "expected": {"quantidade": 2, "total": 36},
         "critical": [], "rubric": ["O texto é acolhedor e informa o total sem confundir?"]},
        {"id": "MEU02", "title": "Atendimento pelo cardápio", "category": "atendimento", "track": "local", "difficulty": "Intermediário",
         "mode": "rag", "query": "Cafeteria Pátio combo café pão preço delivery retirada",
         "brief": "Quanto custa o combo café e pão? Tem delivery? Consulte a base e cite a fonte.",
         "fields": {"preco": "número", "delivery": "booleano", "fontes": "lista de IDs dos documentos"},
         "expected": {"preco": 18, "delivery": False, "fontes": ["cardapio-v1"]}, "critical": ["delivery"],
         "rubric": ["O cliente entende a oferta e como retirar?", "A resposta se limita aos fatos documentados?"]}
    ]
}


def text(value, label, limit=20000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{label}: texto obrigatório, máximo {limit} caracteres")
    return value.strip()


def identifier(value, label):
    value = text(value, label, 80)
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", value):
        raise ValueError(f"{label}: use apenas letras sem acento, números, _ e -")
    return value


def scalar(value):
    return value is None or type(value) in (str, bool, int) or (type(value) is float and math.isfinite(value))


# Uma imagem chega em base64 e so e aceita como PNG: o prompt multimodal carrega
# o proprio dado, entao a bateria nunca aponta para arquivo fora dela.
PNG = base64.b64decode("iVBORw0KGgo=")


def imagens(data):
    if not isinstance(data, dict) or len(data) > 20:
        raise ValueError("Use até 20 imagens na bateria")
    saida = {}
    for chave, valor in data.items():
        nome = identifier(chave, "ID da imagem")
        if not isinstance(valor, str) or len(valor) > 1_400_000:
            raise ValueError(f"{nome}: imagem em base64, máximo 1 MB por arquivo")
        try:
            bruto = base64.b64decode(valor, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError(f"{nome}: base64 inválido") from exc
        if not bruto.startswith(PNG):
            raise ValueError(f"{nome}: somente PNG é aceito")
        saida[nome] = valor
    return saida


def validate_suite(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("A bateria precisa de schema_version: 1")
    result = {"schema_version": 1, "name": text(data.get("name"), "Nome", 100),
              "description": text(data.get("description", "Bateria personalizada"), "Descrição", 500)}
    top_k = data.get("top_k", 4)
    if type(top_k) is not int or not 1 <= top_k <= 10:
        raise ValueError("top_k deve ser inteiro entre 1 e 10")
    result["top_k"] = top_k
    result["images"] = imagens(data.get("images", {}))
    docs = data.get("documents", [])
    tasks = data.get("tasks")
    if not isinstance(docs, list) or len(docs) > 100:
        raise ValueError("Use até 100 trechos na base de conhecimento")
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 100:
        raise ValueError("Use entre 1 e 100 casos")
    result["documents"] = []
    ids = set()
    for doc in docs:
        if not isinstance(doc, dict):
            raise ValueError("Documento precisa ser objeto")
        did = identifier(doc.get("id"), "ID do documento")
        if did in ids:
            raise ValueError("ID de documento repetido")
        ids.add(did)
        result["documents"].append({"id": did, "title": text(doc.get("title"), "Título", 200), "text": text(doc.get("text"), "Conteúdo", 6000)})
    result["tasks"] = []
    tids = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("Caso precisa ser objeto")
        cid = identifier(task.get("id"), "ID do caso")
        if cid in tids:
            raise ValueError("ID de caso repetido")
        tids.add(cid)
        cat = task.get("category")
        if cat not in {c["id"] for c in CATEGORIES}:
            raise ValueError(f"{cid}: categoria desconhecida")
        track = task.get("track", "ambos")
        mode = task.get("mode", "direct")
        if track not in ("local", "digital", "ambos") or mode not in ("direct", "rag"):
            raise ValueError(f"{cid}: track ou mode inválido")
        fields, expected = task.get("fields"), task.get("expected")
        if not isinstance(fields, dict) or not isinstance(expected, dict) or not 1 <= len(fields) <= 20 or fields.keys() != expected.keys():
            raise ValueError(f"{cid}: fields e expected precisam ter os mesmos 1 a 20 campos")
        for field, value in fields.items():
            identifier(field, "Nome de campo")
            text(value, "Descrição de campo", 400)
            if field == "resposta":
                raise ValueError("resposta é acrescentado automaticamente; não inclua no gabarito")
            gold = expected[field]
            if not scalar(gold) and not (isinstance(gold, list) and len(gold) <= 100 and all(scalar(v) for v in gold)):
                raise ValueError(f"{cid}.{field}: gabarito deve ser texto, número, booleano, null ou lista simples")
            if isinstance(gold, str) and len(gold) > 2000:
                raise ValueError("Gabarito textual longo; prefira campos objetivos e rubric para texto livre")
        critical = task.get("critical", [])
        if not isinstance(critical, list) or any(not isinstance(k, str) or k not in expected for k in critical):
            raise ValueError(f"{cid}: critical deve listar campos existentes")
        rubric = task.get("rubric", ["A resposta é útil, clara e fiel ao briefing?"])
        if not isinstance(rubric, list) or not 1 <= len(rubric) <= 8:
            raise ValueError("Use de 1 a 8 critérios humanos")
        row = {"id": cid, "title": text(task.get("title"), "Título", 150), "category": cat, "track": track,
               "difficulty": text(task.get("difficulty", "Personalizado"), "Dificuldade", 40), "mode": mode,
               "brief": text(task.get("brief"), "Briefing"), "fields": fields, "expected": expected,
               "critical": critical, "rubric": [text(r, "Rubrica", 500) for r in rubric]}
        imagem = task.get("image")
        if imagem is not None:
            imagem = identifier(imagem, "Imagem do caso")
            if imagem not in result["images"]:
                raise ValueError(f"{cid}: imagem {imagem} não existe nesta bateria")
            row["image"] = imagem
        render = task.get("render")
        if render is not None:
            if render != "html":
                raise ValueError(f"{cid}: render aceita apenas \"html\"")
            if "html" not in fields:
                raise ValueError(f"{cid}: render html exige um campo \"html\" no gabarito")
            row["render"] = render
        if mode == "rag":
            row["query"] = text(task.get("query"), "Consulta RAG", 1000)
            if not docs or not isinstance(expected.get("fontes"), list) or any(f not in ids for f in expected["fontes"]):
                raise ValueError(f"{cid}: RAG exige documentos e expected.fontes com IDs válidos")
            if len(expected["fontes"]) > top_k:
                raise ValueError(f"{cid}: há mais fontes esperadas que top_k")
        result["tasks"].append(row)
    return result
