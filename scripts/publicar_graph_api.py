#!/usr/bin/env python3
"""
Rota B — publica direto via Instagram Graph API (Meta), sem intermediário.

Pré-requisitos (ver README):
  - Conta Instagram Business/Creator vinculada a uma Página do Facebook
  - App registrado no Meta for Developers, com App Review aprovado
  - Mídia acessível por URL pública no momento da publicação
  - Limite: 25 posts publicados via API por período de 24h

Uso (comportamento original — Engenharia da Mente):
    python scripts/publicar_graph_api.py --data 2026-09-20
    (usa META_ACCESS_TOKEN e IG_BUSINESS_ACCOUNT_ID do .env)

Uso multi-marca (novo, opcional):
    python scripts/publicar_graph_api.py --marca divino-inconsciente --data 2026-10-01
    (usa IG_BUSINESS_ACCOUNT_ID_DIVINO_INCONSCIENTE e, se existir,
    META_ACCESS_TOKEN_DIVINO_INCONSCIENTE — senão cai no META_ACCESS_TOKEN)

Uma imagem vira post simples; 2 a 10 imagens viram carrossel.
"""
import argparse
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from fila_utils import (adicionar_arg_marca, avisos_de_conflito, carregar_item, normalizar_marca, queue_dir,
                        salvar_item, sufixo_env, urls_publicas_da_midia)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
GRAPH_URL = "https://graph.facebook.com/v20.0"  # confirme a versão atual antes de usar


def credenciais(marca: str | None) -> tuple[str, str]:
    sufixo = sufixo_env(marca)
    token = os.getenv(f"META_ACCESS_TOKEN{sufixo}") or os.getenv("META_ACCESS_TOKEN")
    # sem fallback para a conta: publicar na conta de outra marca é pior do que falhar
    conta = os.getenv(f"IG_BUSINESS_ACCOUNT_ID{sufixo}")
    if not token:
        raise SystemExit("META_ACCESS_TOKEN ausente no .env.")
    if not conta:
        raise SystemExit(f"IG_BUSINESS_ACCOUNT_ID{sufixo} ausente no .env.")
    return token, conta


def graph_post(caminho: str, dados: dict, token: str) -> dict:
    resposta = requests.post(f"{GRAPH_URL}/{caminho}", data={**dados, "access_token": token}, timeout=30).json()
    if "id" not in resposta:
        raise RuntimeError(f"Graph API recusou {caminho}: {resposta}")
    return resposta


def aguardar_container(container_id: str, token: str, tentativas: int = 20):
    """O container precisa estar FINISHED antes do media_publish."""
    for _ in range(tentativas):
        status = requests.get(f"{GRAPH_URL}/{container_id}",
                              params={"fields": "status_code", "access_token": token}, timeout=30).json()
        codigo = status.get("status_code")
        if codigo == "FINISHED":
            return
        if codigo in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container {container_id} falhou: {status}")
        time.sleep(3)
    raise RuntimeError(f"Container {container_id} não ficou pronto a tempo.")


def publicar(payload: dict, token: str, conta: str) -> dict:
    urls = urls_publicas_da_midia(payload, os.getenv("PUBLIC_MEDIA_BASE_URL", ""))
    if len(urls) > 10:
        raise SystemExit(f"O Instagram aceita no máximo 10 imagens por carrossel ({len(urls)} encontradas).")
    legenda = f"{payload.get('legenda', '')}\n\n{payload.get('cta', '')}".strip()

    # Passo 1 — criar o container de mídia (um filho por imagem, se carrossel)
    if len(urls) == 1:
        container = graph_post(f"{conta}/media", {"image_url": urls[0], "caption": legenda}, token)
    else:
        filhos = [graph_post(f"{conta}/media", {"image_url": url, "is_carousel_item": "true"}, token)["id"]
                  for url in urls]
        for filho in filhos:
            aguardar_container(filho, token)
        container = graph_post(f"{conta}/media",
                               {"media_type": "CAROUSEL", "children": ",".join(filhos), "caption": legenda}, token)

    # Passo 2 — publicar o container quando estiver processado
    aguardar_container(container["id"], token)
    return graph_post(f"{conta}/media_publish", {"creation_id": container["id"]}, token)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    adicionar_arg_marca(parser)
    args = parser.parse_args()

    marca = normalizar_marca(ROOT, args.marca)
    queue = queue_dir(ROOT, marca)
    post_path, payload = carregar_item(args.data, queue)
    if payload.get("status") != "aprovado":
        raise SystemExit("Post não está aprovado. Use fila_aprovacao.py --aprovar primeiro.")

    token, conta = credenciais(marca)

    for aviso in avisos_de_conflito(post_path, payload, queue):
        print(aviso)

    resultado = publicar(payload, token, conta)
    payload["status"] = "publicado"
    payload["resultado_api"] = resultado
    salvar_item(post_path, payload)
    print("Publicado via Graph API:", resultado)


if __name__ == "__main__":
    main()
