#!/usr/bin/env python3
"""Agent-facing CLI. JSON on stdout, progress events on stderr. No real model by default."""

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import bench
from suites import EXAMPLE


def output(data):
    print(bench.dump(data), flush=True)


def load_suite(path):
    if path:
        source = Path(path)
        if source.stat().st_size > 2_000_000:
            raise ValueError("A bateria excede 2 MB")
        bench.configure_suite(bench.strict_json(source.read_text(encoding="utf-8-sig")))


def validate():
    cases = []
    for task in bench.TASKS:
        _, sources = bench.task_messages(task)
        found = {d["id"] for d in sources}
        missing = sorted(set(task["expected"].get("fontes", [])) - found) if task.get("mode") == "rag" else []
        score = bench.evaluate(task, bench.dump(bench.control_answer(task)))["score"]
        cases.append({"id": task["id"], "ok": score == 100 and not missing, "missing_sources": missing,
                      "retrieved_ids": [d["id"] for d in sources]})
    return {"ok": all(c["ok"] for c in cases), "suite": bench.CURRENT_SUITE["name"], "suite_hash": bench.SUITE_HASH,
            "case_count": len(cases), "cases": cases,
            "limits": "Confere formato, gabarito executável e recuperação; a veracidade dos fatos precisa ser revisada."}


def doctor(probe=True):
    gpu = []
    if shutil.which("nvidia-smi"):
        try:
            check = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                                   capture_output=True, text=True, timeout=8, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if check.returncode == 0:
                gpu = [line.strip() for line in check.stdout.splitlines() if line.strip()]
        except (OSError, subprocess.TimeoutExpired):
            pass
    runtimes = []
    if probe:
        for runtime, port in (("ollama", 11434), ("lmstudio", 1234), ("llamacpp", 8080)):
            url = f"http://127.0.0.1:{port}/v1"
            try:
                models = bench.list_models(url, runtime)
                runtimes.append({"runtime": runtime, "endpoint": url, "available": True, "models": models})
            except (ValueError, TypeError):
                runtimes.append({"runtime": runtime, "endpoint": url, "available": False, "models": []})
    return {"ok": sys.version_info >= (3, 10), "version": bench.VERSION, "python": platform.python_version(),
            "os": platform.system(), "architecture": platform.machine(), "cpu": platform.processor() or None,
            "nvidia_gpu_name_vram_mb_driver": gpu, "runtimes": runtimes,
            "local_data_dir": str(bench.ROOT / ".local"), "models_executed": 0,
            "next_step": "Use models para outra porta; valide a bateria; execute run somente dentro do escopo solicitado.",
            "hardware_limit": "Ausência de NVIDIA não implica ausência de GPU. Não estima RAM, memória livre nem garante que pesos caibam."}


def report(run_id, data_dir):
    if not re.fullmatch(r"[a-f0-9]{32}", run_id):
        raise ValueError("ID de execução inválido")
    path = Path(data_dir) / "runs" / (run_id + ".json")
    run = bench.strict_json(path.read_text(encoding="utf-8"))
    return {"ok": True, "run": run, "report_path": str(path.resolve())}


def run(args):
    load_suite(args.suite)
    valid = validate()
    if not valid["ok"]:
        output({"ok": False, "error": "Bateria inválida ou fontes esperadas ausentes; ajuste antes de inferir.", "validation": valid})
        return 2
    store = bench.Store(Path(args.data_dir) / "runs")
    previous = {r["id"] for r in store.runs}
    store.start({"endpoint": args.endpoint, "runtime": args.runtime, "models": args.model,
                 "profile": args.profile, "repeats": args.repeats, "temperature": args.temperature,
                 "max_tokens": args.max_tokens, "timeout": args.timeout, "hardware": args.hardware})
    last = None
    try:
        while True:
            with store.lock:
                active = dict(store.active) if store.active else None
            if active is None:
                break
            event = json.dumps({"event": "progress", **active}, ensure_ascii=False)
            if event != last and not args.quiet:
                print(event, file=sys.stderr, flush=True)
                last = event
            time.sleep(.2)
    except KeyboardInterrupt:
        store.cancel.set()
        while store.active:
            time.sleep(.2)
    runs = [r for r in store.runs if r["id"] not in previous]
    ok = bool(runs) and all(r["status"] == "completed" for r in runs) and len(runs) == len(args.model)
    errors = sum(r["summary"]["errors"] for r in runs)
    output({"ok": ok and not errors, "suite_hash": bench.SUITE_HASH,
            "runs": [{"id": r["id"], "model": r["model"], "status": r["status"], "protocol": r["protocol"],
                      "summary": r["summary"], "report_path": str((store.path / (r["id"] + ".json")).resolve())} for r in reversed(runs)],
            "next_step": "Use report para ler as respostas; abra bench.py com a mesma --suite para revisão humana."})
    return 0 if ok and not errors else 3


def main(argv=None):
    # JSON output stays UTF-8 in Windows pipes, including agent subprocesses.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="NegócioBench para agentes: saída JSON, execução local, sem dependências.")
    sub = parser.add_subparsers(dest="command", required=True)
    diag = sub.add_parser("doctor", help="Diagnóstico read-only; não executa modelos")
    diag.add_argument("--skip-probes", action="store_true", help="Não consultar servidores de inferência")
    models = sub.add_parser("models", help="Listar modelos locais em um endpoint")
    models.add_argument("--endpoint", required=True)
    models.add_argument("--runtime", choices=["ollama", "lmstudio", "llamacpp"], required=True)
    check = sub.add_parser("validate", help="Conferir contrato e RAG sem inferência")
    check.add_argument("--suite", type=Path)
    sub.add_parser("example", help="Imprimir exemplo de bateria JSON")
    execute = sub.add_parser("run", help="Executar a bateria com modelos explicitamente selecionados")
    execute.add_argument("--endpoint", required=True)
    execute.add_argument("--runtime", choices=["ollama", "lmstudio", "llamacpp"], required=True)
    execute.add_argument("--model", action="append", required=True, help="Repetível; use IDs retornados por models")
    execute.add_argument("--suite", type=Path)
    execute.add_argument("--profile", choices=["quick", "business", "rag", "contexto", "visao", "pagina", "full"], default="quick")
    execute.add_argument("--repeats", type=int, default=1)
    execute.add_argument("--temperature", type=float, default=0)
    execute.add_argument("--max-tokens", type=int, default=2048)
    execute.add_argument("--timeout", type=int, default=180)
    execute.add_argument("--hardware", default="Não informado")
    execute.add_argument("--quiet", action="store_true", help="Não imprimir progresso em stderr")
    execute.add_argument("--data-dir", type=Path, default=bench.ROOT / ".local")
    read = sub.add_parser("report", help="Ler um relatório de execução pelo ID")
    read.add_argument("--run-id", required=True)
    read.add_argument("--data-dir", type=Path, default=bench.ROOT / ".local")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            output(doctor(not args.skip_probes))
        elif args.command == "models":
            output({"ok": True, "models": bench.list_models(args.endpoint, args.runtime)})
        elif args.command == "validate":
            load_suite(args.suite)
            result = validate()
            output(result)
            return 0 if result["ok"] else 2
        elif args.command == "example":
            output(EXAMPLE)
        elif args.command == "report":
            output(report(args.run_id, args.data_dir))
        elif args.command == "run":
            return run(args)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        output({"ok": False, "error": str(exc), "command": args.command})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
