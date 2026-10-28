# Roteiro de instalação no PC da loja (Windows)

Versão 1, 28/10/2026. Cobre a instalação do sistema, a primeira carga e o acesso pelos PCs e tablets. Tudo roda no PC da loja, na rede local. O backup em nuvem fica para depois, como combinado.

## Antes de começar

- PC com Windows ligado durante o expediente (cerca de 10 horas por dia) e ligado à mesma rede (roteador) dos tablets e do outro PC.
- Ter à mão: o Python 3.11 ou mais novo e o PostgreSQL 16 ou mais novo.
- Fixar o IP do PC da loja no roteador (reserva de IP). Sem isso o endereço muda e os tablets perdem o acesso.

## 1. Instalar os programas

1. Python: baixar de python.org e instalar marcando "Add Python to PATH".
2. PostgreSQL: baixar de postgresql.org e instalar com o pgAdmin. Anotar a senha do usuário `postgres` (guarde num lugar seguro).
3. Copiar a pasta `sistema` (a mesma que está em C:\Maria Gabriela\Pizzaria\sistema) para o PC da loja, por exemplo em `C:\Pizzaria\sistema`.

## 2. Criar o banco e o usuário do aplicativo

No pgAdmin (ou no `psql`, com o usuário `postgres`):

```sql
CREATE DATABASE pizzaria;
CREATE ROLE pizzaria_app LOGIN PASSWORD 'uma_senha_forte_para_o_app';
```

O usuário `pizzaria_app` não deve ser superusuário. A senha do app é outra, diferente da do `postgres`.

## 3. Preparar o ambiente do sistema

Abrir o Prompt de Comando na pasta `sistema`:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy set_env.bat.example set_env.bat
notepad set_env.bat
```

No `set_env.bat`, preencher:
- `DB_USER=pizzaria_app` e `DB_PASS=` a senha do app.
- `MIGRATE_DB_USER=postgres` e `MIGRATE_DB_PASS=` a senha do `postgres` (usado só para migrações e para criar o administrador). Se o seu `set_env.bat.example` não tiver essas duas linhas, acrescente.
- `BACKUP_DIRS_EXTRA` pode ficar vazio por enquanto.

O arquivo `set_env.bat` guarda senhas: nunca vai para o GitHub.

## 4. Criar as tabelas e o primeiro administrador

```
call set_env.bat
python scripts\aplicar_migrations_pg.py
psql -U postgres -d pizzaria -v app_role=pizzaria_app -f scripts\papel_app.sql
python scripts\criar_admin.py --usuario admin --nome "Seu Nome" --loja-nome "Nome da Pizzaria"
```

A senha do administrador é pedida sem eco e deve ser trocada no primeiro acesso. O `papel_app.sql` impede que o aplicativo apague ou altere a auditoria.

## 5. Subir o sistema

```
start_api.bat
```

A janela precisa ficar aberta. Para abrir sozinho ao ligar o PC, criar uma tarefa no Agendador de Tarefas do Windows, "ao iniciar", executando `start_api.bat` na pasta `sistema`.

Teste no próprio PC: abrir `http://localhost:8080` no navegador e entrar com `admin`. Se a página de entrada abrir, o sistema está no ar.

## 6. Liberar o acesso na rede da loja

1. Descobrir o IP do PC: `ipconfig` e olhar "Endereço IPv4" (exemplo 192.168.0.20).
2. No Firewall do Windows, criar uma regra de entrada para a porta 8080, só para rede privada.
3. Nos tablets e no outro PC: abrir o navegador (Chrome) em `http://192.168.0.20:8080` e entrar com o login pessoal de cada pessoa.
4. Dica: adicionar o endereço à tela inicial do tablet para abrir como se fosse um aplicativo.

Não abra a porta para a internet. O sistema foi feito para a rede local.

## 7. Primeira carga

Nesta ordem, ainda na tela do administrador:

1. Usuários: criar um login para cada pessoa e o perfil certo (massa, pizzaiolo, acabamento, atendente, gerente, subgerente).
2. Parâmetros: preencher os limites de desconto por perfil, aprovações de compra e de contas, meta de CMV e taxa de entrega padrão. O que ficar em branco usa o padrão seguro.
3. Cardápio e fichas técnicas (opcional, pelo script, que primeiro só simula):
   ```
   set PZ_SENHA=sua_senha
   python scripts\carregar_cardapio.py --usuario admin
   python scripts\carregar_cardapio.py --usuario admin --aplicar
   python scripts\carregar_ficha_tecnica.py --usuario admin --aplicar
   ```
   As fichas só devem ser carregadas se forem as reais. Ficha com dado de exemplo estraga o custo e a lista de compras.
4. Em Contas: "Criar tipos de despesa padrão", cadastrar a conta bancária da loja e as regras de recebimento (taxa e prazo de crédito, débito e Pix).
5. Em Estoque: lançar o estoque inicial dos itens (isto vira o ponto de partida do CMV).

## 8. Antes do primeiro dia de uso

- Fazer um pedido de teste em cada canal, acompanhar nos tablets (massa, montagem, forno, acabamento) e cancelar o pedido de teste com motivo.
- Testar a impressora de etiqueta Bluetooth pelo navegador do tablet. É o ponto de maior risco: se não imprimir direto, avisar para escolhermos o caminho alternativo antes de abrir.
- Fazer a contagem cega do caixa e o fechamento num dia de teste.

## Backup (adiado)

Combinado: ignorar por enquanto. Até lá, o comando manual `python scripts\backup.py` gera uma cópia do banco na pasta de backup. Recomenda-se rodar ao fechar o dia e copiar o arquivo para um pen drive.

## Se algo der errado

- Página não abre no tablet: conferir se o `start_api.bat` está aberto, o IP do PC e a regra do firewall.
- "Erro de conexão com o banco": o serviço do PostgreSQL pode estar parado (Serviços do Windows) ou a senha do `set_env.bat` está errada.
- Esqueceu a senha do administrador: rodar `criar_admin.py` não recria usuário existente; avise para gerarmos um passo de redefinição.
- Mandar prints da janela do `start_api.bat` junto com a descrição do problema.
