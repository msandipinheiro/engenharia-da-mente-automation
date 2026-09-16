#!/usr/bin/env python3
"""
Lista e aprova posts da fila antes da publicação — a barreira humana do pipeline.
Uso:
    python scripts/fila_aprovacao.py --listar
    python scripts/fila_aprovacao.py --aprovar 2026-09-20
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue"

def listar():
    for f in sorted(QUEUE.glob("*.json")):
        payload = json.loads(f.read_text(encoding="utf-8"))
        print(f"{f.stem}  [{payload.get('status')}]  {payload.get('legenda','')[:70]}")

def aprovar(data: str):
    f = QUEUE / f"{data}.json"
    payload = json.loads(f.read_text(encoding="utf-8"))
    if payload.get("status") != "pronto_para_aprovacao":
        raise SystemExit(f"Post {data} está em status '{payload.get('status')}', não em "
                          f"'pronto_para_aprovacao'. Gere a mídia antes de aprovar.")
    payload["status"] = "aprovado"
    f.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Post {data} aprovado. Agora pode ser publicado.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--listar", action="store_true")
    g.add_argument("--aprovar", metavar="DATA")
    args = parser.parse_args()
    if args.listar:
        listar()
    else:
        aprovar(args.aprovar)
