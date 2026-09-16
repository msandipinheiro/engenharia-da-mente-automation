#!/usr/bin/env python3
"""
Rota B — publica direto via Instagram Graph API (Meta), sem intermediário.

Pré-requisitos (ver README):
  - Conta Instagram Business/Creator vinculada a uma Página do Facebook
  - App registrado no Meta for Developers, com App Review aprovado
  - Mídia acessível por URL pública no momento da publicação
  - Limite: 25 posts publicados via API por período de 24h

Uso: python scripts/publicar_graph_api.py --data 2026-09-20
"""
import argparse
import json
import os
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]
IG_ACCOUNT_ID = os.environ["IG_BUSINESS_ACCOUNT_ID"]
PUBLIC_BASE_URL = os.environ["PUBLIC_MEDIA_BASE_URL"]
GRAPH_URL = "https://graph.facebook.com/v20.0"  # confirme a versão atual antes de usar

def publicar(payload: dict) -> dict:
    media_url = f"{PUBLIC_BASE_URL.rstrip('/')}/{Path(payload['midia']).name}"

    # Passo 1 — criar o container de mídia
    container = requests.post(
        f"{GRAPH_URL}/{IG_ACCOUNT_ID}/media",
        data={
            "image_url": media_url,
            "caption": f"{payload['legenda']}\n\n{payload['cta']}",
            "access_token": ACCESS_TOKEN,
        },
        timeout=30,
    ).json()
    if "id" not in container:
        raise RuntimeError(f"Falha ao criar container: {container}")
    creation_id = container["id"]

    # Passo 2 — publicar o container (com pequena espera para processamento)
    time.sleep(3)
    publicacao = requests.post(
        f"{GRAPH_URL}/{IG_ACCOUNT_ID}/media_publish",
        data={"creation_id": creation_id, "access_token": ACCESS_TOKEN},
        timeout=30,
    ).json()
    if "id" not in publicacao:
        raise RuntimeError(f"Falha ao publicar container: {publicacao}")
    return publicacao

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    args = parser.parse_args()

    post_path = ROOT / "queue" / f"{args.data}.json"
    payload = json.loads(post_path.read_text(encoding="utf-8"))
    if payload.get("status") != "aprovado":
        raise SystemExit("Post não está aprovado. Use fila_aprovacao.py --aprovar primeiro.")

    resultado = publicar(payload)
    payload["status"] = "publicado"
    payload["resultado_api"] = resultado
    post_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Publicado via Graph API:", resultado)

if __name__ == "__main__":
    main()
