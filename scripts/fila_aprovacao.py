#!/usr/bin/env python3
"""
Lista e aprova posts da fila antes da publicação — a barreira humana do pipeline.

Uso (comportamento original — Engenharia da Mente):
    python scripts/fila_aprovacao.py --listar
    python scripts/fila_aprovacao.py --aprovar 2026-09-20

Uso multi-marca (novo, opcional):
    python scripts/fila_aprovacao.py --marca divino-inconsciente --listar
    python scripts/fila_aprovacao.py --marca divino-inconsciente --aprovar 2026-10-01
"""
import argparse
import json
from pathlib import Path

from fila_utils import adicionar_arg_marca, avisos_de_conflito, carregar_item, eh_avulso, queue_dir, salvar_item

ROOT = Path(__file__).resolve().parent.parent


def listar(queue: Path):
    grupos = {"calendario": [], "avulsos": []}
    for f in sorted(queue.glob("*.json")):
        payload = json.loads(f.read_text(encoding="utf-8"))
        grupo = "avulsos" if eh_avulso(payload) else "calendario"
        grupos[grupo].append((f, payload))
    for titulo in ("CALENDARIO", "AVULSOS"):
        print(f"\n[{titulo}]")
        for f, payload in grupos["avulsos" if titulo == "AVULSOS" else "calendario"]:
            print(f"{f.stem}  [{payload.get('status')}]  {payload.get('legenda','')[:70]}")


def aprovar(identifier: str, queue: Path):
    f, payload = carregar_item(identifier, queue)
    if payload.get("status") != "pronto_para_aprovacao":
        raise SystemExit(f"Post {identifier} está em status '{payload.get('status')}', não em "
                          f"'pronto_para_aprovacao'. Gere a mídia antes de aprovar.")
    for aviso in avisos_de_conflito(f, payload, queue):
        print(aviso)
    payload["status"] = "aprovado"
    salvar_item(f, payload)
    print(f"Post {f.stem} aprovado. Agora pode ser publicado.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    adicionar_arg_marca(parser)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--listar", action="store_true")
    g.add_argument("--aprovar", metavar="ID_OU_DATA")
    args = parser.parse_args()

    queue = queue_dir(ROOT, args.marca)
    if args.listar:
        listar(queue)
    else:
        aprovar(args.aprovar, queue)
