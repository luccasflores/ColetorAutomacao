# 🧠 Coletor CNAE — M&H Soluções (versão modular/CLI)

Scraper para **coleta de empresas por segmento (CNAE)** em fontes públicas, com foco em **robustez, retomada** e **uso responsável**.  
Implementação **modular** com **Playwright assíncrono**, **concorrência limitada**, *retries* exponenciais e exportação final para **Excel**.

> Esta versão reflete as **mudanças recentes no código** (estrutura em `src/companies_scraper`, CLI, .env, etc.).

---

## 🚩 Principais mudanças (o que está diferente do script antigo)

- ✅ Sem `input()` interativo → agora é **CLI** (`--segmento` / `--out`).  
- ✅ **Playwright assíncrono** (`asyncio`) com **Semaphore** para controlar concorrência.  
- ✅ Coleta de **links na listagem** e visita direta aos detalhes (sem “clicar e voltar”).  
- ✅ **Retries**, **timeouts**, **User-Agent** configurável via `.env`.  
- ✅ **Delays aleatórios** (jitter) para reduzir padrão de bot.  
- ✅ **Checkpoints** em `.checkpoints/` (links e progresso).  
- ✅ Export único **.xlsx** com `drop_duplicates(CNPJ, URL)`.

---

## 📁 Estrutura do Projeto

```bash
ColetorCNAE/
├── src/
│   └── companies_scraper/
│       ├── __init__.py
│       ├── cli.py            # Ponto de entrada da CLI
│       ├── config.py         # Settings a partir do .env (concurrency, timeouts, user-agent)
│       ├── scraper.py        # Pipeline principal (descoberta, listagem, detalhes, export)
│       ├── selectors.py      # Seletores centralizados (listagem e detalhes)
│       └── utils.py          # slugify, build_url, jitter, ensure_dir
├── .env.example              # Exemplo de configuração
├── pyproject.toml            # Script entrypoint e deps (opcional)
├── requirements.txt
└── README.md                 # (este arquivo)
```

---

## 🔧 Instalação

Pré‑requisitos:
- **Python 3.11+**
- **Google Chrome** (ou Chromium) instalado

Crie o ambiente e instale:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

> Em Linux/macOS, ajuste o caminho de ativação do venv conforme seu shell.

---

## ⚙️ Configuração (opcional via `.env`)

Crie um `.env` a partir de `.env.example` para personalizar comportamento:

```ini
# .env
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) ColetorCNAE/0.1
MAX_CONCURRENCY=4
REQUEST_DELAY_MS_MIN=300
REQUEST_DELAY_MS_MAX=900
TIMEOUT_MS=30000
```

---

## ▶️ Uso (CLI)

Execute pelo módulo:

```powershell
python -m companies_scraper.cli --segmento "6920-6/01 - Atividades de contabilidade"
# ou definindo o arquivo de saída
python -m companies_scraper.cli --segmento "6920-6/01 - Atividades de contabilidade" --out .\data\contabilidade.xlsx
```

- O nome do arquivo é derivado automaticamente da **descrição do CNAE** caso `--out` não seja informado.  
- Os **links coletados** são salvos em `.checkpoints/<nome>_links.txt` (útil para auditoria/retomada).  
- O export final fica em **.xlsx** (engine `openpyxl`).

### Colunas exportadas
- `URL`, `CNPJ`, `Nome Fantasia`, `Atividade`, `Inicio`, `Situação`, `Endereço`, `Estado`, `Motivo Situação`, `Telefone`, `Email`

> Observação: dependendo da disponibilidade no site, alguns campos podem vir vazios.

---

## 🧩 Como funciona (pipeline)

1. **build_url**: a partir do texto `"6920-6/01 - Descrição"`, monta a URL (`.../descricao-sem-acentos-69206-01`).  
2. **discover_total_pages**: visita a primeira página, detecta paginação e total (quando disponível).  
3. **collect_listing_links**: coleta todos os links de detalhes por página (concorrência limitada).  
4. **parse_detail**: abre cada detalhe e extrai os campos (seletores centralizados).  
5. **Export**: consolida em `pandas`, remove duplicatas e grava `.xlsx`.

---

## 🧪 Troubleshooting

- **“chromium não encontrado”** → rode `python -m playwright install chromium`.  
- **Erros intermitentes de rede** → o código já faz *retry* exponencial; diminua `MAX_CONCURRENCY` ou aumente `REQUEST_DELAY_MS_*`.  
- **Campos vazios** → pode ser variação de layout; ajuste seletores em `selectors.py`.  
- **Bloqueios do site** → reduza concorrência/delays e evite execuções agressivas; respeite Termos de Uso.

---

## 🔒 Responsabilidade e LGPD

- Respeite os **Termos de Uso** e `robots.txt` do site fonte.  
- Utilize os dados respeitando a legislação (ex.: **LGPD**).  
- Este software destina-se a **fins internos/educacionais**. O autor não se responsabiliza por uso indevido.

---

## 📜 Licença

MIT — veja `LICENSE`.

---

## ✍️ Créditos

Desenvolvido por **Luccas Flores (M&H Soluções)**  
📧 *luccasflores.dev@gmail.com* · 🔗 LinkedIn/GitHub no perfil
