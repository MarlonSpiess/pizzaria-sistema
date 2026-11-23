"""Testes de unidade: só funções puras, sem banco. Rodam em segundos e servem ao teste de mutação."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# api.config exige a variável; nenhum teste daqui conecta. Mesmo padrão de tests/conftest.py: rodando as duas pastas
# juntas (python -m pytest), quem carregar primeiro não pode deixar uma senha falsa para os testes com banco.
os.environ.setdefault("DB_PASS", os.getenv("TEST_DB_PASS", "teste"))
