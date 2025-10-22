import re
from typing import Iterable, List, Dict
from pathlib import Path
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from playwright.async_api import async_playwright, Browser, Page
from .config import SETTINGS
from .utils import jitter_delay, ensure_dir
from . import selectors as S

class ScrapeError(Exception): ...

async def _new_browser():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, channel="chrome")
    return pw, browser

async def _new_page(browser: Browser) -> Page:
    ctx = await browser.new_context(
        user_agent=SETTINGS.user_agent,
        viewport={"width": 1366, "height": 850},
        java_script_enabled=True,
    )
    page = await ctx.new_page()
    page.set_default_timeout(SETTINGS.timeout_ms)
    return page

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(Exception),
)
async def _goto(page: Page, url: str):
    await page.goto(url, wait_until="domcontentloaded")

async def discover_total_pages(url: str) -> tuple[int, int]:
    pw, browser = await _new_browser()
    try:
        page = await _new_page(browser)
        await _goto(page, url)
        await page.wait_for_selector(S.PAGINATION_LINKS, timeout=SETTINGS.timeout_ms)

        # páginas
        links = await page.locator(S.PAGINATION_LINKS).all()
        total_pag = 1
        for l in links:
            href = await l.get_attribute("href")
            if href and href.strip().split("/")[-1].isdigit():
                total_pag = max(total_pag, int(href.strip().split("/")[-1]))

        # total de empresas (pode não existir)
        total_empresas = 0
        try:
            label = await page.locator(S.TOTAL_LABEL).text_content()
            m = re.search(r"de\s+([\d.]+)", label or "")
            total_empresas = int(m.group(1).replace(".", "")) if m else 0
        except:
            pass

        return total_pag, total_empresas
    finally:
        await browser.close()
        await pw.stop()

async def collect_listing_links(base_url: str, page_num: int) -> List[str]:
    pw, browser = await _new_browser()
    try:
        page = await _new_page(browser)
        url = f"{base_url}/{page_num}"
        await _goto(page, url)
        cards = page.locator(S.LISTING_CARD)
        count = await cards.count()
        out: List[str] = []
        for i in range(count):
            card = cards.nth(i)
            a = card.locator(S.LISTING_CARD_LINK)
            if await a.count() > 0:
                href = await a.first.get_attribute("href")
                if href and href.startswith("http"):
                    out.append(href)
        return out
    finally:
        await browser.close()
        await pw.stop()

async def parse_detail(url: str) -> Dict[str, str]:
    pw, browser = await _new_browser()
    try:
        page = await _new_page(browser)
        await _goto(page, url)
        await jitter_delay(SETTINGS.delay_ms_min, SETTINGS.delay_ms_max)

        def maybe(sel: str) -> str | None:
            loc = page.locator(sel)
            return None if loc is None else (loc.first.text_content(timeout=1000) if True else None)

        data = {
            "URL": url,
            "CNPJ": (await page.locator(S.SEL_CNPJ).text_content(timeout=2000)) if await page.locator(S.SEL_CNPJ).count() else None,
            "Nome Fantasia": (await page.locator(S.SEL_NOME_FANTASIA).text_content()) if await page.locator(S.SEL_NOME_FANTASIA).count() else None,
            "Atividade": (await page.locator(S.SEL_ATIVIDADE).text_content()) if await page.locator(S.SEL_ATIVIDADE).count() else None,
            "Inicio": (await page.locator(S.SEL_INICIO).text_content()) if await page.locator(S.SEL_INICIO).count() else None,
            "Situação": (await page.locator(S.SEL_SITUACAO).text_content()) if await page.locator(S.SEL_SITUACAO).count() else None,
            "Endereço": (await page.locator(S.SEL_ENDERECO).text_content()) if await page.locator(S.SEL_ENDERECO).count() else None,
            "Estado": (await page.locator(S.SEL_ESTADO).text_content()) if await page.locator(S.SEL_ESTADO).count() else None,
            "Motivo Situação": (await page.locator(S.SEL_MOTIVO).text_content()) if await page.locator(S.SEL_MOTIVO).count() else None,
            "Telefone": (await page.locator(S.SEL_FONE).text_content()) if await page.locator(S.SEL_FONE).count() else None,
            "Email": (await page.locator(S.SEL_EMAIL).text_content()) if await page.locator(S.SEL_EMAIL).count() else None,
        }
        # Normaliza espaços
        for k,v in list(data.items()):
            if isinstance(v, str):
                data[k] = " ".join(v.split())
        return data
    finally:
        await browser.close()
        await pw.stop()

async def run_segment(entrada: str, out_xlsx: str | None = None, checkpoint_dir: str = ".checkpoints") -> Path:
    from .utils import build_url
    base_url, default_xlsx = build_url(entrada)
    out_path = Path(out_xlsx or default_xlsx)

    ensure_dir(checkpoint_dir)
    ckpt_links = Path(checkpoint_dir) / (out_path.stem + "_links.txt")
    ckpt_rows = Path(checkpoint_dir) / (out_path.stem + "_rows.parquet")

    # Descobrir páginas e total
    total_pages, total_empresas = await discover_total_pages(base_url)
    print(f"📊 Páginas: {total_pages} | Empresas (informado): {total_empresas}")

    # Coletar links de listagem (com concorrência limitada)
    import asyncio
    sem = asyncio.Semaphore(SETTINGS.max_concurrency)
    all_links: list[str] = []

    async def _collect(pg_num: int):
        async with sem:
            links = await collect_listing_links(base_url, pg_num)
            all_links.extend(links)
            await jitter_delay(SETTINGS.delay_ms_min, SETTINGS.delay_ms_max)

    await asyncio.gather(*[_collect(i) for i in range(1, total_pages + 1)])

    # Checkpoint dos links
    ckpt_links.write_text("\n".join(all_links), encoding="utf-8")

    # Detalhes (também com concorrência limitada)
    rows: list[dict] = []
    async def _detail(u: str):
        async with sem:
            row = await parse_detail(u)
            rows.append(row)
            await jitter_delay(SETTINGS.delay_ms_min, SETTINGS.delay_ms_max)

    await asyncio.gather(*[_detail(u) for u in all_links])

    # Export
    df = pd.DataFrame(rows)
    df.drop_duplicates(subset=["CNPJ", "URL"], inplace=True, ignore_index=True)
    df.to_excel(out_path, index=False, engine="openpyxl")
    print(f"✅ Exportado: {out_path.resolve()} ({len(df)} registros)")

    return out_path
