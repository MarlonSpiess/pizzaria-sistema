# Acesso ao sistema pelo tablet Android

Versão 1, 05/11/2026. Complementa o [Roteiro de Instalação](Roteiro_de_Instalacao_Loja.md), item 6.

O sistema roda no PC da loja e abre no navegador do tablet pela rede Wi-Fi da loja. Não há aplicativo para instalar. Fatos conferidos no código: o `start_api.bat` sobe o servidor em `0.0.0.0` (aceita conexões da rede) na porta `8080` (ou a definida em `PIZZARIA_PORT` no `set_env.bat`), e a tela de entrada fica no endereço raiz, `http://IP-DO-PC:8080`.

## 1. Preparar o PC da loja (uma vez)

1. Deixar o sistema no ar: a janela do `start_api.bat` precisa estar aberta. Conferir no próprio PC abrindo `http://localhost:8080`.
2. Descobrir o IP do PC: abrir o Prompt de Comando, digitar `ipconfig` e anotar o "Endereço IPv4" da placa Wi-Fi ou Ethernet ligada ao roteador da loja (exemplo `192.168.0.20`).
3. Conferir que a rede do Windows está como Privada: Configurações, Rede e Internet, clicar na rede em uso, "Tipo de perfil de rede" = Privada.
4. Liberar a porta no firewall. No Prompt de Comando aberto como administrador:
   ```
   netsh advfirewall firewall add rule name="Pizzaria 8080" dir=in action=allow protocol=TCP localport=8080 profile=private
   ```
   Se o Windows perguntou "Permitir acesso" ao Python na primeira vez que o sistema subiu e foi marcado só Rede privada, a regra já pode existir; o comando acima não atrapalha.
5. Fixar o IP: no roteador, criar uma reserva de DHCP para o PC da loja com o IP anotado. Sem isso o IP pode mudar e o tablet deixa de achar o sistema.

## 2. Conectar o tablet

1. No tablet: Configurações, Wi-Fi, entrar na MESMA rede do PC da loja (não usar rede de convidados nem dados móveis 4G/5G).
2. Abrir o Google Chrome.
3. Digitar na barra de endereço, com `http://` e a porta: `http://192.168.0.20:8080` (trocar pelo IP anotado).
4. Deve aparecer a tela "Sistema da Pizzaria" com o botão Entrar.

## 3. Entrar com o login pessoal

1. Cada pessoa usa o próprio usuário e senha, criados pelo administrador em Usuários. Nunca compartilhar login: cada tela mostra só o que a função permite (pizzaiolo vê Montagem, massa vê Massa, e assim por diante).
2. No primeiro acesso o sistema pede para trocar a senha (mínimo de 8 caracteres).
3. Após 5 senhas erradas em 15 minutos o login fica bloqueado por até 15 minutos.
4. A sessão dura até 12 horas. Ao fechar a aba ou o Chrome, é preciso entrar de novo (o login fica guardado só na aba aberta). Ao trocar de pessoa no mesmo tablet, usar Sair.

## 4. Criar o atalho na tela inicial

1. Com o sistema aberto no Chrome, tocar nos três pontos (canto superior direito).
2. Tocar em "Adicionar à tela inicial" e confirmar o nome (exemplo "Pizzaria").
3. O ícone aparece na tela inicial do tablet e abre direto o sistema.

## Se não abrir no tablet

| Sintoma | O que conferir |
|---|---|
| Página não carrega ou "ERR_CONNECTION_TIMED_OUT" | Regra do firewall (passo 1.4) e rede Privada (passo 1.3). |
| "ERR_ADDRESS_UNREACHABLE" | O tablet não enxerga esse IP: IP digitado errado (o do exemplo, ou de outra placa do PC como vEthernet, VirtualBox ou VPN), tablet em outra rede, ou roteador com isolamento de clientes. Comparar o IP do tablet com o do PC: os três primeiros números devem ser iguais. |
| "ERR_CONNECTION_REFUSED" | Janela do `start_api.bat` fechada ou com erro. |
| Abria e parou de abrir | IP do PC mudou: rodar `ipconfig` de novo e fixar a reserva no roteador. |
| Abre no PC e não no tablet | Tablet em outra rede (convidados, 4G) ou roteador com "isolamento de clientes" ligado. |
| Endereço digitado sem porta | Precisa terminar em `:8080`. |

Não abrir a porta 8080 para a internet: o sistema foi feito para a rede local da loja.

## Diagnóstico passo a passo (rede interna)

Fazer na ordem e parar no primeiro passo que falhar. Os comandos rodam no Prompt de Comando do PC da loja (os de firewall, como administrador).

1. **O sistema está escutando na rede?** `netstat -ano | findstr :8080`. Deve aparecer `0.0.0.0:8080 ... LISTENING`. Se aparecer `127.0.0.1:8080` ou nada, o sistema não foi aberto pelo `start_api.bat` (ele usa `--host 0.0.0.0`).
2. **Abre pelo IP no próprio PC?** No navegador do PC, `http://192.168.1.11:8080` (o IP, não `localhost`). Se não abrir, voltar ao passo 1.
3. **O PC enxerga o tablet?** `ping 192.168.1.20` e depois `arp -a | findstr 192.168.1.20`. Se o ping der "Host de destino inacessível" ou o `arp` não mostrar o tablet, o problema é a rede (Wi-Fi), não o sistema: ir ao passo 6.
4. **Perfil de rede é Privado?** No PowerShell: `Get-NetConnectionProfile`. `NetworkCategory` deve ser `Private`. Se for `Public`, trocar em Configurações, Rede e Internet, Wi-Fi, nome da rede, Tipo de perfil de rede.
5. **Regra do firewall existe?** `netsh advfirewall firewall show rule name="Pizzaria 8080"`. Se não existir, criar com o comando do passo 1.4. Para isolar a dúvida, desligar o firewall do perfil Privado por 1 minuto (`netsh advfirewall set privateprofile state off`), testar no tablet e religar (`netsh advfirewall set privateprofile state on`). Se só funcionar desligado, a regra está errada.
6. **Isolamento do Wi-Fi.** Redes com final `_Ext` são de repetidor. Muitos repetidores e redes de convidados bloqueiam a conversa entre aparelhos ("isolamento de clientes" ou "AP isolation"); o sintoma é exatamente `ERR_ADDRESS_UNREACHABLE` com os dois IPs na mesma faixa. Testes: ligar PC e tablet na rede principal do roteador (sem `_Ext`), ou o PC por cabo no roteador. Se funcionar, desativar o isolamento no painel do repetidor ou deixar a loja na rede principal.
7. **No tablet**, um app de varredura de rede (por exemplo Fing) mostra se o PC `192.168.1.11` aparece na rede. Se não aparecer, confirma o passo 6.

O erro mostrado no Chrome também ajuda: `ERR_ADDRESS_UNREACHABLE` indica rede (passos 3 e 6); `ERR_CONNECTION_TIMED_OUT` indica firewall (passos 4 e 5); `ERR_CONNECTION_REFUSED` indica sistema fora do ar (passos 1 e 2).

## Recomendação

Fazer a reserva de IP no roteador antes de criar os atalhos nos tablets, porque o atalho guarda o endereço e deixaria de funcionar se o IP mudar. Atenção também para a impressora térmica Bluetooth: o Chrome só libera Bluetooth para páginas em HTTPS ou no próprio aparelho, e o sistema hoje abre por `http://` na rede; esse teste pendente deve ser feito cedo para escolhermos o caminho de impressão.
