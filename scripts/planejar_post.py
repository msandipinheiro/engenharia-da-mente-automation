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
from dotenv import load_dotenv
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

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

SYSTEM_PROMPT_TEMPLATE = """Você é o redator da marca "Engenharia da Mente" (@engenhariadamente.oficial),
responsável pela copy do produto Mente Sob Medida.

REGRAS DE TOM DE VOZ (nunca quebre):
{tom_de_voz}

DISCLAIMERS OBRIGATÓRIOS quando o conteúdo mencionar o autoteste:
{disclaimers}

PÚBLICO:
{publico}

Responda SOMENTE com um JSON válido (sem markdown, sem texto fora do JSON), no formato:
{{
  "legenda": "<legenda para a publicação, pronta para postar>",
  "cta": "<call to action final>",
  "hashtags_sugeridas": ["#tag1", "#tag2", "..."],
  "roteiro_reel": ["<texto na tela, corte 1>", "<corte 2>", "..."] ou null se o formato não incluir Reel,
  "slides_carrossel": ["<texto do slide 1 - capa>", "<slide 2>", "..."] ou null se o formato não incluir Carrossel,
  "alerta_se_fora_do_tom": "<qualquer risco de tom que você identificou, ou null>"
}}
"""

def gerar_copy(brand: dict, linha_calendario: dict) -> dict:
    """Chama a API da Claude para gerar a copy do dia, respeitando brand.yaml.

    Requer ANTHROPIC_API_KEY no ambiente (.env). Se a chamada falhar (sem
    chave, sem rede, erro da API), levanta a exceção — de propósito: é
    melhor o pipeline parar do que publicar um post sem copy real.
    """
    import anthropic

    client = anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        tom_de_voz="\n".join(f"- {t}" for t in brand["tom_de_voz"]),
        disclaimers="\n".join(f"- {k}: {v}" for k, v in brand.get("disclaimers_obrigatorios", {}).items()),
        publico="\n".join(f"- {p}" for p in brand["publico"]),
    )
    user_prompt = (
        f"Dia {linha_calendario.get('Dia')} do calendário editorial.\n"
        f"Fase: {linha_calendario['Fase']}\n"
        f"Formato: {linha_calendario['Formato']}\n"
        f"Conteúdo planejado: {linha_calendario['Conteúdo']}\n"
        f"CTA sugerido no calendário: {linha_calendario['CTA']}\n\n"
        f"Gere a copy completa para este post, seguindo o JSON pedido no system prompt."
    )

    resp = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text_blocks = [block.text for block in resp.content if getattr(block, "type", None) == "text"]
    if not text_blocks:
        raise RuntimeError("A resposta da Anthropic não contém um bloco de texto para converter em JSON.")
    raw = "\n".join(text_blocks).strip()
    dados = json.loads(raw)
    dados["formato"] = linha_calendario["Formato"]
    dados["fase"] = linha_calendario["Fase"]
    return dados

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
