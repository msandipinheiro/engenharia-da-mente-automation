#!/usr/bin/env python3
"""Agenda posts aprovados no Buffer usando a API GraphQL atual."""
import argparse
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
BUFFER_API_KEY = os.getenv("BUFFER_API_KEY") or os.getenv("BUFFER_ACCESS_TOKEN")
BUFFER_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID")
PUBLIC_MEDIA_BASE_URL = os.getenv("PUBLIC_MEDIA_BASE_URL", "").strip().rstrip("/")

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


def media_urls(payload: dict) -> list[str]:
    values = payload.get("midia_url") or payload.get("midia") or []
    if isinstance(values, str):
        values = [values]
    urls = []
    for value in values:
        text = str(value)
        if text.lower().endswith((".txt", ".json")):
            continue
        if text.startswith(("http://", "https://")):
            urls.append(text)
        else:
            if not PUBLIC_MEDIA_BASE_URL:
                raise SystemExit("PUBLIC_MEDIA_BASE_URL ausente no .env.")
            urls.append(f"{PUBLIC_MEDIA_BASE_URL}/{text.replace(chr(92), '/').lstrip('/')}")
    if not urls:
        raise SystemExit("Nenhuma imagem foi encontrada no campo 'midia'.")
    for url in urls:
        check = requests.head(url, allow_redirects=True, timeout=30)
        if check.status_code >= 400:
            raise SystemExit(f"Public media URL is not reachable ({check.status_code}): {url}")
    return urls


def publicar(payload: dict) -> dict:
    if not BUFFER_CHANNEL_ID:
        raise SystemExit("BUFFER_CHANNEL_ID ausente no .env.")
    urls = media_urls(payload)
    channel = info_do_canal(BUFFER_CHANNEL_ID)
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
        "channelId": BUFFER_CHANNEL_ID,
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
    args = parser.parse_args()

    post_path = ROOT / "queue" / f"{args.data}.json"
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
