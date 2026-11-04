"""Converte os manuais de usuário (.md) em .docx com o pandoc. Uso, na raiz: python planejamento/documentacao/fonte/gerar_docx.py"""
import subprocess
from pathlib import Path

PASTA = Path(__file__).resolve().parents[1] / "usuario"
for md in sorted(PASTA.glob("*.md")):
    saida = md.with_suffix(".docx")
    subprocess.run(["pandoc", str(md), "-o", str(saida), "--resource-path", str(PASTA)], check=True)
    print(saida.name)
