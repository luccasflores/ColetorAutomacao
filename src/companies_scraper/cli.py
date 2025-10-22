import asyncio
import argparse
from .scraper import run_segment

def main():
    parser = argparse.ArgumentParser(
        description="Scraper de empresas por segmento (empresasweb) -> Excel"
    )
    parser.add_argument(
        "--segmento",
        required=True,
        help='Ex.: "6920-6/01 - Atividades de contabilidade"'
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Caminho do Excel de saída (opcional). Padrão: derivado da descrição."
    )
    args = parser.parse_args()
    asyncio.run(run_segment(args.segmento, args.out))

if __name__ == "__main__":
    main()
