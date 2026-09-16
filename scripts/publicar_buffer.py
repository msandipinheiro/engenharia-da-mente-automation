#!/usr/bin/env python3
"""
Rota A — publica/agenda via API atual do Buffer (https://buffer.com).
A API atual usa GraphQL em https://api.buffer.com e exige uma API key em
BUFFER_API_KEY. O script aceita também o nome antigo BUFFER_ACCESS_TOKEN
como fallback temporário para compatibilidade.

Uso: python scripts/publicar_buffer.py --data 2026-09-20
"""
import argparse
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
BUFFER_API_KEY = os.getenv("BUFFER_API_KEY") or os.getenv("BUFFER_ACCESS_TOKEN")
BUFFER_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID")
PUBLIC_MEDIA_BASE_URL = os.getenv("PUBLIC_MEDIA_BASE_URL", "").strip().rstrip("/")


def resolve_media_url(payload: dict) -> str:
    if payload.get("midia_url"):
        return payload["midia_url"]

    media_value = payload.get("midia")
    if not media_value:
        raise SystemExit("No media file was found in the queue payload. Add 'midia' or 'midia_url'.")

    media_text = str(media_value)
    if media_text.startswith(("http://", "https://")):
        payload["midia_url"] = media_text
        return media_text

    if not PUBLIC_MEDIA_BASE_URL:
        raise SystemExit(
            "PUBLIC_MEDIA_BASE_URL missing. Configure the public base URL where files are served, for example: https://cdn.example.com/media"
        )

    filename = Path(media_text).name
    media_url = f"{PUBLIC_MEDIA_BASE_URL}/{filename}"
    payload["midia_url"] = media_url
    return media_url


def buffer_graphql(query: str, variables: dict | None = None) -> dict:
    if not BUFFER_API_KEY:
        raise SystemExit("BUFFER_API_KEY missing. Configure a key from Settings → API in Buffer before running this script.")

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    resp = requests.post(
        "https://api.buffer.com/graphql",
        headers={
            "Authorization": f"Bearer {BUFFER_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if "errors" in body:
        raise RuntimeError(f"Buffer GraphQL error: {body['errors']}")
    return body["data"]


def listar_organizacoes() -> dict:
    query = """
    query GetOrganizations {
      account {
        organizations {
          id
          name
        }
      }
    }
    """
    return buffer_graphql(query)


def listar_canais(organization_id: str) -> dict:
    query = """
    query GetChannels($organizationId: OrganizationId!) {
      channels(input: { organizationId: $organizationId }) {
        id
        name
        service
      }
    }
    """
    return buffer_graphql(query, {"organizationId": organization_id})


def publicar(payload: dict) -> dict:
    """
    A API atual do Buffer exige um canal/Channel ID e, para imagens, uma URL pública
    acessível via internet. Por isso, o script não tenta publicar uma imagem local
    diretamente como na API antiga; ele exige que o canal seja selecionado no ambiente.
    """
    if not BUFFER_CHANNEL_ID:
        raise SystemExit(
            "BUFFER_CHANNEL_ID missing. Use a consulta GraphQL para listar canais e configure o canal correto antes de publicar."
        )

    media_url = resolve_media_url(payload)
    if not media_url or not str(media_url).startswith(("http://", "https://")):
        raise SystemExit(
            "Buffer current API requires a public URL for image assets. Set 'midia_url' or configure 'PUBLIC_MEDIA_BASE_URL'."
        )

    query = """
    mutation CreatePost($channelId: ChannelId!, $text: String!, $mediaUrl: String!) {
      createPost(input: {
        channelId: $channelId
        text: $text
        assets: [{ image: { url: $mediaUrl } }]
        schedulingType: automatic
        mode: addToQueue
      }) {
        ... on PostActionSuccess {
          post {
            id
            text
            dueAt
          }
        }
        ... on MutationError {
          message
        }
      }
    }
    """
    variables = {
        "channelId": BUFFER_CHANNEL_ID,
        "text": f"{payload.get('legenda', '')}\n\n{payload.get('cta', '')}".strip(),
        "mediaUrl": media_url,
    }
    result = buffer_graphql(query, variables)
    if "createPost" not in result:
        raise RuntimeError(f"Resposta inesperada da API do Buffer: {result}")
    return result["createPost"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    args = parser.parse_args()

    post_path = ROOT / "queue" / f"{args.data}.json"
    print(post_path, "\n")
    payload = json.loads(post_path.read_text(encoding="utf-8"))
    if payload.get("status") != "aprovado":
        raise SystemExit("Post não está aprovado. Use fila_aprovacao.py --aprovar primeiro.")

    resultado = publicar(payload)
    payload["status"] = "publicado"
    payload["resultado_api"] = resultado
    post_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Publicado via Buffer:", resultado)


if __name__ == "__main__":
    main()
