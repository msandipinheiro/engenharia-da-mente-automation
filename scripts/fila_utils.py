"""Operacoes compartilhadas para localizar e validar itens da fila."""
import json
import re
from datetime import date
from pathlib import Path

import yaml


def eh_avulso(payload: dict) -> bool:
    return payload.get("tipo") == "avulso" or payload.get("dia_calendario") is None


def data_do_nome(path: Path) -> str | None:
    match = re.search(r"\d{4}-\d{2}-\d{2}$", path.stem)
    if not match:
        return None
    try:
        date.fromisoformat(match.group())
    except ValueError:
        return None
    return match.group()


def sincronizar_data_do_nome(path: Path, payload: dict) -> dict:
    """Mantem a data do JSON alinhada ao sufixo de data do arquivo avulso."""
    if eh_avulso(payload):
        data = data_do_nome(path)
        if data and payload.get("data_publicacao") != data:
            payload["data_publicacao"] = data
    return payload


def carregar_item(identifier: str, queue: Path) -> tuple[Path, dict]:
    direct = queue / f"{identifier}.json"
    candidates = [direct] if direct.exists() else sorted(queue.glob("*.json"))
    for path in candidates:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if path == direct or payload.get("id") == identifier or payload.get("identificador") == identifier:
            return path, sincronizar_data_do_nome(path, payload)
    raise SystemExit(f"Item '{identifier}' não encontrado na fila.")


def salvar_item(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def avisos_de_conflito(path: Path, payload: dict, queue: Path) -> list[str]:
    data = payload.get("data_publicacao")
    if not data:
        return []
    conflitos = []
    for other in sorted(queue.glob("*.json")):
        if other == path:
            continue
        other_payload = json.loads(other.read_text(encoding="utf-8"))
        if other_payload.get("data_publicacao") == data:
            conflitos.append(other.stem)
    if not conflitos:
        return []
    return [
        f"Aviso: {path.stem} compartilha a data {data} com {', '.join(conflitos)}. "
        "Os dois itens serão mantidos."
    ]


# --- multi-marca ---------------------------------------------------------
# Sem --marca (ou com --marca engenharia-da-mente) tudo se comporta como antes:
# config/brand.yaml, content/calendario-editorial.csv, queue/ e BUFFER_CHANNEL_ID.
# Outras marcas: config/marcas/<marca>.yaml, content/<marca>/, queue/<marca>/ e
# BUFFER_CHANNEL_ID_<MARCA>.
MARCA_PADRAO = "engenharia-da-mente"


def marcas_disponiveis(root: Path) -> list[str]:
    return [MARCA_PADRAO] + sorted(p.stem for p in (root / "config" / "marcas").glob("*.yaml"))


def normalizar_marca(root: Path, marca: str | None) -> str | None:
    """Devolve None para a marca padrão; valida as demais contra config/marcas/."""
    if not marca or marca == MARCA_PADRAO:
        return None
    if not (root / "config" / "marcas" / f"{marca}.yaml").exists():
        raise SystemExit(f"Marca '{marca}' não encontrada. Disponíveis: {', '.join(marcas_disponiveis(root))}")
    return marca


def carregar_brand(root: Path, marca: str | None = None) -> dict:
    marca = normalizar_marca(root, marca)
    path = (root / "config" / "marcas" / f"{marca}.yaml") if marca else (root / "config" / "brand.yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def queue_dir(root: Path, marca: str | None = None) -> Path:
    marca = normalizar_marca(root, marca)
    return (root / "queue" / marca) if marca else (root / "queue")


def sufixo_env(marca: str | None) -> str:
    """'' para a marca padrão; '_DIVINO_INCONSCIENTE' para divino-inconsciente."""
    return f"_{marca.upper().replace('-', '_')}" if marca else ""


def adicionar_arg_marca(parser) -> None:
    parser.add_argument("--marca", type=str, default=None,
                        help=f"Slug da marca (ex.: divino-inconsciente, viver-em-fluxo). "
                             f"Omitido = {MARCA_PADRAO}.")


def urls_publicas_da_midia(payload: dict, base_url: str) -> list[str]:
    """Converte o campo 'midia' (caminhos relativos à raiz do repo) em URLs
    públicas, ignorando .txt/.json (ex.: prompt de Reel), e confere se cada
    URL responde antes de entregar para a API de publicação."""
    import requests

    values = payload.get("midia_url") or payload.get("midia") or []
    if isinstance(values, str):
        values = [values]
    base_url = base_url.strip().rstrip("/")
    urls = []
    for value in values:
        text = str(value)
        if text.lower().endswith((".txt", ".json")):
            continue
        if text.startswith(("http://", "https://")):
            urls.append(text)
        else:
            if not base_url:
                raise SystemExit("PUBLIC_MEDIA_BASE_URL ausente no .env.")
            urls.append(f"{base_url}/{text.replace(chr(92), '/').lstrip('/')}")
    if not urls:
        raise SystemExit("Nenhuma imagem foi encontrada no campo 'midia'.")
    for url in urls:
        check = requests.head(url, allow_redirects=True, timeout=30)
        if check.status_code >= 400:
            raise SystemExit(f"Public media URL is not reachable ({check.status_code}): {url}")
    return urls
