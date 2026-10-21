# Sistema da Pizzaria: código

Fatia 1A (Núcleo), versão 0.1. Desenho em [planejamento/desenho_tecnico/01_Primeiro_Incremento.md](../planejamento/desenho_tecnico/01_Primeiro_Incremento.md).

## O que já funciona

Login seguro (bloqueio após 5 falhas, sessão em tabela, token guardado como hash), 8 perfis com permissão negada por padrão, usuários com troca de senha no primeiro acesso, parâmetros da loja com histórico, auditoria só de inserção, `/health`, backup com cópia para pastas extras e teste de restauração, e uma tela simples (entrar, painel, usuários, parâmetros, auditoria).

Ainda não existe: cardápio, pedido, produção e caixa (fatias 1B a 1E).

## Instalar no PC da loja (Windows)

1. Instalar Python 3.11 ou mais novo e PostgreSQL 16 (ou mais novo). Anotar a senha do usuário `postgres`.
2. Criar o banco e um usuário do app (pelo pgAdmin ou `psql`): `CREATE DATABASE pizzaria;` e um usuário com senha própria.
3. Nesta pasta: `python -m venv venv`, `venv\Scripts\activate`, `pip install -r requirements.txt`.
4. Copiar `set_env.bat.example` para `set_env.bat` e preencher (senha do banco, pastas de backup). Esse arquivo nunca vai para o git.
5. Aplicar as migrations e criar o primeiro administrador: `python scripts\aplicar_migrations_pg.py`, depois `python scripts\criar_admin.py --usuario admin --nome "Seu Nome" --loja-nome "Nome da Pizzaria"` (a senha é pedida sem eco).
6. Subir: `start_api.bat`. Abrir `http://IP-DO-PC:8080` nos outros PCs e tablets; liberar a porta só para a rede privada no firewall do Windows.

## Backup

`python scripts\backup.py` faz o `pg_dump`, copia para `BACKUP_DIRS_EXTRA` (pasta do Google Drive para computador e pasta do computador de Marlon) e mantém os últimos 30. Rodar ao fechar o dia (Agendador de Tarefas do Windows) ou pelo botão "Fazer backup agora" no painel. Testar a restauração: `python scripts\restaurar_em_teste.py <arquivo.dump> pizzaria_restauracao_teste` (cria um banco novo, nunca mexe no banco em uso).

## Testes

Precisam de um PostgreSQL local. O banco de teste tem de terminar em `_teste` e é recriado a cada execução:

```
set TEST_DB_PASS=...  (e TEST_DB_HOST, TEST_DB_PORT, TEST_DB_USER se não forem os padrões)
python -m pytest -q
```
