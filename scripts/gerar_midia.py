#!/usr/bin/env python3
"""
Gera a mídia de um post da fila, seguindo o padrão visual da marca
(config/brand.yaml ou config/marcas/<marca>.yaml).

- Formato com "Carrossel": gera 1 imagem PNG por slide (slides_carrossel).
- Formato com "Reel": NÃO gera vídeo (fora do alcance deste script) — em vez
  disso, gera um prompt estruturado para colar numa ferramenta de IA de
  vídeo (Runway, Pika, Sora, InVideo, etc), salvo como .txt ao lado do post.

Uso (comportamento original — Engenharia da Mente):
    python scripts/gerar_midia.py --data 2026-09-01

Uso multi-marca (novo, opcional):
    python scripts/gerar_midia.py --marca divino-inconsciente --data 2026-09-05
"""
import argparse
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from fila_utils import adicionar_arg_marca, carregar_brand, carregar_item, normalizar_marca, queue_dir, salvar_item

ROOT = Path(__file__).resolve().parent.parent

# usados quando a marca (ou config/brand.yaml) não define icone_marca/handle —
# preserva o comportamento original da Engenharia da Mente por padrão
LOGO_PATH_DEFAULT = ROOT / "config" / "icone_marca.png"
HANDLE_DEFAULT = "@engenhariadamente.oficial"


def fonte(size, peso="bold"):
    caminhos = {
        "bold": "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
        "medium": "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf",
        "regular": "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf",
    }
    caminho = caminhos.get(peso, caminhos["bold"])
    if Path(caminho).exists():
        return ImageFont.truetype(caminho, size)
    # fallback se o ambiente não tiver a Poppins instalada (ex.: sua máquina local,
    # se não tiver os Google Fonts em /usr/share/fonts) — cai pra DejaVu, depois pro
    # default do PIL. Se cair aqui, instale a família "Poppins" (Google Fonts) pra
    # ter o visual pretendido.
    fallback_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    fallback_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    fallback = fallback_bold if peso == "bold" else fallback_regular
    return ImageFont.truetype(fallback, size) if Path(fallback).exists() else ImageFont.load_default()


def resolver_logo_e_handle(brand: dict):
    """Le icone_marca/handle da config da marca; cai no default (Engenharia da
    Mente) se a marca não definir esses campos — preserva comportamento antigo."""
    icone = brand.get("icone_marca")
    logo_path = (ROOT / icone) if icone else LOGO_PATH_DEFAULT
    handle = brand.get("handle", HANDLE_DEFAULT)
    return logo_path, handle


def colar_logo(img: Image.Image, cor_fundo_clara: bool, logo_path: Path, handle: str,
               cor_texto: str, tamanho=56):
    """Cola o ícone da marca + handle no rodapé. cor_fundo_clara define se
    usamos o ícone original (fundo claro) ou branco (fundo escuro, na capa)."""
    if not logo_path.exists():
        return
    logo = Image.open(logo_path).convert("RGBA").resize((tamanho, tamanho))
    if not cor_fundo_clara:
        # inverte pra branco quando o fundo é escuro (capa)
        r, g, b, a = logo.split()
        branco = Image.new("RGBA", logo.size, (255, 255, 255, 0))
        branco.putalpha(a)
        logo = branco
    W, H = img.size
    x_logo = 60
    y_logo = H - 78
    img.paste(logo, (x_logo, y_logo), logo)
    draw = ImageDraw.Draw(img)
    f_handle = fonte(26, "medium")
    cor_txt = cor_texto if cor_fundo_clara else "white"
    draw.text((x_logo + tamanho + 16, y_logo + tamanho / 2), handle, font=f_handle,
               fill=cor_txt, anchor="lm")


def cores_da_marca(brand: dict) -> dict:
    """Papéis de cor dos slides, definidos em `cores_slide` no yaml da marca:
    capa (fundo da capa, número e progresso), fundo (slides internos), texto
    (texto interno e @handle) e destaque (etiqueta na capa)."""
    cores = brand.get("cores_slide")
    if not cores:
        raise SystemExit("A marca não define 'cores_slide' (capa, fundo, texto, destaque) no yaml.")
    faltando = {"capa", "fundo", "texto", "destaque"} - set(cores)
    if faltando:
        raise SystemExit(f"'cores_slide' incompleto no yaml da marca; faltam: {', '.join(sorted(faltando))}")
    return cores


def gerar_slide(texto: str, destino: Path, brand: dict, numero: int, total: int, capa: bool,
                logo_path: Path, handle: str):
    W = H = 1080
    cores = cores_da_marca(brand)
    cor_capa, cor_fundo, cor_texto = cores["capa"], cores["fundo"], cores["texto"]

    img = Image.new("RGB", (W, H), color=cor_fundo if not capa else cor_capa)
    draw = ImageDraw.Draw(img)

    if capa:
        f_title = fonte(66, "bold")
        linhas = textwrap.wrap(texto, width=16)
        total_h = len(linhas) * 82
        y = (H - total_h) / 2 - 40
        for linha in linhas:
            bbox = draw.textbbox((0, 0), linha, font=f_title)
            w = bbox[2] - bbox[0]
            draw.text(((W - w) / 2, y), linha, font=f_title, fill="white")
            y += 82
        f_tag = fonte(24, "medium")
        tag = "CARROSSEL"
        bbox = draw.textbbox((0, 0), tag, font=f_tag)
        draw.text(((W - (bbox[2] - bbox[0])) / 2, (H - total_h) / 2 - 100), tag, font=f_tag,
                   fill=cores["destaque"])
        colar_logo(img, cor_fundo_clara=False, logo_path=logo_path, handle=handle, cor_texto=cor_texto)
    else:
        # número alterna de canto conforme a paridade do slide — dá ritmo visual
        lado_esquerdo = (numero % 2 == 1)
        cx = 100 if lado_esquerdo else W - 100
        f_num = fonte(36, "bold")
        draw.ellipse((cx - 42, 58, cx + 42, 142), fill=cor_capa)
        num_txt = str(numero)
        bbox = draw.textbbox((0, 0), num_txt, font=f_num)
        draw.text((cx - (bbox[2] - bbox[0]) / 2, 100 - (bbox[3] - bbox[1]) / 2 - bbox[1]),
                   num_txt, font=f_num, fill="white")

        f_body = fonte(46, "bold")
        linhas = textwrap.wrap(texto, width=24)
        total_h = len(linhas) * 62
        y = (H - total_h) / 2
        for linha in linhas:
            bbox = draw.textbbox((0, 0), linha, font=f_body)
            w = bbox[2] - bbox[0]
            draw.text(((W - w) / 2, y), linha, font=f_body, fill=cor_texto)
            y += 62

        pontos_y = H - 150
        raio_pt, espaco = 9, 28
        largura_total = (total - 1) * espaco
        x0 = (W - largura_total) / 2
        for i in range(1, total):
            cx_pt = x0 + (i - 1) * espaco
            cor_pt = cor_capa if i < numero else cor_fundo
            draw.ellipse((cx_pt - raio_pt, pontos_y - raio_pt, cx_pt + raio_pt, pontos_y + raio_pt),
                         fill=cor_pt, outline=cor_capa, width=2)

        colar_logo(img, cor_fundo_clara=True, logo_path=logo_path, handle=handle, cor_texto=cor_texto)

    img.save(destino)


def gerar_prompt_video_ia(payload: dict, brand: dict, handle: str) -> str:
    """Monta um prompt estruturado para ferramentas de texto-para-vídeo por IA."""
    roteiro = payload.get("roteiro_reel") or []
    cortes = "\n".join(f"{i+1}. {c}" for i, c in enumerate(roteiro))
    cores = cores_da_marca(brand)
    linhas = [
        f"PROMPT PARA FERRAMENTA DE VÍDEO POR IA (Reel — {handle})",
        "=" * 74,
        "",
        "Formato: vertical 9:16, 15-30 segundos, estilo Reel/TikTok.",
        f"Estética: minimalista, fundo {cores['capa']} com texto branco ou texto {cores['texto']} "
        f"sobre fundo {cores['fundo']}, destaques em {cores['destaque']}, tipografia bold sem serifa, sem elementos "
        "decorativos ou mascotes — tom editorial, não infantilizado.",
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
    parser.add_argument("--data", required=True, help="Data ou identificador do post na fila")
    adicionar_arg_marca(parser)
    args = parser.parse_args()

    marca = normalizar_marca(ROOT, args.marca)
    brand = carregar_brand(ROOT, marca)
    logo_path, handle = resolver_logo_e_handle(brand)
    queue = queue_dir(ROOT, marca)
    post_path, payload = carregar_item(args.data, queue)

    media_dir = queue / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    midias = []
    formato = payload.get("formato", "")
    media_prefix = post_path.stem

    if "Carrossel" in formato and payload.get("slides_carrossel"):
        slides = payload["slides_carrossel"]
        for i, texto in enumerate(slides, start=1):
            destino = media_dir / f"{media_prefix}-slide{i}.png"
            gerar_slide(texto, destino, brand, numero=i, total=len(slides), capa=(i == 1),
                        logo_path=logo_path, handle=handle)
            midias.append(str(destino.relative_to(ROOT)))
        print(f"{len(slides)} slides de carrossel gerados em {media_dir}")

    if "Reel" in formato:
        prompt_txt = gerar_prompt_video_ia(payload, brand, handle)
        prompt_path = media_dir / f"{media_prefix}-reel-prompt.txt"
        prompt_path.write_text(prompt_txt, encoding="utf-8")
        midias.append(str(prompt_path.relative_to(ROOT)))
        print(f"Prompt de vídeo IA salvo em {prompt_path} (vídeo em si precisa ser gerado "
              f"numa ferramenta externa de texto-para-vídeo)")

    payload["midia"] = midias
    payload["status"] = "pronto_para_aprovacao"
    salvar_item(post_path, payload)
    print("Status atualizado para 'pronto_para_aprovacao'.")


if __name__ == "__main__":
    main()
