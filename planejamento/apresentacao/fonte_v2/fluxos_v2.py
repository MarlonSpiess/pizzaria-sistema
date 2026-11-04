from lib import *
from fluxo import Fluxo


def mapa_areas():
    f = Fluxo(3, 3, bw=420, bh=150)
    f.no('vend', 0, 1, 'VENDAS · pedidos, caixa e entregas, canais, clientes', 'ini', fs=23)
    f.no('prod', 2, 1, 'PRODUÇÃO · massa, montagem, forno, acabamento, despacho', 'ini', fs=23)
    f.no('adm', 1, 2, 'ADMINISTRATIVO · cardápio, fichas, estoque, compras, contas, custos, imobilizado, RH, BI', 'ini', fs=21)
    f.no('anota', 0, 0, 'Anota Ai (iFood no futuro)', 'pend', fs=22)
    f.no('srv', 2, 0, 'Servidor único no PC da loja · 1 login · acesso por função', 'passo', fs=21)
    f.no('banco', 1, 0, 'PostgreSQL · 101 tabelas · auditoria', 'passo', fs=21)
    f.seta('vend', 'prod', 'pizzas na fila', via=[(832, 330)], lx=832, ly=318)
    f.seta('prod', 'vend', 'acabado e despacho', via=[(832, 430)], lx=832, ly=452)
    f.seta('anota', 'vend', 'varredura de 1 s', tracejado=True, cor=SLATE)
    f.seta('vend', 'adm', 'vendas e caixa')
    f.seta('prod', 'adm', 'baixa pela ficha')
    f.seta('srv', 'banco', None)
    return f.svg()


def ciclo_pedido():
    f = Fluxo(6, 3, bw=230, bh=96)
    f.no('ini', 0, 0, 'Pedido no balcão ou importado do canal', 'ini')
    f.no('rec', 1, 0, 'Recebido (pago por completo)', 'passo')
    f.no('fila', 2, 0, 'Pizzas na lista, urgente na frente', 'passo')
    f.no('mont', 3, 0, 'Montagem (pizzaiolo)', 'passo')
    f.no('forno', 4, 0, 'Forno (acabamento)', 'passo')
    f.no('acab', 5, 0, 'Acabada e etiqueta', 'passo')
    f.no('ped', 5, 1, 'Pedido acabado', 'passo')
    f.no('tipo', 4, 1, 'Entrega?', 'dec', w=200, h=130)
    f.no('desp', 3, 1, 'Despacho: entregador (caixa aberto)', 'passo')
    f.no('saiu', 2, 1, 'Saiu para entrega · aviso "pronto"', 'passo')
    f.no('acerto', 1, 1, 'Acerto do entregador · "finalizado"', 'passo')
    f.no('ret', 4, 2, 'Pronto no balcão · aviso "pronto"', 'passo')
    f.no('cli', 2, 2, 'Cliente retira · "finalizado"', 'passo')
    f.no('fim', 0, 2, 'Caixa do dia', 'fim')
    for a, b in [('ini', 'rec'), ('rec', 'fila'), ('fila', 'mont'), ('mont', 'forno'), ('forno', 'acab'), ('acab', 'ped'), ('ped', 'tipo'),
                 ('desp', 'saiu'), ('saiu', 'acerto'), ('ret', 'cli')]:
        f.seta(a, b)
    f.seta('tipo', 'desp', 'sim')
    f.seta('tipo', 'ret', 'não')
    f.seta('acerto', 'fim', None)
    f.seta('cli', 'fim', None)
    return f.svg()


def importacao():
    f = Fluxo(6, 3, bw=228, bh=100, mx=160, my=90)
    f.no('var', 0, 0, 'Varredura a cada 1 segundo', 'ini')
    f.no('ativo', 1, 0, 'Canal ativo e configurado?', 'dec', w=220, h=150, fs=18)
    f.no('nada', 1, 1, 'Não consulta', 'passo')
    f.no('pend', 2, 0, 'Entrada na fila (pendente)', 'passo')
    f.no('imp', 3, 0, 'Importando: a varredura espera', 'passo')
    f.no('prod', 4, 0, 'Pode produzir? Itens no mapa, sabores abertos', 'dec', w=250, h=160, fs=17)
    f.no('bloq', 4, 1, 'Bloqueada: gerência decide', 'alerta')
    f.no('rec', 3, 2, 'Recusada', 'fim')
    f.no('auto', 5, 0, 'Aceitar sozinho? Loja aberta, caixa de hoje', 'dec', w=250, h=160, fs=17)
    f.no('ger', 5, 1, 'Gerência aceita', 'passo')
    f.no('aceita', 5, 2, 'Aceitar no Anota Ai (até 15 min)', 'pend')
    f.no('cria', 4, 2, 'Criar o pedido: importada', 'pend')
    xs = [f.pos(c, 0)[0] for c in range(6)]
    ys = [f.pos(0, r)[1] for r in range(3)]
    f.seta('var', 'ativo')
    f.seta('ativo', 'pend', 'sim')
    f.seta('ativo', 'nada', 'não')
    f.seta('pend', 'imp')
    f.seta('imp', 'prod')
    f.seta('prod', 'auto', 'sim')
    f.seta('prod', 'bloq', 'não')
    f.seta('bloq', 'rec', 'recusar')
    f.seta('bloq', 'pend', 'tentar de novo', via=[(xs[2], ys[1])], lx=xs[3], ly=ys[1])
    f.seta('auto', 'ger', 'não')
    f.seta('ger', 'aceita')
    f.seta('auto', 'aceita', 'sim', via=[(1652, ys[0]), (1652, ys[2])], lx=1630, ly=(ys[1] + ys[2]) / 2)
    f.seta('aceita', 'cria')
    return f.svg()


def producao():
    f = Fluxo(5, 3, bw=270, bh=100)
    f.no('m0', 0, 0, 'MASSA', 'ini', fs=24)
    f.no('m1', 1, 0, 'Lote de massa', 'passo')
    f.no('m2', 2, 0, 'Contagem de massa aberta', 'passo')
    f.no('m3', 3, 0, 'Perda de massa com motivo', 'alerta')
    f.no('m4', 4, 0, 'Saldo e "falta fazer" por tamanho', 'fim')
    f.no('p0', 0, 1, 'PIZZAIOLO', 'ini', fs=24)
    f.no('p1', 1, 1, 'Pegar a próxima pizza', 'passo')
    f.no('p2', 2, 1, 'Montar a pizza', 'passo')
    f.no('p3', 3, 1, 'Produzida: vai ao forno', 'passo')
    f.no('p4', 4, 1, 'Retroceder ou perder, com motivo', 'alerta')
    f.no('a0', 0, 2, 'ACABAMENTO', 'ini', fs=24)
    f.no('a1', 1, 2, 'Saiu do forno', 'passo')
    f.no('a2', 2, 2, 'Acabada e etiqueta', 'passo')
    f.no('a3', 3, 2, 'Pedido acabado e despacho', 'fim')
    f.no('a4', 4, 2, 'Refazer: pizza igual na frente da fila', 'alerta')
    for a, b in [('m0', 'm1'), ('m1', 'm2'), ('m2', 'm3'), ('m3', 'm4'), ('p0', 'p1'), ('p1', 'p2'), ('p2', 'p3'), ('p3', 'a1'),
                 ('a0', 'a1'), ('a1', 'a2'), ('a2', 'a3')]:
        f.seta(a, b)
    f.seta('p2', 'p4', 'problema', via=[(832, 222), (1519, 222)], lx=1175, ly=222)
    f.seta('a2', 'a4', 'saiu errada', via=[(832, 560), (1519, 560)], lx=1300, ly=560)
    return f.svg()


def caixa():
    f = Fluxo(5, 3, bw=270, bh=110)
    f.no('ab', 0, 0, 'Abrir o caixa com o fundo de troco', 'ini')
    f.no('dia', 1, 0, 'Vendas, sangrias e suprimentos', 'passo')
    f.no('ent', 2, 0, 'Acertar todos os entregadores', 'passo')
    f.no('cont', 3, 0, 'Contagem cega por forma de pagamento', 'passo')
    f.no('esp', 4, 0, 'Sistema mostra esperado e diferença', 'passo')
    f.no('tol', 4, 1, 'Acima da tolerância?', 'dec', w=240, h=150)
    f.no('just', 4, 2, 'Justificativa e aprovação de um gerente que não contou', 'alerta', fs=18)
    f.no('fech', 2, 2, 'Caixa fechado', 'fim')
    for a, b in [('ab', 'dia'), ('dia', 'ent'), ('ent', 'cont'), ('cont', 'esp'), ('esp', 'tol')]:
        f.seta(a, b)
    f.seta('tol', 'just', 'sim')
    f.seta('just', 'fech')
    f.seta('tol', 'fech', 'não')
    return f.svg()


def estoque():
    f = Fluxo(5, 2, bw=270, bh=110, my=90)
    f.no('ac', 0, 0, 'Pizza acabada ou pedido acabado', 'ini')
    f.no('bx', 1, 0, 'Baixa pela ficha técnica (nunca trava)', 'passo')
    f.no('neg', 2, 0, 'Saldo pode ficar negativo', 'passo')
    f.no('al', 3, 0, 'Alerta: baixo, zerado ou negativo', 'passo')
    f.no('dz', 4, 0, 'Zerado ou negativo?', 'dec', w=230, h=150)
    f.no('fs', 4, 1, 'Fechar os sabores que usam o ingrediente', 'passo')
    f.no('api', 3, 1, 'Pausar no Anota Ai', 'pend')
    f.no('rep', 2, 1, 'Repor ou ajustar o estoque', 'passo')
    f.no('ab', 1, 1, 'Reabrir os sabores', 'fim')
    for a, b in [('ac', 'bx'), ('bx', 'neg'), ('neg', 'al'), ('al', 'dz'), ('fs', 'api'), ('api', 'rep'), ('rep', 'ab')]:
        f.seta(a, b)
    f.seta('dz', 'fs', 'sim')
    f.seta('dz', 'rep', 'não: só baixo')
    return f.svg()


ALL = [
    ('As 3 áreas e o que passa entre elas', 'Um login, um servidor, acesso conferido por função. O Anota Ai é consultado pelo sistema.', mapa_areas),
    ('Ciclo do pedido', 'Da venda ao caixa, com os avisos ao Anota Ai em cada passo.', ciclo_pedido),
    ('Importação de pedidos do Anota Ai', 'Estrutura pronta; aceitar e criar o pedido dependem da documentação da API.', importacao),
    ('Produção: uma tela por função', 'A unidade de trabalho é a pizza. Cada função só vê a sua etapa.', producao),
    ('Caixa do dia', 'Um caixa por dia, uma gaveta, contagem cega.', caixa),
    ('Estoque, alertas e vendas fechadas', 'Decisões de 04/11/2026: o estoque pode ficar negativo e a falta fecha a venda dos sabores.', estoque),
]
