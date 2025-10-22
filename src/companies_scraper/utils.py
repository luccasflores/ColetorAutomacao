import re
import unicodedata
import random
import asyncio
from pathlib import Path

def slugify_pt(s: str) -> str:
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^a-zA-Z0-9\s-]', '', s).strip().lower()
    return re.sub(r'[\s_-]+', '-', s)

def build_url(entrada: str) -> tuple[str, str]:
    """
    Entrada esperada: "6920-6/01 - Atividades de contabilidade"
    Retorna: (url, nome_arquivo.xlsx)
    """
    codigo, descricao = [p.strip() for p in entrada.split(" - ", 1)]
    codigo_limpo = codigo.replace("-", "").replace("/", "")
    descricao_url = slugify_pt(descricao)
    url = f"https://empresasweb.net/empresas/{descricao_url}-{codigo_limpo}"

    nome_base = unicodedata.normalize('NFKD', descricao).encode('ascii', 'ignore').decode('ascii')
    nome_base = re.sub(r'[^a-zA-Z0-9]+', '_', nome_base).strip('_')
    arquivo = f"{nome_base}.xlsx"
    return url, arquivo

async def jitter_delay(ms_min: int, ms_max: int):
    await asyncio.sleep(random.uniform(ms_min/1000, ms_max/1000))

def ensure_dir(p: str | Path):
    Path(p).mkdir(parents=True, exist_ok=True)
