#!/usr/bin/env python3
"""
Verifica (não altera) o estado do produto Mente Sob Medida na Hotmart via
API oficial de Produtos — que é somente leitura (GET /products e
GET /products/:ucode/offers, confirmado na documentação oficial: não existe
endpoint de escrita para preço nessa API).

Serve para conferir, sem precisar abrir o painel:
  - se o preço da oferta principal está no valor esperado para a fase atual
    (R$47 até 21/09 23h59, R$97 depois — troca ainda é manual)
  - se a garantia (warranty_period) está em pelo menos 7 dias, conforme
    exigido pelo CDC / política da própria Hotmart
  - o status do produto (DRAFT, ACTIVE, IN_REVIEW etc.)

Uso:
    python scripts/verificar_produto_hotmart.py --produto-id 698441
"""
import argparse
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE_URL = "https://developers.hotmart.com/products/api/v1"
ACCESS_TOKEN = os.getenv("HOTMART_ACCESS_TOKEN")

# Janela de preço combinada (ver Memento de cadastro na Hotmart)
FIM_LANCAMENTO = datetime(2026, 9, 21, 23, 59, tzinfo=ZoneInfo("America/Sao_Paulo"))
PRECO_LANCAMENTO = 47.0
PRECO_PADRAO = 97.0


def headers() -> dict:
    if not ACCESS_TOKEN:
        raise SystemExit("Defina HOTMART_ACCESS_TOKEN no .env (obtido no painel de "
                          "Developers da Hotmart, na sua conta).")
    return {"Content-Type": "application/json", "Authorization": f"Bearer {ACCESS_TOKEN}"}


def buscar_produto(produto_id: int) -> dict:
    resp = requests.get(f"{BASE_URL}/products", headers=headers(),
                         params={"id": produto_id}, timeout=30)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        raise SystemExit(f"Produto {produto_id} não encontrado nessa conta.")
    return items[0]


def buscar_oferta_principal(ucode: str) -> dict:
    resp = requests.get(f"{BASE_URL}/products/{ucode}/offers", headers=headers(), timeout=30)
    resp.raise_for_status()
    for oferta in resp.json().get("items", []):
        if oferta.get("is_main_offer"):
            return oferta
    raise SystemExit("Nenhuma oferta marcada como principal foi encontrada.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--produto-id", type=int, required=True)
    args = parser.parse_args()

    produto = buscar_produto(args.produto_id)
    oferta = buscar_oferta_principal(produto["ucode"])

    print(f"Produto: {produto['name']}  (status: {produto['status']}, formato: {produto['format']})")
    print(f"Garantia cadastrada: {produto.get('warranty_period')} dias")
    if (produto.get("warranty_period") or 0) < 7:
        print("⚠️  ALERTA: garantia abaixo de 7 dias — está em desacordo com o CDC / política da Hotmart.")

    preco_atual = oferta["price"]["value"]
    moeda = oferta["price"]["currency_code"]
    print(f"Preço da oferta principal: {preco_atual} {moeda}")

    agora = datetime.now(tz=ZoneInfo("America/Sao_Paulo"))
    esperado = PRECO_LANCAMENTO if agora <= FIM_LANCAMENTO else PRECO_PADRAO
    if preco_atual != esperado:
        fase = "lançamento" if agora <= FIM_LANCAMENTO else "pós-lançamento"
        print(f"⚠️  ALERTA: preço esperado para a fase de {fase} é {esperado} {moeda}, "
              f"mas está cadastrado {preco_atual} {moeda}. Troca é manual — confira o painel.")
    else:
        print("Preço está de acordo com a fase atual.")


if __name__ == "__main__":
    main()
