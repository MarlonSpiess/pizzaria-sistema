"""Carga inicial do cardápio (e, se confirmado, das fichas técnicas). Rodar com o start_api.bat já aberto.
A senha do admin é pedida sem eco e não é gravada."""
import getpass
import os
import subprocess
import sys
from pathlib import Path

S = Path(r"C:\Maria Gabriela\Pizzaria\sistema")
PY = str(S / "venv" / "Scripts" / "python.exe")
URL = "http://127.0.0.1:8080"
env = dict(os.environ, PZ_SENHA=getpass.getpass("Senha do admin: "))


def rodar(script, *extra):
    r = subprocess.run([PY, str(S / "scripts" / script), "--usuario", "admin", "--url", URL, *extra], env=env, cwd=S)
    if r.returncode:
        sys.exit(f"[erro] {script} falhou; nada mais foi feito.")


print("\n=== Simulação do cardápio ===")
rodar("carregar_cardapio.py")
if input("\nGravar o cardápio? (s/n) ").strip().lower() == "s":
    rodar("carregar_cardapio.py", "--aplicar")
    print("\n=== Fichas técnicas (simulação) ===")
    rodar("carregar_ficha_tecnica.py")
    if input("\nAs fichas são as reais? Gravar? (s/n) ").strip().lower() == "s":
        rodar("carregar_ficha_tecnica.py", "--aplicar")
print("\n[fim] Pode fechar esta janela.")
input()
