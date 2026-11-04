"""Gera as apresentações v2 (sistema e comercial) e os fluxogramas v2 em HTML; render.js converte em PDF.
Uso: python gen_v2.py && node render.js"""
import math
import re

from lib import *
import fluxos_v2
from fluxo import legenda

DATA = '04/11/2026'
FONTS = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Oswald:wght@400..700&family=DM+Sans:wght@400..700&display=swap">'
CSS = """
@page{size:1920px 1080px;margin:0}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:'DM Sans',Arial,sans-serif}
section.s{position:relative;width:1920px;height:1080px;overflow:hidden;page-break-after:always;break-after:page;padding:80px 128px 0}
.cream{background:#FAF6EF;color:#2B2420}.dark{background:#1E1A17;color:#FAF6EF}.red{background:#B5361F;color:#FAF6EF}
.tag{font-size:24px;font-weight:700;letter-spacing:4px;text-transform:uppercase;color:#B5361F}
.dark .tag{color:#D9A441}.red .tag{color:#F6D9A0}
h1,h2,h3,p,ul{margin:0}
h1{font-family:'Oswald',Arial,sans-serif;font-weight:600}
h2{font-family:'Oswald',Arial,sans-serif;font-size:72px;font-weight:600;line-height:1.08;margin-top:12px}
h3{font-size:34px;font-weight:700}
.lead{font-size:32px;line-height:1.4;color:#5E534A;margin-top:18px;max-width:1600px}
.dark .lead{color:#D8CFC4}.red .lead{color:#FBE9E3}
.foot{position:absolute;left:128px;bottom:40px;font-size:20px;color:#8F8378}
.dark .foot{color:#A89C90}.red .foot{color:#F6D9A0}
.grid{display:flex;gap:30px;margin-top:60px}
.card{flex:1;background:#fff;border:2px solid #E6DCCD;border-radius:18px;padding:30px 34px}
.dark .card{background:#2A241F;border-color:#4A413A}
.card h3{color:#B5361F;margin-bottom:12px}.dark .card h3{color:#D9A441}
.card p,.card li{font-size:31px;line-height:1.42}
.card ul{padding-left:28px}.card li{margin-bottom:6px}
.tan{background:#F1E7D8;border-color:#F1E7D8}
.num{display:inline-flex;align-items:center;justify-content:center;width:56px;height:56px;border-radius:50%;background:#B5361F;color:#fff;font-family:'Oswald';font-size:30px;font-weight:600;margin-bottom:14px}
.selo{display:inline-block;font-size:19px;font-weight:700;padding:4px 12px;border-radius:8px;margin-left:8px;vertical-align:middle}
.ok{background:#E3EDDD;color:#4E6B41}.obra{background:#FFF0D6;color:#8A6416}.pend{background:#E4EBF0;color:#47677B}
table.t{border-collapse:collapse;width:100%;margin-top:40px;font-size:28px}
table.t th{background:#1E1A17;color:#FAF6EF;text-align:left;padding:14px 18px;font-weight:700}
table.t td{border-bottom:2px solid #E6DCCD;padding:13px 18px;vertical-align:top;background:#fff}
.os{font-family:'Oswald',Arial,sans-serif}.dm{font-family:'DM Sans',Arial,sans-serif}
svg{display:block}
"""
OK, OBRA, PEND = '<span class="selo ok">pronto</span>', '<span class="selo obra">em construção</span>', '<span class="selo pend">depende da API</span>'


def fit(svgstr, maxw, maxh):
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svgstr)
    w, h = int(m.group(1)), int(m.group(2))
    k = min(maxw / w, maxh / h, 1.6)
    return f'<div style="width:{w * k:.1f}px;height:{h * k:.1f}px"><div style="width:{w}px;height:{h}px;transform:scale({k:.4f});transform-origin:0 0">{svgstr}</div></div>'


def slide(cls, tag, title, body, lead=None, rodape=''):
    s = f'<section class="s {cls}">'
    s += f'<p class="tag">{tag}</p>' if tag else ''
    s += f'<h2>{title}</h2>' if title else ''
    s += f'<p class="lead">{lead}</p>' if lead else ''
    s += body
    s += f'<p class="foot">{rodape}</p>' if rodape else ''
    return s + '</section>'


def cards(items, tan=False, style=''):
    out = f'<div class="grid" style="{style}">'
    for t, lines in items:
        out += f'<div class="card{" tan" if tan else ""}"><h3>{t}</h3>'
        out += f'<p>{lines}</p>' if isinstance(lines, str) else '<ul>' + ''.join(f'<li>{l}</li>' for l in lines) + '</ul>'
        out += '</div>'
    return out + '</div>'


def tabela(cab, linhas, larguras=None):
    s = '<table class="t"><tr>' + ''.join(f'<th{f" style=width:{larguras[i]}" if larguras else ""}>{c}</th>' for i, c in enumerate(cab)) + '</tr>'
    for l in linhas:
        s += '<tr>' + ''.join(f'<td>{c}</td>' for c in l) + '</tr>'
    return s + '</table>'


def tres_areas(cx, cy, r):
    """Disco em 3 setores: Produção, Vendas, Administrativo, com o login no centro."""
    setores = [(RED, 'PRODUÇÃO'), (GOLD, 'VENDAS'), (SLATE, 'ADMIN')]
    s = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#C98F2E"/>'
    for i, (cor, nome) in enumerate(setores):
        a0, a1 = math.radians(-90 + i * 120 + 1.5), math.radians(-90 + (i + 1) * 120 - 1.5)
        rr = r - 18
        x0, y0, x1, y1 = cx + rr * math.cos(a0), cy + rr * math.sin(a0), cx + rr * math.cos(a1), cy + rr * math.sin(a1)
        s += f'<path d="M {cx},{cy} L {x0:.1f},{y0:.1f} A {rr},{rr} 0 0 1 {x1:.1f},{y1:.1f} Z" fill="{cor}"/>'
        am = math.radians(-90 + i * 120 + 60)
        s += f'<text x="{cx + rr * 0.62 * math.cos(am):.1f}" y="{cy + rr * 0.62 * math.sin(am) + 12:.1f}" font-size="{int(r * 0.1)}" fill="#fff" font-weight="700" text-anchor="middle" class="os">{nome}</text>'
    s += f'<circle cx="{cx}" cy="{cy}" r="{r * 0.22}" fill="{DARK}" stroke="{GOLD}" stroke-width="5"/>'
    s += f'<text x="{cx}" y="{cy + r * 0.035:.1f}" font-size="{int(r * 0.085)}" fill="{GOLD}" font-weight="700" text-anchor="middle" class="os">1 LOGIN</text>'
    return s


def capa(titulo, subtitulo, rodape, tag):
    c = '<section class="s dark" style="padding:0">'
    c += f'<div style="position:absolute;left:1060px;top:150px">{svg(760, 760, tres_areas(380, 380, 360))}</div>'
    c += f'<div style="position:absolute;left:128px;top:128px;right:960px"><p class="tag">{tag}</p></div>'
    c += f'<div style="position:absolute;left:128px;top:290px;width:900px"><h1 style="font-size:140px;line-height:1.02;color:#FAF6EF">{titulo}</h1><p style="font-size:36px;line-height:1.4;color:#D8CFC4;margin-top:34px">{subtitulo}</p></div>'
    return c + f'<p class="foot" style="bottom:56px;font-size:24px">{rodape}</p></section>'


# ------------------------------------------------------------------ apresentação do sistema
def deck_sistema():
    R = f'Sistema Integrado da Pizzaria · Apresentação do sistema v2.0 · {DATA}'
    S = [capa('Três áreas, um login.', 'Produção, Vendas e Administrativo num só sistema, no PC da loja, com cada função vendo só a sua tela.',
              f'Versão 2.0 · {DATA}', 'Apresentação do sistema')]
    S.append(slide('cream', 'O princípio', 'Cada fato é registrado uma vez, onde acontece',
                   cards([('Um registro, vários usos', 'A venda nasce no balcão ou no canal. Dela saem a fila da cozinha, a baixa do estoque, o esperado do caixa e a receita do BI, sem digitar de novo.'),
                          ('Menu pela tarefa de quem usa', 'A cozinha usa tablet no pico; a recepção usa o balcão; o escritório usa listas longas. Por isso o sistema tem 3 áreas, e não 9 menus.'),
                          ('A regra vale no servidor', 'Esconder um botão não protege nada. Cada rota confere a permissão do perfil de quem chama.')]),
                   'A organização em 3 áreas foi decidida em 03/11/2026. Os 9 módulos do plano continuam no código; mudou a forma de usar.', R))
    S.append(slide('cream', 'As 3 áreas', 'O que cada área reúne',
                   cards([('🍕 Produção', ['Massa', 'Montagem', 'Forno', 'Acabamento e etiqueta', 'Despacho', 'Andamento e Motivos (gerência)']),
                          ('🧾 Vendas', ['Novo pedido e pedidos do dia', 'Caixa do dia e entregas', 'Acerto do entregador', 'Canais (Anota Ai; iFood depois)', 'Clientes e entregadores']),
                          ('🏢 Administrativo', ['Painel e BI', 'Cardápio e fichas técnicas', 'Estoque e Compras', 'Contas e fluxo de caixa', 'Custos, Imobilizado, RH', 'Usuários, Parâmetros, Auditoria'])]), None, R))
    S.append(slide('cream', 'Acesso por função', 'Um login pessoal, uma tela por função',
                   tabela(['Perfil', 'Entra em', 'Vê'], [
                       ['Massa', 'Produção', 'Só Massa'], ['Pizzaiolo', 'Produção', 'Só Montagem'],
                       ['Acabamento', 'Produção', 'Forno, Acabamento e Despacho, sem valores'],
                       ['Atendente', 'Vendas', 'Pedidos, Caixa e entregas, Clientes; consulta Cardápio e Entregadores'],
                       ['Gerente e subgerente', 'Última área', 'Tudo, com limites de aprovação (subgerente não aprova diferença de caixa nem RH)'],
                       ['Proprietário e administrador', 'Última área', 'Tudo, incluindo usuários, parâmetros, canais e folha']], ['22%', '16%', '62%']), None, R))
    S.append(slide('cream', 'Controle de acesso', 'Regras que o servidor garante',
                   cards([('Na cozinha', ['O pizzaiolo não vê o forno nem o andamento', 'O acabamento não vê o valor do pedido', 'Despachar exige o caixa do dia aberto']),
                          ('No balcão', ['Desconto acima do limite: gerente digita login e senha', 'Cancelar pedido pago: gerente confirma', 'Quem contou o caixa não aprova a própria diferença']),
                          ('No escritório', ['Ativar canal e editar o mapa: só administrador e proprietário', 'Salários e folha: só administrador e proprietário', 'Auditoria que o sistema não consegue apagar nem alterar'])]), None, R))
    S.append(slide('cream', 'Fluxo', 'Ciclo do pedido', '<div style="margin-top:20px">' + fit(fluxos_v2.ciclo_pedido(), 1664, 700) + '</div>', None, R))
    S.append(slide('cream', 'Vendas', 'Do pedido ao caixa fechado',
                   cards([('Pedido', ['Retirada ou entrega; cliente pelo telefone', 'Grande com 2 sabores: metade do preço de cada', 'Uma borda por pizza, adicionais com preço', 'Pagamento dividido; troco só no dinheiro; sem fiado']),
                          ('Caixa do dia', ['Um caixa por dia, uma gaveta', 'Sangria e suprimento com motivo', 'Acerto de todos os entregadores antes de contar', 'Contagem cega; diferença com justificativa e aprovação']),
                          ('Entregas', ['Despacho pelo acabamento, sem valores', 'Acerto: dinheiro recebido, valor das entregas e diária', 'Hora de entrega calculada nos pedidos do dia'])]), None, R))
    S.append(slide('cream', 'Canais', 'Anota Ai: o sistema chama a API',
                   tabela(['Parte', 'Como funciona', 'Situação'], [
                       ['Varredura', 'A cada 1 segundo, só com o canal ativo e configurado', OK],
                       ['Importar', 'Ler a fila, ver se a loja pode produzir, aceitar em até 15 min, criar o pedido', PEND],
                       ['Bloqueados', 'O que não passa nos critérios fica para a gerência: tentar de novo ou recusar', OK],
                       ['Aceitar sozinho', 'Flag do canal: canal ativo, loja aberta, caixa de hoje aberto, itens no mapa, nenhum sabor com venda fechada', OK + ' ' + PEND],
                       ['Avisos', '"Pronto" e "finalizado", com reenvio se a internet cair', OK + ' ' + PEND],
                       ['Finalizar entrega', 'No acerto do entregador', OK + ' ' + PEND],
                       ['Vendas fechadas', 'Ingrediente em falta fecha os sabores no sistema; a pausa no Anota Ai espera a API', OK + ' ' + PEND]], ['20%', '58%', '22%']),
                   None, R))
    S.append(slide('cream', 'Administrativo', 'O escritório no mesmo sistema',
                   cards([('Estoque e Compras', ['Baixa pela ficha técnica, sem travar a produção', 'Saldo pode ficar negativo para a falta aparecer', 'Lista de compras com cotação e aprovação']),
                          ('Contas e Custos', ['Fluxo de 30 dias, 7 em destaque', 'Conciliação com o extrato', 'CMV teórico e real, custo por produto']),
                          ('Imobilizado, RH e BI', ['Manutenção preventiva, preditiva e corretiva', 'Escala, ponto e banco de horas; Meus dados para todos', 'DRE, lucratividade por sabor, alertas'])]), None, R))
    S.append(slide('cream', 'Arquitetura', 'Servidor único no PC da loja', '<div style="margin-top:16px">' + fit(fluxos_v2.mapa_areas(), 1664, 620) + '</div>',
                   'FastAPI e PostgreSQL. 18 migrações, 101 tabelas, 250 rotas, testes automatizados e dois revisores em todo código.', R))
    S.append(slide('cream', 'Situação em ' + DATA, 'O que falta para o primeiro dia',
                   tabela(['Pendência', 'Depende de'], [
                       ['Token e documentação da API do Anota Ai', 'Chamado de Marlon ao Anota Ai'],
                       ['Teste da impressora térmica Bluetooth', 'Teste no tablet do acabamento'],
                       ['Dados de cardápio ainda faltando (abreviações, fichas de bordas, adicionais e bebidas, tempos)', 'Marlon'],
                       ['iFood', 'Acesso ao portal'],
                       ['Nuvem e HTTPS', 'Decisão de Marlon; hoje não é necessário'],
                       ['Backup fora da máquina', 'Adiado por decisão de Marlon']], ['60%', '40%']), None, R))
    S.append(slide('dark', 'Recomendação', 'Pedir o token do Anota Ai e testar a impressora agora',
                   '<p class="lead" style="margin-top:40px;max-width:1500px">São os dois pontos que ainda podem mudar o desenho: o formato do pedido do canal e o caminho de impressão. O resto do sistema já roda na loja sem eles.</p>',
                   None, R))
    return S


# ------------------------------------------------------------------ apresentação comercial
def deck_comercial():
    R = f'Sistema Integrado da Pizzaria · Apresentação comercial v2.0 · {DATA}'
    S = [capa('Do pedido ao resultado.', 'Cozinha, balcão, delivery, caixa, estoque e números do negócio num só sistema, feito para a rotina de uma pizzaria.',
              f'Versão 2.0 · {DATA}', 'Sistema de gestão para a pizzaria')]
    qs = ['Quanto custa cada pizza pela ficha técnica, e quanto foi o CMV do mês?', 'O caixa fechou certo, e se não fechou, onde está a diferença?', 'O que está acabando no estoque antes de faltar?',
          'Quanto sobra de cada pedido depois das taxas de cartão e de aplicativo?', 'Quanto tempo o cliente espera, e onde o pedido demora?', 'Quanto de massa e de insumo se perde, e por quê?']
    g = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:26px;margin-top:44px">'
    g += ''.join(f'<div class="card"><div class="num">{i + 1}</div><p style="font-size:30px;line-height:1.35;font-weight:500">{q}</p></div>' for i, q in enumerate(qs))
    S.append(slide('cream', 'O ponto de partida', 'Perguntas que todo dono de pizzaria faz', g + '</div>',
                   'O sistema responde com números que nascem da própria operação da loja.', R))
    S.append(slide('cream', 'A solução', 'Três áreas, um login, cada um na sua tela',
                   cards([('🍕 Cozinha', 'Tablets por função: massa, montagem e acabamento (com forno e despacho). Botões grandes, fila que se atualiza sozinha, pedido urgente na frente.'),
                          ('🧾 Balcão e delivery', 'Pedido rápido, caixa com contagem cega, entregas e acerto do entregador, pedidos do Anota Ai no mesmo fluxo.'),
                          ('🏢 Escritório', 'Cardápio, fichas técnicas, estoque, compras, contas, custos, equipamentos, equipe e BI.')]), None, R))
    S.append(slide('cream', 'Na cozinha', 'A unidade de trabalho é a pizza',
                   cards([('Menos erro', ['Cada pizza com sabores, borda, adicionais e observação', 'Etiqueta com cliente e número do pedido', 'Cada função vê só a sua etapa']),
                          ('Menos perda', ['Toda perda e todo retrocesso com motivo', 'Massa: saldo e quanto falta abrir, por tamanho', 'Refação entra na frente da fila']),
                          ('Mais previsão', ['Hora de entrega calculada pela fila', 'Capacidade do forno com aviso', 'Visão do andamento para a gerência'])]), None, R))
    S.append(slide('cream', 'No balcão', 'Venda certa e caixa que fecha',
                   cards([('Pedido', ['Cliente pelo telefone, cadastro na primeira compra', 'Meio a meio na Grande pela regra da casa', 'Pagamento dividido, sem fiado']),
                          ('Autorização na hora', ['Desconto acima do limite com login do gerente', 'Cancelamento de pedido pago com confirmação', 'Tudo registrado na auditoria']),
                          ('Caixa', ['Contagem cega: conta antes de ver o esperado', 'Diferença com justificativa e aprovação de outra pessoa', 'Acerto do entregador antes do fechamento'])]), None, R))
    S.append(slide('cream', 'Delivery', 'Anota Ai integrado ao fluxo da loja',
                   cards([('Pedido entra sozinho', 'Com a API liberada, o sistema consultará o Anota Ai a cada segundo e levará o pedido direto à fila da cozinha.'),
                          ('Aceite com critério', 'Aceitará sozinho só com o canal ativo, a loja aberta, o caixa de hoje aberto, todos os itens mapeados e nenhum sabor fechado. O resto vai para a gerência.'),
                          ('Cliente avisado', 'Receberá "pronto" quando o pedido sair para entrega ou ficar disponível para retirada, e "finalizado" no acerto do entregador ou na retirada.')]),
                   'Estrutura pronta e testada; a conexão aguarda o token e a documentação da API, que o Anota Ai libera por chamado.', R))
    S.append(slide('cream', 'Controle', 'Estoque que acompanha a venda',
                   cards([('Baixa automática', 'Cada pizza acabada baixa os insumos pela ficha técnica, com custo médio e lote. A produção nunca para por causa do estoque.'),
                          ('Alerta e ação', 'Ingrediente baixo, zerado ou negativo gera alerta. Sem ingrediente, a gerência fecha num toque os sabores que o usam; a pausa no delivery virá com a API.'),
                          ('Compra certa', 'Lista de necessidades pelo estoque mínimo e pela validade, cotação por fornecedor e aprovação acima de um valor.')]), None, R))
    S.append(slide('cream', 'Resultado', 'Os números do negócio sem planilha',
                   cards([('CMV', 'Teórico pela ficha e real pelo inventário, fechado no mês.'), ('DRE gerencial', 'Por competência, com série e exportação.'),
                          ('Lucratividade', 'Por sabor e por categoria, depois das taxas.'), ('Alertas', 'CMV acima da meta, estoque, diferença de caixa, atraso, manutenção.')]), None, R))
    S.append(slide('cream', 'Confiança', 'Seguro por desenho',
                   cards([('Login pessoal', 'Cada pessoa com a sua senha; bloqueio após tentativas erradas.'),
                          ('Acesso no servidor', 'Cada função só acessa o que é dela, mesmo que alguém tente pela rede.'),
                          ('Auditoria', 'Quem fez o quê e quando. O sistema não consegue apagar nem alterar.'),
                          ('Dados na loja', 'Roda no PC da loja, na rede local, com backup sob comando.')]), None, R))
    passos = ['Instalar no PC da loja e liberar a rede local', 'Criar os logins e preencher os parâmetros', 'Carregar cardápio, fichas e estoque inicial',
              'Dia de teste: pedido, cozinha, etiqueta e caixa', 'Ligar o Anota Ai quando o token chegar']
    g = '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:22px;margin-top:50px">'
    g += ''.join(f'<div class="card"><div class="num">{i + 1}</div><p style="font-size:27px;line-height:1.35">{p}</p></div>' for i, p in enumerate(passos))
    S.append(slide('cream', 'Implantação', 'Do PC da loja ao primeiro dia', g + '</div>', None, R))
    S.append(slide('red', 'Próximo passo', 'Um dia de teste na loja',
                   '<p class="lead" style="margin-top:40px;max-width:1500px">Instalado e carregado, um dia de teste com pedidos reais de balcão mostra a cozinha, a etiqueta e o fechamento de caixa funcionando antes de abrir o delivery.</p>', None, R))
    return S


def fluxogramas():
    pags = []
    for i, (t, sub, fn) in enumerate(fluxos_v2.ALL):
        pags.append(f'<section class="s cream" style="padding:52px 128px 0"><p class="tag">Fluxograma {i + 1} de {len(fluxos_v2.ALL)}</p>'
                    f'<h2 style="font-size:58px;margin-top:6px">{t}</h2><p style="font-size:27px;color:#5E534A;margin-top:6px">{sub}</p>{legenda()}'
                    f'<div style="margin-top:14px">{fit(fn(), 1664, 700)}</div><p class="foot">Sistema Integrado da Pizzaria · Fluxogramas v2.0 · {DATA}</p></section>')
    return pags


def pagina(titulo, secoes):
    return f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{titulo}</title>{FONTS}<style>{CSS}</style></head><body>' + ''.join(secoes) + '</body></html>'


if __name__ == '__main__':
    open('sistema.html', 'w', encoding='utf-8').write(pagina('Apresentação do Sistema', deck_sistema()))
    open('comercial.html', 'w', encoding='utf-8').write(pagina('Apresentação Comercial', deck_comercial()))
    open('fluxos.html', 'w', encoding='utf-8').write(pagina('Fluxogramas', fluxogramas()))
    print('ok')
