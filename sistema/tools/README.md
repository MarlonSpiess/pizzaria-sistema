# Ferramentas de revisão do código

Usadas na revisão pelo método ub-mode (06/11/2026). Instalar com `pip install -r requirements-dev.txt` (só na máquina de desenvolvimento, nunca no PC da loja). Todos os comandos rodam a partir de `sistema/`.

| Ferramenta | Para que serve | Comando |
|---|---|---|
| crapper | CRAP por função (complexidade x falta de cobertura). Meta: abaixo de 10 | `python -m pytest -q --cov=api --cov-report=json:cobertura.json` e depois `python tools/crapper.py cobertura.json 10` |
| dryer | Trechos duplicados entre arquivos | `pylint --disable=all --enable=duplicate-code --min-similarity-lines=6 --ignore-imports=yes --ignore-signatures=yes api scripts` |
| mutator | Teste de mutação das funções puras com os testes de unidade (sem banco) | `mutmut run` e `mutmut results` (configuração em `setup.cfg`) |
| código morto | Imports e variáveis sem uso | `python -m pyflakes api scripts tests_unidade` |

Notas:

- O teste de mutação usa só `tests_unidade/` porque a suíte com banco leva minutos; por isso só as funções puras entram (`setup.cfg` lista o que fica de fora).
- Sobreviventes equivalentes já conhecidos (não há teste que os distinga): `"utf-8"` x `"UTF-8"` no bcrypt, formato `"f"` x `"F"` em `fmt`, soma a partir de zero em `preco_pizza`, e as regras de `_um_de` montadas na importação do módulo.
