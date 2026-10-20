import sys
from lib import *
import flows

FONTS = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Oswald:wght@400..700&family=DM+Sans:wght@400..700&display=swap">'
CSS = """
@page{size:1920px 1080px;margin:0}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:'DM Sans',Arial,sans-serif}
section.s{position:relative;width:1920px;height:1080px;overflow:hidden;page-break-after:always;break-after:page;padding:88px 128px 0}
.cream{background:#FAF6EF;color:#2B2420}.dark{background:#1E1A17;color:#FAF6EF}.red{background:#B5361F;color:#FAF6EF}
.tag{font-size:24px;font-weight:700;letter-spacing:4px;text-transform:uppercase;color:#B5361F}
.dark .tag{color:#D9A441}.red .tag{color:#F6D9A0}
h1,h2,h3,p,ul{margin:0}
h1{font-family:'Oswald',Arial,sans-serif;font-weight:600}
h2{font-family:'Oswald',Arial,sans-serif;font-size:78px;font-weight:600;line-height:1.08;margin-top:14px}
h3{font-size:30px;font-weight:700}
.lead{font-size:34px;line-height:1.4;color:#5E534A;margin-top:20px;max-width:1500px}
.dark .lead{color:#D8CFC4}.red .lead{color:#FBE9E3}
.foot{position:absolute;left:128px;bottom:44px;font-size:20px;color:#8F8378}
.dark .foot{color:#A89C90}.red .foot{color:#F6D9A0}
.grid{display:flex;gap:28px;margin-top:44px}
.card{flex:1;background:#fff;border:2px solid #E6DCCD;border-radius:18px;padding:32px 36px}
.dark .card{background:#2A241F;border-color:#4A413A}
.card h3{color:#B5361F;margin-bottom:14px}.dark .card h3{color:#D9A441}
.card p,.card li{font-size:27px;line-height:1.42}
.card ul{padding-left:30px}.card li{margin-bottom:6px}
.tan{background:#F1E7D8;border-color:#F1E7D8}
.num{display:inline-flex;align-items:center;justify-content:center;width:56px;height:56px;border-radius:50%;background:#B5361F;color:#fff;font-family:'Oswald';font-size:30px;font-weight:600;margin-bottom:14px}
.big{font-family:'Oswald';font-size:56px;font-weight:600;color:#B5361F;line-height:1}
.dark .big{color:#D9A441}
.os{font-family:'Oswald',Arial,sans-serif}.dm{font-family:'DM Sans',Arial,sans-serif}
svg{display:block}
"""

import re


def fit(svgstr, maxw, maxh):
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svgstr)
    w, h = int(m.group(1)), int(m.group(2))
    k = min(maxw / w, maxh / h, 1.6)
    return f'<div style="width:{w * k:.1f}px;height:{h * k:.1f}px"><div style="width:{w}px;height:{h}px;transform:scale({k:.4f});transform-origin:0 0">{svgstr}</div></div>'


TOTAL = [0]


def slide(cls, tag, title, body, lead=None, extra='', n=None):
    s = f'<section class="s {cls}">'
    if tag:
        s += f'<p class="tag">{tag}</p>'
    if title:
        s += f'<h2>{title}</h2>'
    if lead:
        s += f'<p class="lead">{lead}</p>'
    s += body + extra
    s += f'<p class="foot">Sistema Integrado da Pizzaria · {n}</p>' if n else ''
    s += '</section>'
    return s


def cards(items, cols=None, tan=False):
    out = '<div class="grid">'
    for t, lines in items:
        c = 'card tan' if tan else 'card'
        out += f'<div class="{c}"><h3>{t}</h3>'
        if isinstance(lines, str):
            out += f'<p>{lines}</p>'
        else:
            out += '<ul>' + ''.join(f'<li>{l}</li>' for l in lines) + '</ul>'
        out += '</div>'
    return out + '</div>'


def module_slide(n, num, tag, title, lead, left_title, left, right):
    body = '<div class="grid">'
    body += f'<div class="card" style="flex:1.4"><h3>{left_title}</h3><ul>' + ''.join(f'<li>{l}</li>' for l in left) + '</ul></div>'
    body += '<div style="flex:1;display:flex;flex-direction:column;gap:24px">'
    for t, txt, dark in right:
        if dark:
            body += f'<div class="card" style="background:#1E1A17;border-color:#1E1A17"><h3 style="color:#D9A441">{t}</h3><p style="color:#FAF6EF">{txt}</p></div>'
        else:
            body += f'<div class="card tan"><h3 style="color:#1E1A17">{t}</h3><p>{txt}</p></div>'
    body += '</div></div>'
    return slide('cream', tag, title, body, lead, n=n)


def build_deck():
    S = []
    n = [0]

    def nx():
        n[0] += 1
        return n[0]

    # 1 capa
    cover = f'<section class="s dark" style="padding:0">'
    cover += f'<div style="position:absolute;left:1040px;top:120px">{svg(780, 780, pizza(390, 390, 370))}</div>'
    cover += '<div style="position:absolute;left:128px;top:128px;right:960px"><p class="tag">Sistema integrado de gestão para pizzarias</p></div>'
    cover += '<div style="position:absolute;left:128px;top:300px;width:880px"><h1 style="font-size:150px;line-height:1.02;color:#FAF6EF">Do pedido ao resultado.</h1><p style="font-size:38px;line-height:1.4;color:#D8CFC4;margin-top:36px">Vendas, produção, caixa, estoque, custos, pessoas e BI em um só lugar, desenhado para a rotina de uma pizzaria.</p></div>'
    cover += '<p class="foot" style="left:128px;bottom:56px;font-size:24px;color:#A89C90">Planejamento completo aprovado em 20/10/2026 · Outubro de 2026</p></section>'
    nx()
    S.append(cover)

    # 2 perguntas
    qs = ['Quanto custou, de fato, cada pizza que saiu hoje?', 'O caixa fechou certo, e se não fechou, onde está a diferença?', 'O que está acabando no estoque antes de faltar?',
          'Quanto sobra de cada pedido depois das taxas de cartão e de aplicativo?', 'Quanto tempo o cliente espera, e onde o pedido demora?', 'Quanto de massa e de insumo se perde por semana, e por quê?']
    g = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:28px;margin-top:48px">'
    for i, q in enumerate(qs):
        g += f'<div class="card"><div class="num">{i + 1}</div><p style="font-size:31px;line-height:1.35;font-weight:500">{q}</p></div>'
    g += '</div>'
    S.append(slide('cream', 'O ponto de partida', 'Perguntas que todo dono de pizzaria faz', g, 'O sistema foi desenhado para responder cada uma delas com números que ninguém precisou digitar duas vezes.', n=nx()))

    # 3 ideia central
    hub = ''
    cxs = [(960, 280, 'Produção', 'a pizza entra na fila'), (350, 280, 'Estoque', 'baixa pela receita'), (350, 520, 'Caixa', 'valor esperado'), (960, 520, 'Contas', 'recebível'), (655, 590, 'BI', 'receita do dia')]
    sv = ''
    for (x, y, t, s2) in [(560, 40, 'Produção', 'a pizza entra na fila'), (130, 130, 'Estoque', 'baixa pelos insumos'), (130, 400, 'Caixa', 'valor esperado'), (1000, 130, 'Contas', 'recebível'), (1000, 400, 'BI', 'receita do dia')]:
        sv += title_box(x, y, 300, 96, t, s2, RED if t in ('Produção', 'Estoque', 'Caixa') else (SLATE if t == 'Contas' else GREEN), fs=26, fs2=19)
    sv += f'<circle cx="650" cy="290" r="110" fill="{DARK}"/>'
    sv += text_block(650, 270, 'VENDA', 36, GOLD, 700, 200, family='os')
    sv += text_block(650, 318, 'registrada uma vez', 19, '#D8CFC4', 500, 200)
    ar = ''
    ar += arrow(650, 180, 710, 136, INK) if False else ''
    ar += arrow(600, 200, 640, 140, INK) if False else ''
    ar += arrow(700, 196, 700, 140, INK)
    ar += arrow(560, 250, 430, 190, INK)
    ar += arrow(545, 330, 430, 430, INK)
    ar += arrow(740, 250, 1000, 190, INK)
    ar += arrow(740, 335, 1000, 440, INK)
    S.append(slide('cream', 'A ideia central', 'Cada fato é registrado uma vez, onde acontece',
                   f'<div style="display:flex;gap:56px;margin-top:20px"><div style="flex:0 0 1300px">{svg(1300, 520, sv + ar)}</div><div style="flex:1;font-size:27px;line-height:1.4;color:#5E534A;padding-top:50px"><p><b style="color:#B5361F">Sem redigitar.</b> Uma venda vira fila de produção, baixa de estoque, valor esperado no caixa, recebível e receita do dia.</p><p style="margin-top:22px"><b style="color:#B5361F">Sem depender.</b> Cada módulo também funciona sozinho: o dado entra de forma automática ou à mão.</p></div></div>',
                   n=nx()))

    # 4 nove módulos
    legend = ''
    mods = [('1', 'RH', SLATE), ('2', 'Imobilizado', SLATE), ('3', 'Estoques e Compras', RED), ('4', 'Contas e Fluxo de Caixa', SLATE), ('5', 'Custos', GREEN), ('6', 'Vendas', RED), ('7', 'Produção', RED), ('8', 'Fechamento de Caixa', RED), ('9', 'BI', GREEN)]
    legend = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px 40px;margin-top:6px;font-size:30px">'
    for nn, t, c in mods:
        legend += f'<div style="display:flex;align-items:center;gap:16px"><span style="width:46px;height:46px;border-radius:50%;background:{c};color:#fff;display:inline-flex;align-items:center;justify-content:center;font-family:Oswald;font-size:26px">{nn}</span>{t}</div>'
    legend += '</div><p style="font-size:24px;color:#A89C90;margin-top:26px">No centro, o Núcleo: usuários, perfis, parâmetros, cadastros e auditoria.</p>'
    S.append(slide('dark', 'Visão geral', 'Nove módulos, uma só pizza', '', None,
                   extra=f'<div style="position:absolute;left:128px;top:300px;width:700px"><p class="lead" style="margin-top:0;margin-bottom:34px">Cada fatia é um módulo. Juntas, formam a gestão completa da pizzaria.</p>{legend}</div><div style="position:absolute;left:960px;top:140px">{svg(820, 820, pizza(410, 410, 390))}</div>',
                   n=nx()))

    # 5 jornada resumida
    steps = [('Pedido', 'balcão ou Anota Aí'), ('Massa', 'duas fases'), ('Pizzaiolo', 'monta a próxima'), ('Forno', 'esteira, 2 min'), ('Acabamento', 'etiqueta por pizza'), ('Entrega', 'ou retirada'), ('Caixa', 'fecha o dia')]
    sv = ''
    for i, (t, s2) in enumerate(steps):
        x = i * 232
        col = SLATE if t == 'Caixa' else RED
        sv += f'<path d="M {x},0 L {x + 200},0 L {x + 232},70 L {x + 200},140 L {x},140 L {x + 32},70 Z" fill="{col if i % 2 == 0 else GOLD}"/>'
        txtc = '#fff' if i % 2 == 0 or col == SLATE else DARK
        sv += text_block(x + 118, 52, t, 28, txtc if col != SLATE else '#fff', 700, 150, family='os')
        sv += text_block(x + 118, 98, s2, 18, txtc, 500, 150)
    S.append(slide('dark', 'A jornada de um pedido', 'Da chamada do cliente ao fechamento do dia',
                   f'<div style="margin-top:56px">{svg(1624, 140, sv)}</div>' + cards([('O pedido nunca se perde', ['Entra pelo balcão ou pelo Anota Aí com os mesmos dados.', 'Pedido urgente vai ao topo da fila.']), ('Cada função vê só o seu', ['Massa, pizzaiolo e acabamento têm tablet e login pessoal.', 'A unidade de trabalho é a pizza.']), ('Tudo deixa rastro', ['Quem fez cada etapa, e quando.', 'Tempo por etapa vira indicador.'])]),
                   n=nx()))

    # 6 vendas
    S.append(module_slide(nx(), 6, 'Módulo Vendas', 'Vender em qualquer canal, digitar uma vez', 'Balcão e Anota Aí no mesmo lugar, com um cardápio único.', 'O que o módulo faz',
                          ['Cardápio único: pizzas, calzones e bebidas, com preço por categoria e tamanho', 'Grande com dois sabores soma metade do preço de cada sabor', 'Borda e extras são adicionais com preço', 'Pagamento dividido: dinheiro, Pix, crédito e débito, com troco', 'Desconto e acréscimo com motivo obrigatório e limite por perfil', 'Cliente cadastrado na primeira compra, com aviso por WhatsApp em um clique'],
                          [('Anota Aí', 'Cardápio enviado daqui; pedidos recebidos por adaptador, assim que o acesso for liberado.', False), ('Entrega', 'Taxa digitada pelo atendente; entregador terceiro, pago por entrega e diária.', True)]))

    # 7 produção
    roles = [('Massa', ['Fase 1: bater, bolear e crescer', 'Fase 2: abrir massas e massas com borda', 'Registra perda com motivo']), ('Pizzaiolo', ['Recebe sempre a próxima pizza', 'Falta insumo? Retrocede uma posição, com motivo', 'Marca produzida: vai ao forno']), ('Acabamento', ['Vê o que está no forno', 'Imprime etiqueta por pizza: cliente, número e sabor', 'Marca o pedido acabado, à mão'])]
    S.append(slide('cream', 'Módulo Produção', 'Cozinha organizada por tablet', cards(roles) + '<p style="font-size:28px;color:#5E534A;margin-top:34px;max-width:1600px">Pedido urgente reorganiza a fila, menos o que já está em produção. A entrega estimada considera as pizzas na frente e os pizzaiolos ativos.</p>', 'Cada função enxerga só o que precisa, com login pessoal.', n=nx()))

    # 8 caixa
    S.append(module_slide(nx(), 8, 'Módulo Fechamento de Caixa', 'Caixa sem surpresa', 'O sistema sabe quanto deveria ter; o operador conta sem ver.', 'Como o dia fecha',
                          ['Abertura com fundo de troco e responsável registrado', 'Sangrias e suprimentos com motivo e autorização', 'Contagem cega: o operador informa o que contou antes de ver o esperado', 'Diferença acima da tolerância exige justificativa e aprovação do gerente', 'Acerto do entregador por pedido, no fim do turno', 'Pedidos sem cupom fiscal informado aparecem em lista'],
                          [('Relatório do dia', 'Totais por forma de pagamento, sangrias, cancelamentos e descontos.', False), ('Segue adiante', 'Valores realizados vão a Contas; quebras de caixa vão ao BI.', True)]))

    # 9 estoque
    S.append(module_slide(nx(), 3, 'Módulo Estoques e Compras', 'Saber o que existe antes de faltar', 'Saldo real por local, baixa pela receita e compra com registro.', 'O que o módulo controla',
                          ['Locais: freezer, câmara fria e estoque seco', 'Baixa automática pela ficha técnica de cada pizza vendida', 'Inventário: itens críticos todo dia, completo todo mês, com ajuste e motivo', 'Lote e validade em todos os insumos de pizza e calzone', 'Pedido de compra por fornecedor, com aprovação acima de um valor', 'Custo médio móvel, com os últimos 3 preços à vista'],
                          [('Alerta de mínimo', 'Sugestão pelo consumo médio, com aprovação do gestor.', False), ('Material de consumo', 'Limpeza e descartáveis entram como classe de item.', True)]))

    # 10 contas
    S.append(module_slide(nx(), 4, 'Módulo Contas e Fluxo de Caixa', 'Quanto entra, quanto sai, e quando', 'Compromissos e recebíveis num só calendário.', 'O que o módulo organiza',
                          ['Contas bancárias por loja, cada loja uma empresa', 'Despesas recorrentes por tipo: aluguel, energia, internet e outras', 'Repasse por canal e por maquininha, com taxa e prazo', 'Entregador como conta a pagar, baixada no acerto do dia', 'Forma de pagamento registrada em cada baixa', 'Fluxo de 30 dias, com 7 em destaque'],
                          [('Taxas à vista', 'A conciliação mostra o que o cartão e o aplicativo cobram de verdade.', False), ('Separação', 'Retirada do proprietário fica fora das despesas.', True)]))

    # 11 custos
    S.append(module_slide(nx(), 5, 'Módulo Custos', 'Quanto custa cada pizza, e quanto sobra', 'Margem por produto, sabor e canal, com sugestão de preço.', 'O que o módulo calcula',
                          ['Custo de cada produto pela ficha técnica, com fator de correção', 'CMV teórico contra CMV real, por mês', 'Custos fixos e variáveis, marcados por tipo de despesa', 'Embalagem e custo da entrega entram onde pertencem', 'Preço sugerido por margem desejada; a decisão é sempre do dono', 'Ponto de equilíbrio'],
                          [('Sem meta imposta', 'O sistema começa sem meta e propõe depois, a partir do histórico da loja.', False), ('Margem por canal', 'Balcão e aplicativo têm margens diferentes por causa das taxas.', True)]))

    # 12 manutenção
    S.append(module_slide(nx(), 2, 'Módulo Imobilizado', 'Equipamento parado custa pedido', 'Bens controlados e manutenção completa, do aviso ao custo.', 'O que o módulo cobre',
                          ['Bens cadastrados um a um, com depreciação fiscal ou por vida útil', 'Manutenção preventiva por bem, com alerta antes do vencimento', 'Preditiva: leituras da inspeção avisam antes da quebra', 'Corretiva: registro da parada e da volta', 'Ordem de serviço com peças, horas e custo', 'Garantia e seguro com alerta de vencimento'],
                          [('Forno parado', 'Avisa a produção e registra o tempo perdido.', False), ('Pronto para crescer', 'O cadastro aceita veículos próprios no futuro.', True)]))

    # 13 pessoas
    S.append(module_slide(nx(), 1, 'Módulo RH', 'Pessoas, escala e custo, sem substituir o contador', 'Gestão gerencial; a folha legal continua com o contador.', 'O que o módulo organiza',
                          ['Cadastro um a um, com contrato por tipo', 'Escala parametrizável: parte de 6x1 ou 5x2 e acompanha mudanças de legislação', 'Ponto lançado pelo gerente, relógio biométrico no futuro', 'Horas extras com aprovação e limite', 'Benefícios, prévia de folha e treinamentos com validade', 'Salários visíveis só ao administrador e ao proprietário'],
                          [('Cada um vê o seu', 'O funcionário consulta a própria escala e o próprio ponto.', False), ('Liga ao acesso', 'Quem sai da equipe perde o login.', True)]))

    # 14 BI
    tiles = ''
    for t in ['Vendas de ontem', 'CMV do mês', 'Saldo de caixa']:
        tiles += f'<div class="card" style="text-align:left"><p style="font-size:24px;color:#8F8378">{t}</p><p class="big" style="margin-top:18px">R$ ---</p></div>'
    S.append(slide('cream', 'Módulo BI', 'A manhã do dono começa com três números',
                   f'<div class="grid" style="margin-top:36px">{tiles}</div>' + cards([('Todos os dias', ['Pedidos, ticket médio, atrasos, perdas e diferença de caixa', 'Atualiza sozinho a cada poucos minutos']), ('Todo mês', ['DRE por competência', 'Lucratividade por sabor e por categoria', 'CMV teórico contra real']), ('Alertas na tela', ['CMV acima da meta, estoque mínimo, diferença de caixa, pedido atrasado, manutenção vencendo'])]) + '<p style="font-size:22px;color:#8F8378;margin-top:18px">Estrutura do painel: os valores virão dos dados da loja.</p>',
                   n=nx()))

    # 15 mapa
    S.append(slide('cream', 'O sistema por inteiro', 'Mapa de integrações', f'<div style="margin-top:4px">{fit(flows.flow_map(), 1664, 760)}</div>', None, n=nx()))
    # 16 jornada completa
    S.append(slide('cream', 'O sistema por inteiro', 'Jornada completa de um pedido', f'<div style="margin-top:4px">{fit(flows.flow_order(), 1664, 760)}</div>', None, n=nx()))

    # 17 controle
    S.append(slide('dark', 'Controle e segurança', 'Quem fez, quando e por quê', cards([('Acesso', ['Login pessoal e intransferível', 'Perfis: administrador, proprietário, gerente, subgerente, atendente, massa, pizzaiolo e acabamento', 'Tudo que não é permitido é negado']), ('Rastro', ['Auditoria que só aceita inserção', 'Desconto, cancelamento, estorno e diferença de caixa exigem motivo', 'Exclusão lógica: o histórico não some']), ('Dados', ['Senhas protegidas e segredos fora do código', 'Salários só para quem tem permissão', 'Backup diário fora da máquina'])]), 'Controle que protege a loja sem atrapalhar a operação.', n=nx()))

    # 18 configurável
    pars = ['Limite de desconto por perfil', 'Valor por entrega e diária do entregador', 'Preço e limite do funcionário', 'Tempo e capacidade do forno', 'Fundo de troco e tolerância de caixa', 'Locais de estoque e fator de correção', 'Taxa e prazo por maquininha e canal', 'Tipos de despesa, fixas ou variáveis', 'Tipos de escala e de contrato', 'Metas e alertas do BI']
    chips = '<div style="display:flex;flex-wrap:wrap;gap:16px;margin-top:44px">' + ''.join(f'<span style="background:#fff;border:2px solid #E6DCCD;border-radius:40px;padding:16px 30px;font-size:28px;font-weight:500">{p}</span>' for p in pars) + '</div>'
    S.append(slide('cream', 'Feito para a sua pizzaria', 'Configurável, não engessado', chips + '<p style="font-size:30px;color:#5E534A;margin-top:40px;max-width:1500px">As regras ficam nos parâmetros da loja, e não escritas no código. Mudou a regra, muda o parâmetro.</p>', 'Cada loja define os seus números.', n=nx()))

    # 19 cresce
    fut = [('Anota Aí', 'Pedidos e cardápio por adaptador, quando o acesso for liberado.'), ('Outros canais', 'iFood e similares entram como um canal a mais.'), ('Cupom fiscal', 'Hoje digitado em software de terceiro; emissão pelo sistema é projeto futuro.'), ('Nuvem e várias lojas', 'Beta local, espelho na nuvem depois, e um aplicativo central para ler todas as lojas.'), ('Mais automação', 'Relógio biométrico, importação de nota, de extrato e envio de WhatsApp.')]
    g = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:26px;margin-top:44px">'
    for t, d in fut:
        g += f'<div class="card"><h3>{t}</h3><p>{d}</p></div>'
    g += '<div class="card" style="background:#1E1A17;border-color:#1E1A17"><h3 style="color:#D9A441">Por isso desde já</h3><p style="color:#FAF6EF">Identificador da loja em todo registro e esquema estável.</p></div></div>'
    S.append(slide('cream', 'Pronto para crescer', 'O que já nasce preparado', g, 'Itens marcados como futuros estão previstos, não prontos.', n=nx()))

    # 20 tecnologia
    S.append(slide('dark', 'Tecnologia e dados', 'Dados na sua loja, tecnologia aberta', cards([('Onde roda', ['Servidor local na loja, em um dos PCs da recepção', 'Tablets e PCs acessam pela rede da loja, pelo navegador', 'Segundo PC apto a assumir']), ('Como foi feito', ['Python com FastAPI', 'Banco PostgreSQL, o mesmo no local e na nuvem', 'Interface em HTML']), ('Para a nuvem', ['Espelho previsto em Fly.io, depois', 'Esquema estável e legível', 'Backup diário fora da máquina'])]), 'Pensado para rodar bem em casa e migrar sem retrabalho.', n=nx()))

    # 21 transparência
    S.append(slide('cream', 'Transparência', 'O que o sistema não faz', cards([('Fora do beta', ['Emissão de cupom fiscal', 'Folha legal e eSocial, que ficam com o contador', 'Ser o registrador oficial de ponto', 'Contabilidade societária completa']), ('Onde estamos', ['Planejamento dos nove módulos aprovado em 20/10/2026', 'Nenhum módulo está pronto para uso ainda', 'Os números do painel só existem com dados reais da loja'])], tan=False), 'Honestidade sobre os limites faz parte do projeto.', n=nx()))

    # 22 roteiro
    et = [('0', 'Núcleo', 'Login, perfis, parâmetros, cadastros'), ('1', 'Vendas, Produção e Caixa', 'O pedido de ponta a ponta'), ('2', 'Estoques e Compras', 'Baixa automática'), ('3', 'Contas e Fluxo de Caixa', 'Pagar, receber, projetar'), ('4', 'Custos', 'CMV e margem'), ('5', 'Imobilizado e RH', 'Bens, manutenção e pessoas'), ('6', 'BI', 'Visão consolidada')]
    sv = ''
    for i, (nn, t, d) in enumerate(et):
        x = i * 236
        sv += f'<circle cx="{x + 60}" cy="50" r="40" fill="{RED if i < 2 else (SLATE if i in (2, 3, 5) else GREEN)}"/><text x="{x + 60}" y="64" font-size="36" fill="#fff" font-weight="600" text-anchor="middle" class="os">{nn}</text>'
        if i < len(et) - 1:
            sv += f'<line x1="{x + 104}" y1="50" x2="{x + 192}" y2="50" stroke="{GOLD}" stroke-width="4"/>'
        sv += text_block(x + 60, 150, t, 22, INK, 700, 210)
        sv += text_block(x + 60, 220, d, 18, GREY, 500, 210)
    S.append(slide('cream', 'Próximos passos', 'Roteiro de construção', f'<div style="margin-top:56px">{svg(1664, 270, sv)}</div><div class="card tan" style="margin-top:20px"><p style="font-size:30px">Primeiro incremento sugerido: login, parâmetros, cardápio, pedido de balcão com pagamento, fila de produção por função e fechamento do dia.</p></div>', 'A ordem segue o que os outros módulos consomem.', n=nx()))

    # 23 fecho
    fim = '<section class="s red" style="padding:0"><div style="position:absolute;left:128px;top:250px;width:1100px"><h1 style="font-size:116px;line-height:1.06;color:#FAF6EF">Uma pizzaria.<br>Um sistema.<br>Uma visão clara.</h1><p style="font-size:38px;line-height:1.4;color:#FBE9E3;margin-top:44px">Vamos conversar sobre a sua pizzaria?</p></div>'
    fim += f'<div style="position:absolute;left:1260px;top:240px">{svg(560, 560, pizza(280, 280, 270, bg=RED))}</div>'
    fim += '<p class="foot" style="font-size:24px">Sistema Integrado da Pizzaria · Outubro de 2026</p></section>'
    nx()
    S.append(fim)
    return S


def build_flow_pages():
    pages = []
    for i, (t, sub, fn) in enumerate(flows.ALL):
        s = f'<section class="s cream" style="padding:56px 128px 0"><p class="tag">Fluxograma {i + 1} de {len(flows.ALL)}</p><h2 style="font-size:60px;margin-top:6px">{t}</h2><p style="font-size:28px;color:#5E534A;margin-top:6px">{sub}</p><div style="margin-top:20px">{fit(fn(), 1664, 760)}</div><p class="foot">Sistema Integrado da Pizzaria · Plano Macro v1.0</p></section>'
        pages.append(s)
    return pages


def page(title, sections):
    return f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{title}</title>{FONTS}<style>{CSS}</style></head><body>' + ''.join(sections) + '</body></html>'


if __name__ == '__main__':
    open('deck.html', 'w', encoding='utf-8').write(page('Sistema Integrado da Pizzaria', build_deck()))
    open('flow.html', 'w', encoding='utf-8').write(page('Fluxogramas do Sistema Integrado da Pizzaria', build_flow_pages()))
    print('ok')
