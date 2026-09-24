#!/usr/bin/env python3
"""Agenda posts aprovados no Buffer usando a API GraphQL atual.

Uso (comportamento original — Engenharia da Mente):
    python scripts/publicar_buffer.py --data 2026-09-01
    (usa BUFFER_API_KEY/BUFFER_ACCESS_TOKEN e BUFFER_CHANNEL_ID do .env)

Uso multi-marca (novo, opcional):
    python scripts/publicar_buffer.py --marca divino-inconsciente --data 2026-09-05
    (usa BUFFER_CHANNEL_ID_DIVINO_INCONSCIENTE — ver convenção abaixo)
"""
import argparse
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from fila_utils import (adicionar_arg_marca, avisos_de_conflito, carregar_item, normalizar_marca, queue_dir,
                        salvar_item, sufixo_env, urls_publicas_da_midia)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
BUFFER_API_KEY = os.getenv("BUFFER_API_KEY") or os.getenv("BUFFER_ACCESS_TOKEN")
PUBLIC_MEDIA_BASE_URL = os.getenv("PUBLIC_MEDIA_BASE_URL", "").strip().rstrip("/")


def channel_id_env_var(marca: str | None) -> str:
    """Convenção: BUFFER_CHANNEL_ID (original, sem marca) ou
    BUFFER_CHANNEL_ID_<MARCA_EM_MAIUSCULAS_COM_UNDERSCORE> (multi-marca)."""
    return "BUFFER_CHANNEL_ID" + sufixo_env(marca)


def buffer_graphql(query: str, variables: dict | None = None) -> dict:
    if not BUFFER_API_KEY:
        raise SystemExit("BUFFER_API_KEY ausente no .env.")
    response = requests.post(
        "https://api.buffer.com/graphql",
        headers={"Authorization": f"Bearer {BUFFER_API_KEY}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    if body.get("errors"):
        raise RuntimeError(f"Buffer GraphQL error: {body['errors']}")
    return body["data"]


def info_do_canal(channel_id: str) -> dict:
    query = """
    query GetChannel($channelId: ChannelId!) {
      channel(input: { id: $channelId }) { id service type name }
    }
    """
    return buffer_graphql(query, {"channelId": channel_id}).get("channel") or {}


def publicar(payload: dict, channel_id: str) -> dict:
    urls = urls_publicas_da_midia(payload, PUBLIC_MEDIA_BASE_URL)
    channel = info_do_canal(channel_id)
    is_instagram = str(channel.get("service", "")).lower() == "instagram"
    is_profile = str(channel.get("type", "")).lower() == "profile"
    scheduling_type = "notification" if is_instagram and is_profile else "automatic"
    post_type = "post"
    metadata = {"instagram": {"type": post_type, "shouldShareToFeed": True}} if is_instagram else None
    query = """
    mutation CreatePost($channelId: ChannelId!, $text: String!, $assets: [AssetInput!]!, $schedulingType: SchedulingType!, $metadata: PostInputMetaData) {
      createPost(input: {
        channelId: $channelId
        text: $text
        assets: $assets
        metadata: $metadata
        schedulingType: $schedulingType
        mode: addToQueue
      }) {
        ... on PostActionSuccess { post { id text dueAt } }
        ... on MutationError { message }
      }
    }
    """
    result = buffer_graphql(query, {
        "channelId": channel_id,
        "text": f"{payload.get('legenda', '')}\n\n{payload.get('cta', '')}".strip(),
        "assets": [{"image": {"url": url}} for url in urls],
        "schedulingType": scheduling_type,
        "metadata": metadata,
    })["createPost"]
    if result.get("message"):
        raise RuntimeError(f"Buffer recusou o post: {result['message']}")
    return result


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

    channel_env_var = channel_id_env_var(marca)
    channel_id = os.getenv(channel_env_var)
    if not channel_id:
        raise SystemExit(f"{channel_env_var} ausente no .env.")

    for aviso in avisos_de_conflito(post_path, payload, queue):
        print(aviso)

    resultado = publicar(payload, channel_id)
    payload["status"] = "publicado"
    payload["resultado_api"] = resultado
    salvar_item(post_path, payload)
    print("Publicado via Buffer:", resultado)


if __name__ == "__main__":
    main()
