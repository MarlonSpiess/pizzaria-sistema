# Revisão da estrutura do projeto (23/11/2026)

Escopo: repositório `MarlonSpiess/pizzaria-sistema` (main depois dos PRs #2 a #5), pasta local `C:\Maria Gabriela\Pizzaria` no mh-spiess e pasta compartilhada do projeto no Claude. Nada foi apagado, renomeado ou movido: este relatório só aponta e recomenda. O que depende de aprovação está na seção 5.

## 1. Resumo

1. Os PRs #2, #3, #4 e #5 foram mesclados na main, nessa ordem, sem conflito (merge commit, histórico preservado).
2. **Achado principal:** a pasta local do mh-spiess tem código que nunca foi para o git: o módulo de Checklists (melhoria M4) e as melhorias M1 e M2, feitos em 16/11/2026 sobre a base antiga (commit `08522c7`). Esse código usa as migrações `022_checklists.sql` e `023_pedido_controle.sql`, e o PR #5 trouxe outra `022`. Como o script de migração controla por número e checksum, copiar a main para o PC apagaria os Checklists e poderia travar a subida do sistema.
3. O trabalho local foi integrado num branch próprio, com a migração do PR #5 renumerada para **024**. Esse PR precisa entrar antes de qualquer cópia de código para o PC.
4. Existem hoje **quatro cópias** do sistema que não batem entre si: main, pasta local, `sistema/` e `sistema_copia/` na pasta do projeto no Claude.
5. A documentação técnica foi atualizada para a migração 024 e para as decisões de 23/11; ainda há documentos de planejamento com números e textos de 04/11 (seção 3.2).

## 2. Mapa atual

| Lugar | O que tem | Situação |
|---|---|---|
| GitHub, main | `planejamento/` e `sistema/` até a migração 022 (PR #5), sem Checklists | Fonte oficial, mas incompleta |
| GitHub, branch de integração (este PR) | main + trabalho local de 16/11 + protótipos de layout do PR #1 + `Acesso_pelo_Tablet.md` + migração 024 | Aguarda aprovação |
| GitHub, PR #1 | Três modelos de layout | Conteúdo idêntico já está no branch de integração |
| GitHub, branch `claude/project-thread-xpd82o` | `Acesso_pelo_Tablet.md` (sem PR) | Conteúdo idêntico já está no branch de integração |
| PC mh-spiess, `C:\Maria Gabriela\Pizzaria` | Sistema em uso (base `08522c7` + Checklists), `planejamento/` com `melhoria_continua/`, `revisao_ub_mode/` e `revisao_ub_mode2/` | Em uso; não foi tocado |
| Pasta do projeto no Claude | `planejamento/`, `sistema/` (versão parada antes dos PRs #4 e #5), `sistema_copia/`, duas cópias de `03_Padroes_de_Layout` na raiz, gabarito, `.notes/` | Mistura de cópias antigas |

## 3. Achados

### 3.1 Prioridade alta

| # | Achado | Recomendação |
|---|---|---|
| A1 | Código só na pasta local (Checklists, M1, M2), sem git e sem a aprovação do pacote de 16/11 (o próprio `pacote_aprovacao/00_Resumo_e_Decisoes.md` diz que foi feito antes da aprovação e que os testes não tinham rodado). | Aprovar o PR de integração. Daqui em diante, nenhuma mudança de código direto na pasta do PC: toda mudança passa por branch e PR, e o PC só recebe a main. |
| A2 | Número de migração repetido (022 local e 022 do PR #5). | Feito no PR de integração: a do PR #5 virou `024_pedido_volta_para_producao.sql`. Ela nunca foi aplicada no PC, então a troca é segura. |
| A3 | O arquivo `sistema\set_env.bat.example` da pasta local tem uma **senha real** do banco no lugar do texto de exemplo, e existe um `set_env.bat.bak`. O exemplo é o arquivo que vai para o git. | Não foi copiado para o git. Recomendo trocar essa senha no PostgreSQL e no `set_env.bat`, voltar o exemplo para `troque_esta_senha` e apagar o `.bak` (pendência antiga). |
| A4 | Quatro cópias do sistema divergentes (seção 2). | Uma só fonte: o GitHub. A pasta do PC recebe a main por cópia controlada; a pasta do projeto no Claude deixa de guardar código (apagar `sistema/` e `sistema_copia/` de lá, depois da sua aprovação). |

### 3.2 Prioridade média

| # | Achado | Recomendação |
|---|---|---|
| M1 | `README.md` da raiz ainda fala em "9 módulos" e "plano macro v1.0, aguarda aprovação". `sistema/README.md` diz "versão do PR #2, migrações até a 018". | Reescrever os dois (curto): 3 áreas, onde está cada coisa, link para `documentacao/00_Indice.md`. |
| M2 | Plano Macro, seção 0, e a apresentação v2 dizem "21 migrações, 103 tabelas, 257 rotas". Hoje são 24 migrações, 110 tabelas e 270 rotas. | Atualizar a seção 0 com uma linha de 23/11; gerar a apresentação v3 só quando houver mudança de conteúdo, não por números. |
| M3 | Checklists aparece nos menus do código (Produção, Vendas e Administrativo), mas não está em `menus/01_Estrutura_de_Menus.md` nem no Plano Macro. | Acrescentar o menu Checklists à estrutura de menus e uma linha "melhoria contínua" na seção 0 do Plano Macro, marcando como proposta até você responder o pacote de aprovação. |
| M4 | `03_Padroes_de_Layout.md` em três lugares: raiz da pasta do projeto (versão antiga, sem a conferência visual), raiz com sufixo `-20261030T163640-c431` (versão final) e `planejamento/desenho_tecnico/` na pasta local (igual à final; agora no branch de integração). | Manter só `planejamento/desenho_tecnico/03_Padroes_de_Layout.md` e apagar as duas cópias da raiz da pasta do projeto. |
| M5 | Documentos Word repetidos em `melhoria_continua/`: `Checklists_da_Pizzaria.docx` = `pacote_aprovacao/01_...`; `Modulo_Checklists_M4.docx` = `pacote_aprovacao/02_...`; `referencia/lista compacta - pizzaria.docx` = `pacote_aprovacao/04_...` (conferido byte a byte). | Manter as versões de `pacote_aprovacao/` e apagar as três repetidas, ajustando o link no `01_Checklists.md` e no índice. |
| M6 | Siglas que se confundem: "M4" é a melhoria de Checklists, mas também é o "Detalhamento 04" (Estoques e Compras) e as respostas "M1 a M18" do Imobilizado. E a numeração dos arquivos de `modulos/` (01 Núcleo e Vendas ... 08 RH) é a ordem de construção, diferente da numeração do Plano Macro (1 RH, 2 Imobilizado ... 9 BI). | Renomear as melhorias para MC1 a MC8 (melhoria contínua) e pôr uma linha no índice explicando as duas numerações. Não renomear os arquivos dos módulos, porque são registro aprovado e têm links. |
| M7 | Código dentro de `planejamento/`: `instalacao/carga_inicial.py`, com o caminho `C:\Maria Gabriela\Pizzaria` fixo. | Mover para `sistema/scripts/` e ler o caminho da pasta do próprio script. |
| M8 | O gerador do Apêndice B (`fonte/gerar_apendice_permissoes.py`) estava quebrado desde o PR #4 (a matriz virou `_MATRIZ` com `frozenset`). | Corrigido no PR de integração e conferido: 55 permissões, 0 divergência com o código. |

### 3.3 Prioridade baixa

| # | Achado | Recomendação |
|---|---|---|
| B1 | `sistema/docs/` tem 27 relatórios de QA soltos (rodadas 1A a 6 e duas rodadas ub-mode). | Separar em `sistema/docs/qa/<rodada>/` quando houver a próxima rodada. |
| B2 | Na pasta local, `revisao_ub_mode/` e `revisao_ub_mode2/` são cópias dos relatórios que agora estão no git. | Apagar depois que a main for copiada para o PC. |
| B3 | O `logo.svg` da pasta local ganhou metadados de alguma ferramenta (bloco c2pa). | Ficar com a versão do git na próxima cópia. |
| B4 | Apresentação v1 (3 PDFs, `fonte_v1/` e `project/`) misturada com a v2 na mesma pasta. | Mover a v1 para `apresentacao/arquivo_v1/`. |
| B5 | Branches já mescladas continuam no GitHub (`qkmkh7`, `41vyn4`, `cgrh54`, `vgg9td`) e há a `xpd82o` sem PR. | Apagar depois da aprovação do PR de integração; fechar o PR #1, cujo conteúdo entra por ele. |
| B6 | Os 9 documentos de módulo (`modulos/`) continuam válidos como registro e já abrem com a caixa "Situação em 04/11/2026" explicando as 3 áreas; o Manual Técnico, seção 9, tem a tabela dos 9 módulos para as 3 áreas. | Manter como está. Não vale reorganizar `modulos/` por área. |

## 4. Estrutura proposta (depois da aprovação)

```
README.md                      atualizado (3 áreas, onde está cada coisa)
planejamento/
  00_Plano_Macro.md            seção 0 atualizada em 23/11
  modulos/                     sem mudança (registro aprovado)
  menus/  arquitetura/  desenho_tecnico/  prototipos/  carga/  instalacao/
  melhoria_continua/           sem os .docx repetidos; MC1 a MC8
  documentacao/                índice v2.1 (já feito)
  apresentacao/                v2 + arquivo_v1/
  revisao/                     este relatório
sistema/
  api/  frontend/  migrations_pg/ (001 a 024)  scripts/ (com carga_inicial.py)
  tests/  tests_unidade/  tools/  docs/ (qa/ por rodada)
```

## 5. Decisões para você, uma a uma (com recomendação)

1. **Integrar o módulo de Checklists no repositório?** Recomendo sim, pelo PR de integração (já aberto para sua aprovação). O pacote de aprovação de 16/11 continua valendo para decidir o que fica ligado.
2. **Os Checklists ficam ligados para todas as funções antes do piloto em papel?** O pacote de 16/11 recomendava construir só depois do piloto (M4-10), e hoje as abas aparecem para todos. Recomendo deixar ligado só para a gerência até você responder o pacote, e decidir se o subgerente pode liberar a loja sem o checklist de início.
3. **Quando copiar a main para o PC?** Recomendo num horário sem venda, depois do item 1, com backup antes; a cópia preserva `set_env.bat`, `venv/` e `backups/` e aplica só as migrações que faltarem no banco (a 024 e, se ainda não tiverem sido aplicadas, a 022 e a 023; o `--dry-run` mostra antes).
4. **Trocar a senha do banco que apareceu no arquivo de exemplo?** Recomendo sim, no mesmo horário da cópia.
5. **Limpar a pasta do projeto no Claude** (`sistema/`, `sistema_copia/`, as duas cópias de `03_Padroes_de_Layout` na raiz)? Recomendo sim.
6. **Arrumações de média e baixa prioridade** (M1, M3, M5, M6, M7, B1, B4, B5)? Recomendo fazer num PR só de organização, sem mudar código de regra.

## 6. Recomendação

Aprovar o PR de integração primeiro, porque ele junta as duas versões do sistema e resolve o número de migração repetido; em seguida, marcar o horário da cópia para o PC e, por último, o PR de organização.
