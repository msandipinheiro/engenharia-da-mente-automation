#!/usr/bin/env python3
"""
Gera a mídia (imagem/carrossel) de um post da fila, no padrão visual da marca.
Uso: python scripts/gerar_midia.py --data 2026-09-20
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def gerar_imagem_placeholder(texto: str, destino: Path):
    """
    TODO: substituir por geração real (matplotlib/PIL) seguindo config/brand.yaml,
    reaproveitando o mesmo padrão usado nos diagramas do material principal
    (paleta teal, tipografia Arial/Calibri).
    """
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1080, 1080), color="#EAF5F4")
    draw = ImageDraw.Draw(img)
    draw.text((60, 500), texto[:80], fill="#134A47")
    img.save(destino)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Data do post na fila (AAAA-MM-DD)")
    args = parser.parse_args()

    post_path = ROOT / "queue" / f"{args.data}.json"
    payload = json.loads(post_path.read_text(encoding="utf-8"))

    media_dir = ROOT / "queue" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    media_path = media_dir / f"{args.data}.png"
    gerar_imagem_placeholder(payload["legenda"], media_path)

    payload["midia"] = str(media_path.relative_to(ROOT))
    payload["status"] = "pronto_para_aprovacao"
    post_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Mídia gerada em {media_path}. Status atualizado para 'pronto_para_aprovacao'.")

if __name__ == "__main__":
    main()
