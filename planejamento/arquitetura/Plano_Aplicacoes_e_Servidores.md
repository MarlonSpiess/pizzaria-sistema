# Plano de aplicações e servidores (Etapa 3)

Versão 0.2, 04/11/2026. Servidor único com módulos separados APROVADO por Marlon em 04/11/2026. Parte do que já existe no sistema e marca o que ainda depende de decisão ou de informação externa. Nada aqui foi implantado.

## 1. Situação atual (fato)

- Um único servidor de aplicação (FastAPI) serve a API e a tela (JavaScript simples) para as 3 áreas: Produção, Vendas e Administrativo. Um login, 3 áreas.
- Um único banco PostgreSQL. O acesso por função é conferido no servidor, não na tela.
- Roda no PC da loja, na rede local, com tablets e outro PC como clientes (roteiro em planejamento/instalacao).
- Estrutura de Canais (Anota Ai e iFood) existe, sem integração real.

## 2. Proposta de arquitetura

**Recomendação: manter um servidor único com módulos separados no código (monólito modular), e não 3 servidores.**

Motivos: uma loja só, um login só, mesmo banco e mesmas regras de acesso. Separar em 3 servidores aumentaria a manutenção sem ganho agora. O código já é dividido por módulo (rotas e permissões por função) e a tela tem o seletor de áreas.

| Peça | Função | Onde roda no beta |
|---|---|---|
| Aplicação web (API + telas) | As 3 áreas | PC da loja |
| PostgreSQL | Dados | PC da loja |
| Serviço de canais (PROPOSTA, não decidido) | Receber pedidos do Anota Ai e iFood e colocar na fila de entrada | A definir (mesmo servidor, processo separado, é uma opção) |
| Impressão | Etiquetas (teste da impressora Bluetooth pendente) | Tablet do acabamento |

## 3. Pontos a decidir (não inventar)

1. **Como o Anota Ai entrega pedidos**: a API não é pública; depende do token e da documentação liberados pelo Anota Ai (por chamado). Se será consulta periódica ou aviso (webhook) só se sabe com a documentação. Sem isso, o serviço de canais fica só como estrutura.
2. **Acesso de fora da loja**: se for webhook, será preciso um endereço acessível pela internet (depende da documentação do Anota Ai). No PC da loja isso exige exposição segura (túnel ou nuvem). Decisão do Marlon quando chegar o momento; a recomendação é nuvem quando a integração entrar.
3. **Nuvem**: o README do sistema diz pronto para migrar, mas isso ainda não foi testado. O backup está adiado, como combinado (roteiro de instalação).
4. **Tablets**: Android 14 ou mais novo, acesso pelo navegador, pelo IP fixo do PC da loja.

## 4. Segurança que já vale e o que falta

Já vale: acesso rígido por função no servidor, senha com troca obrigatória, auditoria, testes de acesso por perfil.
Falta antes de expor fora da loja: HTTPS (nada no código ainda); conferir que DOCS_ENABLED continua desligado (o padrão já é desligado); definir CLIENT_IP_HEADER se houver proxy, senão todos os clientes aparecem com o IP do proxy no limite de tentativas; token dos canais ainda não existe no código e deve ficar fora do banco (intenção).

## 5. Ordem sugerida

1. Fechar pendências de segurança do servidor.
2. Rodar o beta no PC da loja com as 3 áreas.
3. Quando o Anota Ai liberar o token: serviço de canais e aceitar pedido da fila.
4. Decidir nuvem e HTTPS antes de qualquer acesso externo.

## 6. Pendências marcadas (sem decisão, não inventar)

| Item | Depende de | Situação |
|---|---|---|
| Como o Anota Ai entrega pedidos (consulta ou aviso) | Token e documentação do Anota Ai | Pendente |
| iFood | Acesso ao portal do iFood (não pôde ser lido) | Pendente |
| Nuvem | Decisão de Marlon | Pendente |
| HTTPS e acesso de fora da loja | Decisão da nuvem | Pendente |
| Aceitar pedido da fila e virar pedido do sistema | Formato do pedido do Anota Ai | Pendente |
| Cópia na pasta local C:\Maria Gabriela\Pizzaria | Pasta fora do ar | Pendente |

## 7. Integração com o Anota Ai: decisão de Marlon (04/11/2026)

O Anota Ai tem API. O sistema chama a API (nada chega de fora), então continua na loja, sem nuvem e sem HTTPS por enquanto.

- **Varredura a cada 1 segundo** dos pedidos novos, enquanto o canal estiver ativo. Em falha, espera crescente e registro no log.
- **Aviso ao Anota Ai** quando o pedido está pronto (entrega), saiu para entrega ou está disponível para retirada. Fila com tentativas: se a internet cair, o aviso espera e é reenviado.
- **Construído (estrutura, testada com adaptador falso):** migração 014, varredor em segundo plano, fila de avisos, trava para só um processo trabalhar por canal.
- **Pendente da documentação da API:** endereços, autenticação, formato do pedido e de cada aviso (adaptador em `api/services/anotaai.py`), limite de chamadas (a cada 1 segundo pode exceder), e a importação do pedido da fila para o sistema. URL e token entram por variáveis de ambiente `ANOTAAI_URL` e `ANOTAAI_TOKEN`.
- **Cancelamento:** hoje não gera aviso; decidir se o Anota Ai precisa receber.
