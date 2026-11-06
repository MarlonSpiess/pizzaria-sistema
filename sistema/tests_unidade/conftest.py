"""Testes de unidade: só funções puras, sem banco. Rodam em segundos e servem ao teste de mutação."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DB_PASS", "sem-banco")  # api.config exige a variável; nenhum teste daqui conecta
