#!/usr/bin/env python3
"""
Gera a mídia de um post da fila, seguindo o padrão visual da marca (brand.yaml).

- Formato com "Carrossel": gera 1 imagem PNG por slide (slides_carrossel).
- Formato com "Reel": NÃO gera vídeo (fora do alcance deste script) — em vez
  disso, gera um prompt estruturado para colar numa ferramenta de IA de
  vídeo (Runway, Pika, Sora, InVideo, etc), salvo como .txt ao lado do post.

Uso: python scripts/gerar_midia.py --data 2026-09-01
"""
import argparse
import json
import textwrap
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent


def carregar_brand():
    return yaml.safe_load((ROOT / "config" / "brand.yaml").read_text(encoding="utf-8"))


def fonte(size, bold=False):
    # Fallback robusto: tenta DejaVu (quase sempre presente em Linux); se não
    # achar, usa a fonte default do PIL (sem negrito/tamanho customizado).
    candidatos = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for c in candidatos:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def gerar_slide(texto: str, destino: Path, brand: dict, numero: int, total: int, capa: bool):
    W = H = 1080
    teal = brand["paleta"]["teal_principal"]
    teal_dark = brand["paleta"]["teal_escuro"]
    teal_light = brand["paleta"]["teal_claro"]

    img = Image.new("RGB", (W, H), color=teal_light if not capa else teal)
    draw = ImageDraw.Draw(img)

    if capa:
        # capa: fundo teal cheio, texto branco, título maior
        f_title = fonte(64, bold=True)
        linhas = textwrap.wrap(texto, width=18)
        total_h = len(linhas) * 78
        y = (H - total_h) // 2
        for linha in linhas:
            bbox = draw.textbbox((0, 0), linha, font=f_title)
            w = bbox[2] - bbox[0]
            draw.text(((W - w) / 2, y), linha, font=f_title, fill="white")
            y += 78
    else:
        # slide de conteúdo: fundo claro, número no topo, texto centralizado
        f_num = fonte(34, bold=True)
        f_body = fonte(46, bold=True)
        draw.ellipse((60, 60, 140, 140), fill=teal)
        num_txt = str(numero)
        bbox = draw.textbbox((0, 0), num_txt, font=f_num)
        draw.text((100 - (bbox[2] - bbox[0]) / 2, 100 - (bbox[3] - bbox[1]) / 2 - bbox[1]),
                   num_txt, font=f_num, fill="white")

        linhas = textwrap.wrap(texto, width=24)
        total_h = len(linhas) * 62
        y = (H - total_h) // 2
        for linha in linhas:
            bbox = draw.textbbox((0, 0), linha, font=f_body)
            w = bbox[2] - bbox[0]
            draw.text(((W - w) / 2, y), linha, font=f_body, fill=teal_dark)
            y += 62

        # rodapé com progresso (● ● ○ ○ ○)
        pontos = "".join("●" if i < numero else "○" for i in range(1, total))
        f_dots = fonte(28)
        bbox = draw.textbbox((0, 0), pontos, font=f_dots)
        draw.text(((W - (bbox[2] - bbox[0])) / 2, H - 90), pontos, font=f_dots, fill=teal)

    img.save(destino)


def gerar_prompt_video_ia(payload: dict, brand: dict) -> str:
    """Monta um prompt estruturado para ferramentas de texto-para-vídeo por IA."""
    roteiro = payload.get("roteiro_reel") or []
    cortes = "\n".join(f"{i+1}. {c}" for i, c in enumerate(roteiro))
    paleta = brand["paleta"]
    linhas = [
        "PROMPT PARA FERRAMENTA DE VÍDEO POR IA (Reel — @engenhariadamente.oficial)",
        "=" * 74,
        "",
        "Formato: vertical 9:16, 15-30 segundos, estilo Reel/TikTok.",
        f"Estética: minimalista, fundo em tons de teal ({paleta['teal_principal']} / "
        f"{paleta['teal_escuro']}) com texto branco ou {paleta['teal_escuro']} sobre fundo "
        f"{paleta['teal_claro']}, tipografia bold sem serifa, sem elementos decorativos ou "
        "mascotes — tom editorial, não infantilizado.",
        "",
        f"Tom: {'; '.join(brand['tom_de_voz'][:2])}",
        "",
        "Estrutura (um corte de texto por cena, ritmo rápido, ~2-4s por corte):",
        cortes if cortes else "(nenhum roteiro de reel foi gerado para este post)",
        "",
        "Instruções à ferramenta de IA:",
        "- Cada linha acima é uma cena com o texto centralizado na tela.",
        "- Sem voz/narração — é um Reel de texto animado (estilo \"quote reel\").",
        "- Sem rostos, sem imagens de banco de imagem genéricas.",
        "- Última cena deve durar mais (~4-5s) para dar tempo de leitura do CTA.",
        "- Música: instrumental leve, sem letra, volume baixo (não deve competir com a leitura).",
        "",
        "Legenda (para colar junto do vídeo na publicação):",
        payload.get("legenda", ""),
    ]
    return "\n".join(linhas)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Data do post na fila (AAAA-MM-DD)")
    args = parser.parse_args()

    brand = carregar_brand()
    post_path = ROOT / "queue" / f"{args.data}.json"
    payload = json.loads(post_path.read_text(encoding="utf-8"))

    media_dir = ROOT / "queue" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    midias = []
    formato = payload.get("formato", "")

    if "Carrossel" in formato and payload.get("slides_carrossel"):
        slides = payload["slides_carrossel"]
        for i, texto in enumerate(slides, start=1):
            destino = media_dir / f"{args.data}-slide{i}.png"
            gerar_slide(texto, destino, brand, numero=i, total=len(slides), capa=(i == 1))
            midias.append(str(destino.relative_to(ROOT)))
        print(f"{len(slides)} slides de carrossel gerados em {media_dir}")

    if "Reel" in formato:
        prompt_txt = gerar_prompt_video_ia(payload, brand)
        prompt_path = media_dir / f"{args.data}-reel-prompt.txt"
        prompt_path.write_text(prompt_txt, encoding="utf-8")
        midias.append(str(prompt_path.relative_to(ROOT)))
        print(f"Prompt de vídeo IA salvo em {prompt_path} (vídeo em si precisa ser gerado "
              f"numa ferramenta externa de texto-para-vídeo)")

    payload["midia"] = midias
    payload["status"] = "pronto_para_aprovacao"
    post_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Status atualizado para 'pronto_para_aprovacao'.")


if __name__ == "__main__":
    main()
