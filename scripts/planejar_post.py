#!/usr/bin/env python3
"""
Lê o calendário editorial e gera o rascunho de copy do dia via Claude API.

Uso (comportamento original, intacto — Engenharia da Mente):
    python scripts/planejar_post.py --dia 14

Uso multi-marca (novo, opcional):
    python scripts/planejar_post.py --marca divino-inconsciente --dia 3 --data-ancora 2026-10-01
    (--data-ancora é a data do Dia 1 do calendário da marca, salvo --dia-ancora)
"""
import argparse
import csv
import json
import yaml
from dotenv import load_dotenv
from datetime import date, timedelta
from pathlib import Path

from fila_utils import adicionar_arg_marca, carregar_brand, normalizar_marca, queue_dir

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def carregar_linha_calendario(dia: int, marca: str | None = None):
    """Sem --marca: comportamento original (lê config/calendar_source.yaml,
    aponta pra content/calendario-editorial.csv). Com --marca: convenção
    fixa content/<marca>/calendario-editorial.csv, mesmas colunas."""
    if marca:
        caminho_csv = ROOT / "content" / marca / "calendario-editorial.csv"
        colunas = {"dia": "Dia", "fase": "Fase", "formato": "Formato", "conteudo": "Conteúdo", "cta": "CTA"}
    else:
        cfg = yaml.safe_load((ROOT / "config" / "calendar_source.yaml").read_text(encoding="utf-8"))
        caminho_csv = ROOT / cfg["path"]
        colunas = cfg["columns"]

    with open(caminho_csv, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if int(row[colunas["dia"]]) == dia:
                return row
    raise ValueError(f"Dia {dia} não encontrado no calendário"
                      + (f" de {marca}" if marca else ""))


def data_real_do_dia(dia: int, data_ancora: date, dia_ancora: int) -> date:
    """Converte 'Dia N' do calendário para uma data real, dado um ponto de ancoragem
    (ex.: dia 17 = data da última chamada). Ajuste os valores default no __main__.
    """
    return data_ancora + timedelta(days=dia - dia_ancora)


SYSTEM_PROMPT_TEMPLATE = """Você é o redator da marca "{nome_marca}" ({handle}){produto}.

REGRAS DE TOM DE VOZ (nunca quebre):
{tom_de_voz}

DISCLAIMERS OBRIGATÓRIOS (a chave diz quando se aplica; "geral" vale para todo post):
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
    """Chama a API da Claude para gerar a copy do dia, respeitando o brand.yaml
    (ou config/marcas/<marca>.yaml) carregado.

    Requer ANTHROPIC_API_KEY no ambiente (.env). Se a chamada falhar (sem
    chave, sem rede, erro da API), levanta a exceção — de propósito: é
    melhor o pipeline parar do que publicar um post sem copy real.
    """
    import anthropic

    client = anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente
    nome_marca = brand.get("nome", brand.get("handle", "a marca"))
    produto = f",\nresponsável pela copy do produto {brand['produto']}" if brand.get("produto") else ""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        nome_marca=nome_marca,
        handle=brand.get("handle", ""),
        produto=produto,
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
    if raw.startswith("```"):
        # o modelo às vezes embrulha o JSON em ```json ... ``` mesmo instruído a não fazer
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    dados = json.loads(raw)
    dados["formato"] = linha_calendario["Formato"]
    dados["fase"] = linha_calendario["Fase"]
    return dados


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dia", type=int, required=True, help="Número do dia no calendário")
    parser.add_argument("--data-ancora", type=str, default=None,
                        help="Data real de um dia-âncora (AAAA-MM-DD). Padrão da Engenharia da Mente: 2026-09-21. "
                             "Obrigatório com --marca.")
    parser.add_argument("--dia-ancora", type=int, default=None,
                        help="Número do dia do calendário que corresponde à data-ancora "
                             "(padrão: 17 na Engenharia da Mente, 1 nas outras marcas)")
    adicionar_arg_marca(parser)
    args = parser.parse_args()

    marca = normalizar_marca(ROOT, args.marca)
    if args.data_ancora is None:
        if marca:
            # os padrões abaixo são do lançamento da Engenharia da Mente; para outra
            # marca gerariam datas erradas sem aviso
            parser.error("--data-ancora é obrigatório com --marca (ex.: --data-ancora 2026-10-01).")
        args.data_ancora, args.dia_ancora = "2026-09-21", args.dia_ancora or 17
    if args.dia_ancora is None:
        args.dia_ancora = 1 if marca else 17
    brand = carregar_brand(ROOT, marca)
    linha = carregar_linha_calendario(args.dia, marca)
    ancora = date.fromisoformat(args.data_ancora)
    data_post = data_real_do_dia(args.dia, ancora, args.dia_ancora)

    copy = gerar_copy(brand, linha)

    queue = queue_dir(ROOT, marca)
    queue.mkdir(parents=True, exist_ok=True)
    out_path = queue / f"{data_post.isoformat()}.json"
    payload = {
        "dia_calendario": args.dia,
        "data_publicacao": data_post.isoformat(),
        "status": "rascunho",
        **copy,
    }
    if marca:
        payload["marca"] = marca
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rascunho salvo em {out_path}")


if __name__ == "__main__":
    main()
