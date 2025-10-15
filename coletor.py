import time
import pandas as pd
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor
import re
import unicodedata
from math import ceil
import os
import sys
import json
import requests


def gerar_url_e_arquivo():
    entrada = input(
        "Digite o segmento (ex: 6920-6/01 - Atividades de contabilidade): ").strip()

    try:
        codigo, descricao = entrada.split(" - ", 1)
        codigo_limpo = codigo.replace("-", "").replace("/", "")
        descricao_url = (
            descricao.lower()
            .strip()
            .replace("ç", "c")
            .replace("ã", "a").replace("â", "a").replace("á", "a")
            .replace("é", "e").replace("ê", "e")
            .replace("í", "i")
            .replace("ó", "o").replace("õ", "o")
            .replace("ú", "u")
            .replace(" ", "-")
        )

        nome_arquivo = unicodedata.normalize('NFKD', descricao).encode(
            'ASCII', 'ignore').decode('ASCII')
        nome_arquivo = re.sub(r'[^a-zA-Z]', '', nome_arquivo)
        nome_arquivo += ".xlsx"

        url = f"https://empresasweb.net/empresas/{descricao_url}-{codigo_limpo}"
        return url, nome_arquivo
    except ValueError:
        print("Formato inválido. Use o formato: 6920-6/01 - Atividades de contabilidade")
        return gerar_url_e_arquivo()


def obter_total_paginas_e_empresas(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector('a[href*="/empresas/"]')

        # Pega número de páginas
        links = page.locator('a[href*="/empresas/"]')
        total_paginas = 1
        for i in range(links.count()):
            href = links.nth(i).get_attribute("href")
            if href and href.strip().split("/")[-1].isdigit():
                total_paginas = max(total_paginas, int(
                    href.strip().split("/")[-1]))

        # Captura número total de empresas
        texto_empresas = page.locator(
            '.okved-company-tools__label').text_content()
        match = re.search(r'de\s+([\d.]+)', texto_empresas)
        total_empresas = int(match.group(1).replace('.', '')) if match else 0

        print(
            f"\n📊 Encontramos {total_empresas} empresas nesse segmento. Iniciando a coleta...\n")
        browser.close()
        return total_paginas


def scrape_data(page, data_list, arquivo_excel):
    time.sleep(3)
    data = {}

    data['CNPJ'] = page.locator('//*[@id="clip_cnpj"]').text_content(
    ) if page.locator('//*[@id="clip_cnpj"]').is_visible() else None
    data['Nome Fantasia'] = page.locator('//*[@id="anketa"]/div[1]/div/div[1]').text_content(
    ) if page.locator('//*[@id="anketa"]/div[1]/div/div[1]').is_visible() else None
    data['Atividade'] = page.locator('//*[@id="anketa"]/div[2]/div[2]/div[1]/span[2]/a').text_content(
    ) if page.locator('//*[@id="anketa"]/div[2]/div[2]/div[1]/span[2]/a').is_visible() else None
    data['Inicio'] = page.locator('//*[@id="anketa"]/div[2]/div[1]/div[1]/div/dl[1]/dd[2]').text_content(
    ) if page.locator('//*[@id="anketa"]/div[2]/div[1]/div[1]/div/dl[1]/dd[2]').is_visible() else None
    data['Situação'] = page.locator('//*[@id="anketa"]/div[2]/div[1]/div[1]/div/dl[2]/dd[2]').text_content(
    ) if page.locator('//*[@id="anketa"]/div[2]/div[1]/div[1]/div/dl[2]/dd[2]').is_visible() else None
    data['Endereço'] = page.locator('//*[@id="contacts-row"]/div[1]/div/address/span[2]').text_content(
    ) if page.locator('//*[@id="contacts-row"]/div[1]/div/address/span[2]').is_visible() else None
    data['Estado'] = page.locator('//*[@id="contacts-row"]/div[1]/div/address/span[3]').text_content(
    ) if page.locator('//*[@id="contacts-row"]/div[1]/div/address/span[3]').is_visible() else None
    data['Motivo Situação'] = page.locator('//*[@id="anketa"]/div[2]/div[1]/div[1]/div/dl[2]/dd[4]').text_content(
    ) if page.locator('//*[@id="anketa"]/div[2]/div[1]/div[1]/div/dl[2]/dd[4]').is_visible() else None
    data['Telefone'] = page.locator('//*[@id="contacts-row"]/div[2]/div/span[2]/a').text_content(
    ) if page.locator('//*[@id="contacts-row"]/div[2]/div/span[2]/a').is_visible() else None
    data['Email'] = page.locator('//*[@id="contacts-row"]/div[3]/div/span[2]/a').text_content(
    ) if page.locator('//*[@id="contacts-row"]/div[3]/div/span[2]/a').is_visible() else None

    data_list.append(data)

    df = pd.DataFrame(data_list)
    df.to_excel(arquivo_excel, index=False, engine='openpyxl')
    print(data)
    print(f"✅ Dados salvos.")


def process_page(page, data_list, arquivo_excel):
    results = page.locator('//*[@id="main"]/div/div[2]/div[3]/div/div')
    count = results.count()
    if count == 0:
        print("⚠️ Nenhum resultado encontrado na página.")
        return

    for i in range(count):
        result = results.nth(i).locator('a')
        if result.count() > 0:
            result.first.click()
            scrape_data(page, data_list, arquivo_excel)
            page.go_back()
            time.sleep(1)


def process_pages(url, start, end, data_list, arquivo_excel):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page()
        for page_number in range(start, end + 1):
            full_url = f'{url}/{page_number}'
            page.goto(full_url)
            process_page(page, data_list, arquivo_excel)
        browser.close()


def main():
    url, arquivo_excel = gerar_url_e_arquivo()
    total_paginas = obter_total_paginas_e_empresas(url)
    paginas_browser = ceil(total_paginas / 5)

    data_list = []
    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(1, total_paginas + 1, paginas_browser):
                start = i
                end = min(i + paginas_browser - 1, total_paginas)
                futures.append(executor.submit(
                    process_pages, url, start, end, data_list, arquivo_excel))

            for future in futures:
                future.result()
    except Exception as e:
        print(f"❌ Ocorreu um erro: {e}")

    print("\n✅ Processo Finalizado com Sucesso!")
    input("Pressione Enter para sair...")


if __name__ == "__main__":
    main()
