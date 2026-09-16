#!/usr/bin/env python3
"""
Lê o calendário editorial e gera o rascunho de copy do dia via Claude API.
Uso: python scripts/planejar_post.py --dia 14
"""
import argparse
import csv
import json
import os
import yaml
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def carregar_brand():
    return yaml.safe_load((ROOT / "config" / "brand.yaml").read_text(encoding="utf-8"))

def carregar_linha_calendario(dia: int):
    cfg = yaml.safe_load((ROOT / "config" / "calendar_source.yaml").read_text(encoding="utf-8"))
    with open(ROOT / cfg["path"], encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if int(row[cfg["columns"]["dia"]]) == dia:
                return row
    raise ValueError(f"Dia {dia} não encontrado no calendário")

def data_real_do_dia(dia: int, data_ancora: date, dia_ancora: int) -> date:
    """Converte 'Dia N' do calendário para uma data real, dado um ponto de ancoragem
    (ex.: dia 17 = data da última chamada). Ajuste os valores default no __main__.
    """
    return data_ancora + timedelta(days=dia - dia_ancora)

def gerar_copy(brand: dict, linha_calendario: dict) -> dict:
    """
    TODO: chamar a API da Claude aqui, por exemplo:

        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=f"Tom de voz: {brand['tom_de_voz']}. Nunca capacitista...",
            messages=[{"role": "user", "content": f"Gere a legenda para: {linha_calendario}"}],
        )

    Por ora, devolve um placeholder para você testar o pipeline ponta a ponta
    antes de plugar a chamada real.
    """
    return {
        "legenda": f"[RASCUNHO — preencher via Claude API] {linha_calendario['Conteúdo']}",
        "cta": linha_calendario["CTA"],
        "formato": linha_calendario["Formato"],
        "fase": linha_calendario["Fase"],
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dia", type=int, required=True, help="Número do dia no calendário (1-21)")
    parser.add_argument("--data-ancora", type=str, default="2026-09-21", help="Data real de um dia-âncora (AAAA-MM-DD)")
    parser.add_argument("--dia-ancora", type=int, default=17, help="Número do dia do calendário que corresponde à data-ancora")
    args = parser.parse_args()

    brand = carregar_brand()
    linha = carregar_linha_calendario(args.dia)
    ancora = date.fromisoformat(args.data_ancora)
    data_post = data_real_do_dia(args.dia, ancora, args.dia_ancora)

    copy = gerar_copy(brand, linha)

    (ROOT / "queue").mkdir(exist_ok=True)
    out_path = ROOT / "queue" / f"{data_post.isoformat()}.json"
    payload = {
        "dia_calendario": args.dia,
        "data_publicacao": data_post.isoformat(),
        "status": "rascunho",
        **copy,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rascunho salvo em {out_path}")

if __name__ == "__main__":
    main()
