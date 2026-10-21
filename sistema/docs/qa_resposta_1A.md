# Resposta ao QA cego da fatia 1A

Data: 21/10/2026. Relatório original: [qa_cego_1A.md](qa_cego_1A.md). Depois das correções: 56 testes passando (eram 35) e teste no navegador sem erro de console além das recusas esperadas.

## Corrigido

| Achado | O que foi feito | Teste |
|---|---|---|
| A-01 corrida no último administrador | Trava do banco serializa as alterações de usuário | `test_alteracao_de_usuario_espera_a_trava_dos_administradores` (falha sem a trava, passa com ela) |
| M-01 auditoria contornável | `scripts/papel_app.sql`: o app roda com papel sem UPDATE, DELETE, TRUNCATE nem permissão de desligar gatilho na auditoria | `test_papel_restrito_nao_altera_nem_desliga_a_auditoria` |
| M-02 campo nulo no PATCH | Campo nulo recusado com 422 | `test_patch_hostil_nunca_da_500` |
| M-03 senha acima de 72 bytes | Limite em bytes, 422 | `test_senha_com_acentos_acima_de_72_bytes...` |
| M-04 caractere NUL e de controle | Filtro em toda entrada de texto (controle, invisíveis e marcas bidirecionais) | `test_patch_hostil...`, `test_login_hostil...`, `test_parametros_formato_estrito...` |
| M-05, B-07 notação científica e formatos de número | Só dígitos ASCII, ponto ou vírgula; saída sem expoente | `test_parametros_formato_estrito...` |
| M-06 limite de corpo por partes | Limite aplicado no fluxo de bytes (ASGI) | `test_corpo_grande_recusado_inclusive_em_partes` |
| M-07 backups simultâneos | Trava de sessão, nome com microssegundos, 409 se já houver backup | `test_backups_simultaneos_nao_colidem` |
| M-08 usuário de login sem limite | Máximo de 40 caracteres, senha até 256 | `test_login_hostil_nao_da_500` |
| M-09 lacunas de teste | Testes novos de concorrência, entrada hostil e papel restrito | `tests/test_robustez.py` |
| B-03 limpar parâmetro apaga o padrão | Limpar volta ao padrão do catálogo | `test_limpar_parametro_volta_ao_padrao_do_catalogo` |
| B-04 deslocamento enorme | Máximo de 1.000.000 | `test_auditoria_deslocamento_enorme...` |
| B-05 detalhe técnico nas respostas | Mensagens fixas; detalhe só no log do servidor | `test_backup_com_copia_extra_falhando_avisa` |
| B-06 "Backup em dia" com cópia falha | Tela só fica verde se as cópias deram certo | tela |
| B-08 caracteres de controle em nomes | Coberto pelo filtro de M-04 | testes de M-04 |
| B-09 senha fraca | Recusa lista de senhas triviais e senha igual ao usuário | `test_senhas_fracas_recusadas` |
| B-10 permissão e dump parcial | Arquivo 600, dump parcial apagado, tamanho da cópia conferido | `test_backup_falho_nao_deixa_arquivo_parcial` |
| B-11 auditoria incompleta | Login, logout e backup manual auditados; alteração de usuário guarda o login | `test_login_e_logout_ficam_na_auditoria` |
| B-12 versões soltas | `requirements.txt` com versões fixas | |
| B-13 senha provisória em `prompt` | Campo de senha na própria linha | tela |
| S-01 IP forjável com proxy | Usa o último valor do cabeçalho do proxy confiável | |
| S-03, S-04 backup preso e pasta sem permissão | Conexão própria, sem transação aberta; falha de pasta registrada sem erro 500 | `test_pasta_de_backup_sem_permissao_nao_da_500` |

## Fica como limite conhecido (decisão adiada)

- **B-01 e B-02, rajada de login e bloqueio global:** com 1 a 5 pessoas na recepção e rede só local o risco é baixo; revisar se o sistema algum dia for exposto fora da loja.
- **S-02, colisão de hash no bloqueio:** probabilidade desprezível.
- **B-10 parte da criptografia:** o backup vai ao Google Drive sem senha e contém hashes de senha. Pergunta a Marlon: cifrar o arquivo antes de enviar?
