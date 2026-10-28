"use strict";
// Texto de usuário só entra na tela como nó de texto (nunca como HTML).
const raiz = document.getElementById("raiz");
const estado = { token: null, eu: null, aba: "painel" };
try { estado.token = sessionStorage.getItem("pz-token"); } catch (e) { /* sem armazenamento: pede login */ }

function h(tag, attrs, ...filhos) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "onclick" || k === "onsubmit" || k === "onchange") el[k] = v;
    else if (k === "class") el.className = v;
    else if (v !== false && v != null) el.setAttribute(k, v);
  }
  for (const f of filhos.flat()) if (f != null && f !== false) el.append(f instanceof Node ? f : document.createTextNode(String(f)));
  return el;
}

async function api(metodo, caminho, corpo) {
  const opcoes = { method: metodo, headers: {} };
  if (estado.token) opcoes.headers.Authorization = "Bearer " + estado.token;
  if (corpo !== undefined) { opcoes.headers["Content-Type"] = "application/json"; opcoes.body = JSON.stringify(corpo); }
  let r;
  try { r = await fetch("/api" + caminho, opcoes); }
  catch (e) { throw new Error("Sem conexão com o servidor da loja."); }
  let dados = null;
  try { dados = await r.json(); } catch (e) { /* sem corpo */ }
  if (r.status === 401 && estado.token && caminho !== "/auth/login") { sair(false); throw new Error("Sessão expirada. Entre de novo."); }
  if (!r.ok) throw new Error((dados && dados.detail) || "Erro " + r.status);
  return dados;
}

function sair(chamarApi = true) {
  if (chamarApi && estado.token) api("POST", "/auth/logout").catch(() => {});
  estado.token = null; estado.eu = null; estado.rascunho = null;
  try { sessionStorage.removeItem("pz-token"); } catch (e) { /* ok */ }
  desenhar();
}

function aviso(tipo, texto) { return h("div", { class: "aviso " + tipo, role: "alert" }, texto); }
const fmtData = (iso) => iso ? new Date(iso).toLocaleString("pt-BR") : "";

function telaLogin(msg) {
  const u = h("input", { id: "u", autocomplete: "username", autocapitalize: "none", required: "" });
  const s = h("input", { id: "s", type: "password", autocomplete: "current-password", required: "" });
  const erro = h("div");
  const form = h("form", { class: "cartao", onsubmit: async (ev) => {
    ev.preventDefault(); erro.replaceChildren();
    try {
      const r = await api("POST", "/auth/login", { usuario: u.value, senha: s.value });
      estado.token = r.token; estado.eu = r;
      try { sessionStorage.setItem("pz-token", r.token); } catch (e) { /* ok */ }
      estado.aba = "painel"; desenhar();
    } catch (e) { erro.replaceChildren(aviso("erro", e.message)); }
  } },
  h("h2", {}, "Entrar"), msg ? aviso("ok", msg) : null, erro,
  h("label", { for: "u" }, "Usuário"), u, h("label", { for: "s" }, "Senha"), s,
  h("button", { class: "principal", type: "submit" }, "Entrar"));
  raiz.replaceChildren(h("div", { class: "login" }, h("img", { class: "login-logo", src: "/static/logo.svg", alt: "Pizza" }), h("h1", {}, "Sistema da Pizzaria"), form));
}

function telaTrocaSenha() {
  const a = h("input", { type: "password", autocomplete: "current-password", required: "" });
  const n = h("input", { type: "password", autocomplete: "new-password", required: "", minlength: "8" });
  const msg = h("div");
  const form = h("form", { class: "cartao", onsubmit: async (ev) => {
    ev.preventDefault(); msg.replaceChildren();
    try {
      await api("POST", "/auth/trocar-senha", { senha_atual: a.value, senha_nova: n.value });
      estado.eu = await api("GET", "/auth/me"); desenhar();
    } catch (e) { msg.replaceChildren(aviso("erro", e.message)); }
  } },
  h("h2", {}, "Defina a sua senha"), h("p", { class: "pequeno" }, "Sua senha foi definida pelo administrador. Escolha uma senha só sua, com pelo menos 8 caracteres."),
  msg, h("label", {}, "Senha atual"), a, h("label", {}, "Senha nova"), n,
  h("button", { class: "principal", type: "submit" }, "Salvar senha"));
  raiz.replaceChildren(h("div", { class: "login" }, form,
    h("button", { class: "sec", onclick: () => sair() }, "Sair")));
}

const ABAS = [
  ["painel", "Painel", null, "Visão geral", "📊"],
  ["vendas", "Vendas", ["administrador", "proprietario", "gerente", "subgerente", "atendente"], "Operação", "🧾"],
  ["producao", "Produção", ["administrador", "proprietario", "gerente", "subgerente", "massa", "pizzaiolo", "acabamento", "atendente"], "Operação", "👨‍🍳"],
  ["caixa", "Caixa", ["administrador", "proprietario", "gerente", "subgerente", "atendente"], "Operação", "💰"],
  ["estoque", "Estoque", ["administrador", "proprietario", "gerente", "subgerente"], "Suprimentos", "📦"],
  ["compras", "Compras", ["administrador", "proprietario", "gerente", "subgerente"], "Suprimentos", "🛒"],
  ["contas", "Contas", ["administrador", "proprietario", "gerente", "subgerente"], "Financeiro", "🏦"],
  ["bi", "BI", ["administrador", "proprietario", "gerente", "subgerente"], "Financeiro", "📊"],
  ["custos", "Custos", ["administrador", "proprietario", "gerente", "subgerente"], "Financeiro", "📈"],
  ["imobilizado", "Imobilizado", ["administrador", "proprietario", "gerente", "subgerente"], "Financeiro", "🏭"],
  ["rh", "RH", ["administrador", "proprietario", "gerente", "subgerente"], "Financeiro", "👥"],
  ["meusdados", "Meus dados", null, "Visão geral", "🗓️"],
  ["cardapio", "Cardápio", ["administrador", "proprietario", "gerente", "subgerente", "atendente"], "Cadastros", "🍕"],
  ["fichas", "Fichas e etapas", ["administrador", "proprietario", "gerente", "subgerente"], "Cadastros", "📋"],
  ["clientes", "Clientes", ["administrador", "proprietario", "gerente", "subgerente", "atendente"], "Cadastros", "👥"],
  ["entregadores", "Entregadores", ["administrador", "proprietario", "gerente", "subgerente", "atendente"], "Cadastros", "🛵"],
  ["usuarios", "Usuários", ["administrador", "proprietario"], "Sistema", "🔑"],
  ["parametros", "Parâmetros", ["administrador", "proprietario", "gerente", "subgerente"], "Sistema", "⚙️"],
  ["auditoria", "Auditoria", ["administrador", "proprietario", "gerente", "subgerente"], "Sistema", "🧾"],
];

function alternarTema() {
  const dia = document.documentElement.getAttribute("data-theme") === "light";
  if (dia) document.documentElement.removeAttribute("data-theme"); else document.documentElement.setAttribute("data-theme", "light");
  try { localStorage.setItem("pz-tema", dia ? "noite" : "dia"); } catch (e) { /* sem armazenamento */ }
}

function moldura(conteudo) {
  const abas = ABAS.filter(([, , perfis]) => !perfis || perfis.includes(estado.eu.perfil));
  const itens = [];
  let grupo = null;
  for (const [id, nome, , g, icone] of abas) {
    if (g !== grupo) { itens.push(h("div", { class: "menu-sec" }, g)); grupo = g; }
    itens.push(h("button", { class: "menu-item" + (id === estado.aba ? " ativo" : ""), title: nome, onclick: () => { estado.aba = id; desenhar(); } },
      h("span", { class: "ic" }, icone), h("span", { class: "rot" }, nome)));
  }
  const menu = h("aside", { id: "menu" },
    h("div", { class: "marca" }, h("img", { src: "/static/logo.svg", alt: "Pizza" }),
      h("div", { class: "txt" }, h("div", { class: "t1" }, "Sistema da Pizzaria"), h("div", { class: "t2" }, "Gestão integrada"))),
    h("nav", { class: "menu" }, itens));
  const fundo = h("div", { id: "fundo-menu", onclick: () => { menu.classList.remove("aberto"); fundo.classList.remove("aberto"); } });
  const titulo = (abas.find(([id]) => id === estado.aba) || abas[0])[1];
  const topo = h("div", { class: "topo" },
    h("button", { class: "sanduiche", title: "Menu", onclick: () => {
      if (window.matchMedia("(max-width:760px)").matches) { const a = menu.classList.toggle("aberto"); fundo.classList.toggle("aberto", a); }
      else menu.classList.toggle("recolhido");
    } }, "☰"),
    h("div", { class: "titulo-pagina" }, titulo),
    h("div", { class: "topo-dir" },
      h("button", { class: "tema", title: "Alternar noite e dia", onclick: alternarTema },
        h("span", {}, "🌙"), h("span", { class: "tema-trilho" }, h("span", { class: "tema-bola" })), h("span", {}, "☀️")),
      h("div", { class: "chip" }, "👤 ", h("b", {}, estado.eu.nome), h("span", { class: "nome-completo" }, " (" + estado.eu.perfil + ")")),
      h("button", { class: "sec", onclick: () => sair() }, "Sair")));
  raiz.replaceChildren(h("div", { id: "quadro" }, menu, fundo,
    h("div", { id: "principal" }, topo, h("main", { class: "conteudo" }, h("div", { class: "conteudo-miolo" }, conteudo)))));
}

async function abaPainel() {
  const alvo = h("div"); alvo.append(h("p", {}, "Carregando..."));
  moldura(alvo);
  const blocos = [h("div", { class: "cartao" }, h("h2", {}, "Bem-vindo, " + estado.eu.nome),
    h("p", {}, "Este é o primeiro incremento do sistema: acesso, usuários, parâmetros e auditoria. Pedidos, produção e caixa entram nas próximas fatias."))];
  if (["administrador", "proprietario", "gerente", "subgerente"].includes(estado.eu.perfil)) {
    try {
      const b = await api("GET", "/sistema/backup");
      const cart = h("div", { class: "cartao" }, h("h2", {}, "Backup"));
      if (!b.ultimo_sucesso) cart.append(aviso("alerta", "Nenhum backup feito ainda."));
      else cart.append(aviso(b.atrasado || b.ultimo_sucesso.copias_falha || (b.copias_extras_configuradas && !b.ultimo_sucesso.copias_ok) ? "alerta" : "ok", (b.atrasado ? "Backup atrasado. " : (b.ultimo_sucesso.copias_falha || (b.copias_extras_configuradas && !b.ultimo_sucesso.copias_ok) ? "Backup feito, mas a cópia extra não foi concluída. " : "Backup em dia. ")) + "Último: " + fmtData(b.ultimo_sucesso.concluido_em)
        + " (" + b.ultimo_sucesso.copias_ok + " cópia(s) extra(s) ok" + (b.ultimo_sucesso.copias_falha ? ", " + b.ultimo_sucesso.copias_falha + " com falha" : "") + ")."));
      if (b.ultima_tentativa && !b.ultima_tentativa.sucesso) cart.append(aviso("erro", "A última tentativa falhou: " + (b.ultima_tentativa.detalhe || "sem detalhe")));
      if (!b.copias_extras_configuradas) cart.append(aviso("alerta", "Nenhuma cópia fora da pasta do sistema está configurada."));
      const msg = h("div");
      cart.append(msg, h("button", { class: "principal", onclick: async (ev) => {
        ev.target.disabled = true; msg.replaceChildren(h("p", {}, "Fazendo backup..."));
        try {
          const r = await api("POST", "/sistema/backup");
          msg.replaceChildren(aviso(r.sucesso && !r.copias_falha ? "ok" : "alerta", r.sucesso ? "Backup feito: " + r.arquivo + (r.detalhe ? ". " + r.detalhe : "") : "Backup falhou: " + r.detalhe));
        } catch (e) { msg.replaceChildren(aviso("erro", e.message)); }
        ev.target.disabled = false;
      } }, "Fazer backup agora"));
      blocos.push(cart);
    } catch (e) { blocos.push(aviso("erro", e.message)); }
  }
  alvo.replaceChildren(...blocos);
}

async function abaUsuarios() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  async function carregar() {
    let lista;
    try { lista = await api("GET", "/usuarios"); } catch (e) { alvo.replaceChildren(aviso("erro", e.message)); return; }
    const u = h("input", { required: "", autocapitalize: "none" }), nome = h("input", { required: "" });
    const perfil = h("select", {}, ["atendente", "gerente", "subgerente", "massa", "pizzaiolo", "acabamento", "proprietario", "administrador"].map((p) => h("option", { value: p }, p)));
    const senha = h("input", { type: "password", autocomplete: "new-password", minlength: "8", required: "" });
    const form = h("form", { class: "cartao", onsubmit: async (ev) => {
      ev.preventDefault(); msg.replaceChildren();
      try { await api("POST", "/usuarios", { usuario: u.value, nome: nome.value, perfil: perfil.value, senha: senha.value });
        msg.replaceChildren(aviso("ok", "Usuário criado. Ele troca a senha no primeiro acesso.")); await carregar(); }
      catch (e) { msg.replaceChildren(aviso("erro", e.message)); }
    } }, h("h2", {}, "Novo usuário"),
    h("div", { class: "linha" }, h("div", {}, h("label", {}, "Usuário"), u), h("div", {}, h("label", {}, "Nome"), nome)),
    h("div", { class: "linha" }, h("div", {}, h("label", {}, "Perfil"), perfil), h("div", {}, h("label", {}, "Senha inicial"), senha)),
    h("button", { class: "principal", type: "submit" }, "Criar usuário"));
    const linhas = lista.map((x) => h("tr", {}, h("td", {}, x.usuario), h("td", {}, x.nome), h("td", {}, x.perfil),
      h("td", {}, x.ativo ? "ativo" : "inativo"),
      h("td", {}, h("button", { class: "sec", onclick: async () => {
        msg.replaceChildren();
        try { await api("PATCH", "/usuarios/" + x.id, { ativo: !x.ativo }); await carregar(); } catch (e) { msg.replaceChildren(aviso("erro", e.message)); }
      } }, x.ativo ? "Desativar" : "Reativar"), " ",
      h("button", { class: "sec", onclick: (ev) => {
        const celula = ev.target.parentNode;
        const campo = h("input", { type: "password", autocomplete: "new-password", minlength: "8", placeholder: "Senha provisória" });
        celula.replaceChildren(campo, h("button", { class: "sec", onclick: async () => {
          msg.replaceChildren();
          try { await api("POST", "/usuarios/" + x.id + "/redefinir-senha", { senha_nova: campo.value }); msg.replaceChildren(aviso("ok", "Senha redefinida. O usuário troca no próximo acesso.")); await carregar(); }
          catch (e) { msg.replaceChildren(aviso("erro", e.message)); }
        } }, "Salvar"), h("button", { class: "sec", onclick: () => carregar() }, "Cancelar"));
        campo.focus();
      } }, "Redefinir senha"))));
    alvo.replaceChildren(msg, form, h("div", { class: "cartao tabela" }, h("h2", {}, "Usuários"),
      h("table", {}, h("thead", {}, h("tr", {}, ["Usuário", "Nome", "Perfil", "Situação", ""].map((t) => h("th", {}, t)))), h("tbody", {}, linhas))));
  }
  await carregar();
}

async function abaParametros() {
  const alvo = h("div"); moldura(alvo);
  const podeEditar = ["administrador", "proprietario"].includes(estado.eu.perfil);
  let lista;
  try { lista = await api("GET", "/parametros"); } catch (e) { alvo.replaceChildren(aviso("erro", e.message)); return; }
  const msg = h("div");
  const linhas = lista.map((p) => {
    const atual = Array.isArray(p.valor) ? p.valor.join(", ") : (p.valor == null ? "" : String(p.valor));
    const campo = h("input", { value: atual, placeholder: p.tipo === "formas" ? "dinheiro, pix, credito, debito" : "não definido", disabled: !podeEditar });
    const salvar = h("button", { class: "sec", disabled: !podeEditar, onclick: async () => {
      msg.replaceChildren();
      const bruto = campo.value.trim();
      const valor = p.tipo === "formas" ? (bruto ? bruto.split(",").map((x) => x.trim()).filter(Boolean) : null) : (bruto || null);
      try { await api("PUT", "/parametros/" + p.chave, { valor }); msg.replaceChildren(aviso("ok", "Salvo: " + p.descricao)); }
      catch (e) { msg.replaceChildren(aviso("erro", e.message)); }
    } }, "Salvar");
    return h("tr", {}, h("td", {}, p.descricao, h("div", { class: "pequeno" }, p.definido ? "alterado " + fmtData(p.vigente_desde) : "valor padrão")), h("td", {}, campo), h("td", {}, salvar));
  });
  alvo.replaceChildren(msg, h("div", { class: "cartao tabela" }, h("h2", {}, "Parâmetros da loja"),
    podeEditar ? null : h("p", { class: "pequeno" }, "Só o administrador e o proprietário alteram parâmetros."),
    h("table", {}, h("tbody", {}, linhas))));
}

async function abaAuditoria() {
  const alvo = h("div"); moldura(alvo);
  let r;
  try { r = await api("GET", "/auditoria?limite=100"); } catch (e) { alvo.replaceChildren(aviso("erro", e.message)); return; }
  const linhas = r.data.map((a) => h("tr", {}, h("td", {}, fmtData(a.quando)), h("td", {}, a.usuario || ""), h("td", {}, a.acao),
    h("td", {}, a.entidade + (a.entidade_id ? " " + a.entidade_id : "")),
    h("td", { class: "pequeno" }, a.depois ? JSON.stringify(a.depois) : "")));
  alvo.replaceChildren(h("div", { class: "cartao tabela" }, h("h2", {}, "Auditoria (últimos " + r.data.length + " de " + r.total + ")"),
    h("table", {}, h("thead", {}, h("tr", {}, ["Quando", "Quem", "Ação", "O quê", "Depois"].map((t) => h("th", {}, t)))), h("tbody", {}, linhas))));
}

// ---------------------------------------------------------------- Fatia 1B: cadastros
const GERENCIA = ["administrador", "proprietario", "gerente", "subgerente"];
const ehGerencia = () => GERENCIA.includes(estado.eu.perfil);
const brl = (v) => v == null ? "" : "R$ " + String(v).replace(".", ",");
const campo = (rotulo, el) => h("div", {}, h("label", {}, rotulo), el);
const entradaPreco = (valor) => h("input", { inputmode: "decimal", placeholder: "0,00", value: valor == null ? "" : String(valor).replace(".", ","), autocomplete: "off" });
const precoOuNulo = (el) => el.value.trim() === "" ? null : el.value.trim();
const rotuloTipo = { pizza: "Pizza", calzone: "Calzone", bebida: "Bebida", acompanhamento: "Acompanhamento" };

async function abaCardapio() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  const subs = [["pizza", "Sabores de pizza"], ["categorias", "Preços por categoria"], ["adicionais", "Bordas e adicionais"], ["outros", "Calzones, bebidas e outros"], ["simulador", "Simulador de preço"]];
  if (!estado.sub) estado.sub = "pizza";
  const editar = ehGerencia();
  const falha = (e) => msg.replaceChildren(aviso("erro", e.message));
  const ok = (t) => msg.replaceChildren(aviso("ok", t));

  async function desenharSub() {
    const nav = h("div", { class: "subnav" }, subs.map(([id, nome]) => h("button", { class: id === estado.sub ? "ativo" : "", onclick: () => { estado.sub = id; msg.replaceChildren(); desenharSub(); } }, nome)));
    let corpo;
    try {
      if (estado.sub === "categorias") corpo = await subCategorias();
      else if (estado.sub === "adicionais") corpo = await subAdicionais();
      else if (estado.sub === "simulador") corpo = await subSimulador();
      else corpo = await subProdutos(estado.sub === "pizza");
    } catch (e) { corpo = aviso("erro", e.message); }
    alvo.replaceChildren(nav, msg, corpo);
  }

  async function subCategorias() {
    const lista = await api("GET", "/categorias");
    const nome = h("input", { required: "" }), g = entradaPreco(), b = entradaPreco();
    const form = h("form", { class: "cartao", onsubmit: async (ev) => {
      ev.preventDefault();
      try { await api("POST", "/categorias", { nome: nome.value, preco_padrao_grande: precoOuNulo(g), preco_padrao_broto: precoOuNulo(b) }); ok("Categoria criada."); desenharSub(); } catch (e) { falha(e); }
    } }, h("h2", {}, "Nova categoria"), h("div", { class: "linha" }, campo("Nome (ex.: Tradicionais)", nome), campo("Preço padrão Grande", g), campo("Preço padrão Broto", b)),
    h("button", { class: "principal", type: "submit" }, "Criar categoria"));
    const linhas = lista.map((c) => {
      const tr = h("tr", {});
      const mostrar = () => tr.replaceChildren(h("td", {}, c.nome), h("td", {}, brl(c.preco_padrao_grande)), h("td", {}, brl(c.preco_padrao_broto)), h("td", {}, c.ativo ? "ativa" : "inativa"),
        h("td", {}, editar ? [h("button", { class: "sec", onclick: edicao }, "Editar"), " ", h("button", { class: "sec", onclick: async () => {
          try { await api("PATCH", "/categorias/" + c.id, { ativo: !c.ativo }); desenharSub(); } catch (e) { falha(e); }
        } }, c.ativo ? "Inativar" : "Reativar")] : null));
      const edicao = () => {
        const n = h("input", { value: c.nome }), eg = entradaPreco(c.preco_padrao_grande), eb = entradaPreco(c.preco_padrao_broto);
        tr.replaceChildren(h("td", {}, n), h("td", {}, eg), h("td", {}, eb), h("td", {}), h("td", {}, h("button", { class: "sec", onclick: async () => {
          try { await api("PATCH", "/categorias/" + c.id, { nome: n.value, preco_padrao_grande: precoOuNulo(eg), preco_padrao_broto: precoOuNulo(eb) }); ok("Categoria salva."); desenharSub(); } catch (e) { falha(e); }
        } }, "Salvar"), " ", h("button", { class: "sec", onclick: mostrar }, "Cancelar")));
      };
      mostrar(); return tr;
    });
    return h("div", {}, h("p", { class: "pequeno" }, "O preço padrão da categoria só preenche o cadastro de um sabor novo; cada sabor guarda o próprio preço."),
      editar ? form : null, h("div", { class: "cartao tabela" }, h("h2", {}, "Categorias"),
        h("table", {}, h("thead", {}, h("tr", {}, ["Categoria", "Padrão Grande", "Padrão Broto", "Situação", ""].map((t) => h("th", {}, t)))), h("tbody", {}, linhas))));
  }

  async function subProdutos(ehPizza) {
    const [produtos, categorias] = await Promise.all([api("GET", "/produtos"), ehPizza ? api("GET", "/categorias") : Promise.resolve([])]);
    const filtrados = produtos.filter((p) => ehPizza ? p.tipo === "pizza" : p.tipo !== "pizza");
    const tipo = h("select", {}, ["calzone", "bebida", "acompanhamento"].map((t) => h("option", { value: t }, rotuloTipo[t])));
    const nome = h("input", { required: "" }), ingr = h("input", { placeholder: "opcional" });
    const cat = h("select", {}, categorias.filter((c) => c.ativo).map((c) => h("option", { value: c.id }, c.nome)));
    const g = entradaPreco(), b = entradaPreco(), u = entradaPreco();
    const padrao = () => { const c = categorias.find((x) => String(x.id) === cat.value); if (c) { g.value = c.preco_padrao_grande == null ? "" : String(c.preco_padrao_grande).replace(".", ","); b.value = c.preco_padrao_broto == null ? "" : String(c.preco_padrao_broto).replace(".", ","); } };
    cat.onchange = padrao; if (ehPizza) padrao();  // trocar a categoria refaz os preços sugeridos
    const form = h("form", { class: "cartao", onsubmit: async (ev) => {
      ev.preventDefault();
      const corpo = ehPizza ? { tipo: "pizza", nome: nome.value, categoria_id: Number(cat.value), ingredientes: ingr.value.trim() || null, preco_grande: precoOuNulo(g), preco_broto: precoOuNulo(b) }
        : { tipo: tipo.value, nome: nome.value, ingredientes: ingr.value.trim() || null, preco_unico: precoOuNulo(u) };
      try { await api("POST", "/produtos", corpo); ok("Cadastrado."); desenharSub(); } catch (e) { falha(e); }
    } }, h("h2", {}, ehPizza ? "Novo sabor de pizza" : "Novo produto"),
    h("div", { class: "linha" }, ehPizza ? campo("Categoria", cat) : campo("Tipo", tipo), campo("Nome", nome), campo("Ingredientes", ingr)),
    h("div", { class: "linha" }, ehPizza ? [campo("Preço Grande", g), campo("Preço Broto", b)] : campo("Preço", u)),
    h("button", { class: "principal", type: "submit" }, "Cadastrar"));
    const cabeca = ehPizza ? ["Categoria", "Sabor", "Ingredientes", "Grande", "Broto", "Situação", ""] : ["Tipo", "Nome", "Preço", "Situação", ""];
    const linhas = filtrados.map((p) => {
      const tr = h("tr", {});
      const mostrar = () => tr.replaceChildren(...(ehPizza
        ? [h("td", {}, p.categoria), h("td", {}, p.nome), h("td", { class: "pequeno" }, p.ingredientes || ""), h("td", {}, brl(p.preco_grande)), h("td", {}, brl(p.preco_broto))]
        : [h("td", {}, rotuloTipo[p.tipo]), h("td", {}, p.nome), h("td", {}, brl(p.preco_unico))]),
        h("td", {}, p.ativo ? "ativo" : "inativo"),
        h("td", {}, editar ? [h("button", { class: "sec", onclick: edicao }, "Editar"), " ", h("button", { class: "sec", onclick: async () => {
          try { await api("PATCH", "/produtos/" + p.id, { ativo: !p.ativo }); desenharSub(); } catch (e) { falha(e); }
        } }, p.ativo ? "Inativar" : "Reativar"), " ", h("button", { class: "sec", onclick: historico }, "Histórico")] : null));
      const edicao = () => {
        const n = h("input", { value: p.nome }), i = h("input", { value: p.ingredientes || "" });
        const eg = entradaPreco(p.preco_grande), eb = entradaPreco(p.preco_broto), eu = entradaPreco(p.preco_unico);
        const salvar = h("button", { class: "sec", onclick: async () => {
          const corpo = { nome: n.value, ingredientes: i.value.trim() || null };
          if (ehPizza) { if (eg.value.trim() !== String(p.preco_grande).replace(".", ",")) corpo.preco_grande = eg.value.trim(); if (eb.value.trim() !== String(p.preco_broto).replace(".", ",")) corpo.preco_broto = eb.value.trim(); }
          else if (eu.value.trim() !== String(p.preco_unico).replace(".", ",")) corpo.preco_unico = eu.value.trim();
          try { await api("PATCH", "/produtos/" + p.id, corpo); ok("Salvo. Preço alterado fica no histórico."); desenharSub(); } catch (e) { falha(e); }
        } }, "Salvar");
        tr.replaceChildren(...(ehPizza ? [h("td", {}, p.categoria), h("td", {}, n), h("td", {}, i), h("td", {}, eg), h("td", {}, eb)] : [h("td", {}, rotuloTipo[p.tipo]), h("td", {}, n), h("td", {}, eu)]),
          h("td", {}, i && !ehPizza ? i : ""), h("td", {}, salvar, " ", h("button", { class: "sec", onclick: mostrar }, "Cancelar")));
      };
      const historico = async () => {
        try {
          const hist = await api("GET", "/produtos/" + p.id + "/historico-precos");
          const prox = tr.nextSibling && tr.nextSibling.classList && tr.nextSibling.classList.contains("hist") ? tr.nextSibling : null;
          if (prox) { prox.remove(); return; }
          const col = h("td", { colspan: String(cabeca.length), class: "pequeno" }, hist.length ? hist.map((x) => h("div", {}, fmtData(x.vigente_desde) + ": " + x.tamanho + " " + brl(x.valor) + (x.alterado_por ? " (" + x.alterado_por + ")" : ""))) : "Sem histórico.");
          tr.after(h("tr", { class: "hist" }, col));
        } catch (e) { falha(e); }
      };
      mostrar(); return tr;
    });
    return h("div", {}, editar ? form : null, h("div", { class: "cartao tabela" }, h("h2", {}, ehPizza ? "Sabores de pizza" : "Calzones, bebidas e acompanhamentos"),
      linhas.length ? h("table", {}, h("thead", {}, h("tr", {}, cabeca.map((t) => h("th", {}, t)))), h("tbody", {}, linhas)) : h("p", {}, "Nada cadastrado ainda.")));
  }

  async function subAdicionais() {
    const lista = await api("GET", "/adicionais");
    const tipo = h("select", {}, [["borda", "Borda"], ["adicional", "Adicional"]].map(([v, t]) => h("option", { value: v }, t)));
    const nome = h("input", { required: "" }), g = entradaPreco(), b = entradaPreco();
    const form = h("form", { class: "cartao", onsubmit: async (ev) => {
      ev.preventDefault();
      try { await api("POST", "/adicionais", { tipo: tipo.value, nome: nome.value, preco_grande: g.value.trim(), preco_broto: b.value.trim() }); ok("Cadastrado."); desenharSub(); } catch (e) { falha(e); }
    } }, h("h2", {}, "Nova borda ou adicional"), h("div", { class: "linha" }, campo("Tipo", tipo), campo("Nome", nome), campo("Preço na Grande", g), campo("Preço na Broto", b)),
    h("button", { class: "principal", type: "submit" }, "Cadastrar"));
    const linhas = lista.map((a) => {
      const tr = h("tr", {});
      const mostrar = () => tr.replaceChildren(h("td", {}, a.tipo === "borda" ? "Borda" : "Adicional"), h("td", {}, a.nome), h("td", {}, brl(a.preco_grande)), h("td", {}, brl(a.preco_broto)), h("td", {}, a.ativo ? "ativo" : "inativo"),
        h("td", {}, editar ? [h("button", { class: "sec", onclick: edicao }, "Editar"), " ", h("button", { class: "sec", onclick: async () => {
          try { await api("PATCH", "/adicionais/" + a.id, { ativo: !a.ativo }); desenharSub(); } catch (e) { falha(e); }
        } }, a.ativo ? "Inativar" : "Reativar")] : null));
      const edicao = () => {
        const n = h("input", { value: a.nome }), eg = entradaPreco(a.preco_grande), eb = entradaPreco(a.preco_broto);
        tr.replaceChildren(h("td", {}, a.tipo === "borda" ? "Borda" : "Adicional"), h("td", {}, n), h("td", {}, eg), h("td", {}, eb), h("td", {}), h("td", {}, h("button", { class: "sec", onclick: async () => {
          const corpo = { nome: n.value };
          if (eg.value.trim() !== String(a.preco_grande).replace(".", ",")) corpo.preco_grande = eg.value.trim();
          if (eb.value.trim() !== String(a.preco_broto).replace(".", ",")) corpo.preco_broto = eb.value.trim();
          try { await api("PATCH", "/adicionais/" + a.id, corpo); ok("Salvo."); desenharSub(); } catch (e) { falha(e); }
        } }, "Salvar"), " ", h("button", { class: "sec", onclick: mostrar }, "Cancelar")));
      };
      mostrar(); return tr;
    });
    return h("div", {}, editar ? form : null, h("div", { class: "cartao tabela" }, h("h2", {}, "Bordas e adicionais"),
      linhas.length ? h("table", {}, h("thead", {}, h("tr", {}, ["Tipo", "Nome", "Grande", "Broto", "Situação", ""].map((t) => h("th", {}, t)))), h("tbody", {}, linhas)) : h("p", {}, "Nada cadastrado ainda.")));
  }

  async function subSimulador() {
    const [produtos, adicionais] = await Promise.all([api("GET", "/produtos?tipo=pizza&ativo=true"), api("GET", "/adicionais?ativo=true")]);
    const tam = h("select", {}, [["grande", "Grande"], ["broto", "Broto"]].map(([v, t]) => h("option", { value: v }, t)));
    const opcoes = (vazio) => [h("option", { value: "" }, vazio)].concat(produtos.map((p) => h("option", { value: p.id }, p.categoria + ": " + p.nome)));
    const s1 = h("select", {}, opcoes("Escolha o sabor")), s2 = h("select", {}, opcoes("Sem segundo sabor"));
    const checks = adicionais.map((a) => { const c = h("input", { type: "checkbox", value: a.id }); return [c, h("label", { class: "marca" }, c, " " + a.nome + " (" + (a.tipo === "borda" ? "borda" : "adicional") + ")")]; });
    const saida = h("div");
    const ajusta = () => { s2.disabled = tam.value !== "grande"; if (s2.disabled) s2.value = ""; };
    tam.onchange = ajusta; ajusta();
    const form = h("form", { class: "cartao", onsubmit: async (ev) => {
      ev.preventDefault(); saida.replaceChildren();
      if (!s1.value) { saida.replaceChildren(aviso("erro", "Escolha o sabor.")); return; }
      const corpo = { tamanho: tam.value, sabor1_id: Number(s1.value), sabor2_id: s2.value ? Number(s2.value) : null, adicional_ids: checks.filter(([c]) => c.checked).map(([c]) => Number(c.value)) };
      try {
        const r = await api("POST", "/precos/pizza", corpo);
        saida.replaceChildren(h("table", {}, h("tbody", {}, r.itens.map((i) => h("tr", {}, h("td", {}, i.descricao), h("td", {}, brl(i.valor)))),
          h("tr", {}, h("th", {}, "Total"), h("th", {}, brl(r.total))))));
      } catch (e) { saida.replaceChildren(aviso("erro", e.message)); }
    } }, h("h2", {}, "Simulador de preço"), h("p", { class: "pequeno" }, "Confere o preço de uma pizza antes de vender. Grande com dois sabores custa a metade de cada sabor, arredondando para cima cada metade."),
    h("div", { class: "linha" }, campo("Tamanho", tam), campo("Sabor 1", s1), campo("Sabor 2", s2)),
    h("div", {}, checks.map(([, l]) => l)), h("button", { class: "principal", type: "submit" }, "Calcular"), saida);
    return form;
  }
  await desenharSub();
}

async function abaClientes() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div"), q = h("input", { placeholder: "Buscar por nome ou telefone", autocomplete: "off" }), tabela = h("div", { class: "cartao tabela" });
  const falha = (e) => msg.replaceChildren(aviso("erro", e.message));
  let busca = 0;
  async function listar() {
    let lista;
    const minha = ++busca;
    try { lista = await api("GET", "/clientes?limite=200&q=" + encodeURIComponent(q.value.trim())); } catch (e) { falha(e); return; }
    if (minha !== busca) return;  // resposta de uma busca antiga
    const linhas = lista.map((c) => {
      const tr = h("tr", {});
      const mostrar = () => tr.replaceChildren(h("td", {}, c.nome), h("td", {}, c.telefone), h("td", { class: "pequeno" }, c.endereco || ""), h("td", {}, c.ativo ? "ativo" : "inativo"),
        h("td", {}, h("button", { class: "sec", onclick: edicao }, "Editar"), " ", h("button", { class: "sec", onclick: async () => {
          try { await api("PATCH", "/clientes/" + c.id, { ativo: !c.ativo }); listar(); } catch (e) { falha(e); }
        } }, c.ativo ? "Inativar" : "Reativar")));
      const edicao = () => {
        const n = h("input", { value: c.nome }), t = h("input", { value: c.telefone, inputmode: "tel" }), e = h("input", { value: c.endereco || "" });
        tr.replaceChildren(h("td", {}, n), h("td", {}, t), h("td", {}, e), h("td", {}), h("td", {}, h("button", { class: "sec", onclick: async () => {
          try { await api("PATCH", "/clientes/" + c.id, { nome: n.value, telefone: t.value, endereco: e.value.trim() || null }); msg.replaceChildren(aviso("ok", "Cliente salvo.")); listar(); } catch (x) { falha(x); }
        } }, "Salvar"), " ", h("button", { class: "sec", onclick: mostrar }, "Cancelar")));
      };
      mostrar(); return tr;
    });
    tabela.replaceChildren(h("h2", {}, lista.length >= 200 ? "Clientes (primeiros 200; refine a busca)" : "Clientes (" + lista.length + ")"),
      linhas.length ? h("table", {}, h("thead", {}, h("tr", {}, ["Nome", "Telefone", "Endereço", "Situação", ""].map((t) => h("th", {}, t)))), h("tbody", {}, linhas)) : h("p", {}, "Nenhum cliente encontrado."));
  }
  const nome = h("input", { required: "" }), tel = h("input", { required: "", inputmode: "tel" }), end = h("input", { placeholder: "rua, número, bairro, complemento" });
  const form = h("form", { class: "cartao", onsubmit: async (ev) => {
    ev.preventDefault();
    try { await api("POST", "/clientes", { nome: nome.value, telefone: tel.value, endereco: end.value.trim() || null });
      msg.replaceChildren(aviso("ok", "Cliente cadastrado.")); nome.value = tel.value = end.value = ""; listar(); } catch (e) { falha(e); }
  } }, h("h2", {}, "Novo cliente"), h("div", { class: "linha" }, campo("Nome", nome), campo("Telefone (com DDD)", tel)), campo("Endereço", end), h("button", { class: "principal", type: "submit" }, "Cadastrar"));
  let espera = null;
  q.oninput = () => { clearTimeout(espera); espera = setTimeout(listar, 300); };
  alvo.replaceChildren(msg, form, h("div", { class: "cartao" }, q), tabela);
  await listar();
}

async function abaEntregadores() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  const editar = ehGerencia();
  let lista;
  try { lista = await api("GET", "/entregadores"); } catch (e) { alvo.replaceChildren(aviso("erro", e.message)); return; }
  const falha = (e) => msg.replaceChildren(aviso("erro", e.message));
  const nome = h("input", { required: "" }), tel = h("input", { inputmode: "tel", placeholder: "opcional" });
  const form = h("form", { class: "cartao", onsubmit: async (ev) => {
    ev.preventDefault();
    try { await api("POST", "/entregadores", { nome: nome.value, telefone: tel.value.trim() || null }); abaEntregadores(); } catch (e) { falha(e); }
  } }, h("h2", {}, "Novo entregador"), h("p", { class: "pequeno" }, "Entregadores são terceiros: aqui só o cadastro. Valores de entrega e diária entram no fechamento."),
  h("div", { class: "linha" }, campo("Nome", nome), campo("Telefone", tel)), h("button", { class: "principal", type: "submit" }, "Cadastrar"));
  const linhas = lista.map((x) => {
    const tr = h("tr", {});
    const mostrar = () => tr.replaceChildren(h("td", {}, x.nome), h("td", {}, x.telefone || ""), h("td", {}, x.ativo ? "ativo" : "inativo"),
      h("td", {}, editar ? [h("button", { class: "sec", onclick: edicao }, "Editar"), " ", h("button", { class: "sec", onclick: async () => {
        try { await api("PATCH", "/entregadores/" + x.id, { ativo: !x.ativo }); abaEntregadores(); } catch (e) { falha(e); }
      } }, x.ativo ? "Inativar" : "Reativar")] : null));
    const edicao = () => {
      const n = h("input", { value: x.nome }), t = h("input", { value: x.telefone || "", inputmode: "tel" });
      tr.replaceChildren(h("td", {}, n), h("td", {}, t), h("td", {}), h("td", {}, h("button", { class: "sec", onclick: async () => {
        try { await api("PATCH", "/entregadores/" + x.id, { nome: n.value, telefone: t.value.trim() }); abaEntregadores(); } catch (e) { falha(e); }
      } }, "Salvar"), " ", h("button", { class: "sec", onclick: mostrar }, "Cancelar")));
    };
    mostrar(); return tr;
  });
  alvo.replaceChildren(msg, editar ? form : null, h("div", { class: "cartao tabela" }, h("h2", {}, "Entregadores"),
    linhas.length ? h("table", {}, h("thead", {}, h("tr", {}, ["Nome", "Telefone", "Situação", ""].map((t) => h("th", {}, t)))), h("tbody", {}, linhas)) : h("p", {}, "Nenhum entregador cadastrado.")));
}

// ---------------------------------------------------------------- Fatia 1B2: fichas e etapas
const FUNCOES = { massa: "Massa", pizzaiolo: "Pizzaiolo", acabamento: "Acabamento", automatica: "Automática (forno)" };
const CLASSES = { insumo: "Insumo", preparo: "Preparo", embalagem: "Embalagem", revenda: "Revenda", consumo: "Material de consumo" };

async function abaFichas() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  if (!estado.subf) estado.subf = "fichas";
  const falha = (e) => msg.replaceChildren(aviso("erro", e.message));
  const ok = (t) => msg.replaceChildren(aviso("ok", t));
  const subs = [["fichas", "Fichas técnicas"], ["itens", "Itens"], ["etapas", "Etapas de produção"], ["qualidade", "O que falta"]];

  async function desenharSub() {
    const nav = h("div", { class: "subnav" }, subs.map(([id, nome]) => h("button", { class: id === estado.subf ? "ativo" : "", onclick: () => { estado.subf = id; msg.replaceChildren(); desenharSub(); } }, nome)));
    let corpo;
    try { corpo = await ({ fichas: subFichas, itens: subItens, etapas: subEtapas, qualidade: subQualidade }[estado.subf])(); }
    catch (e) { corpo = aviso("erro", e.message); }
    alvo.replaceChildren(nav, msg, corpo);
  }

  async function subItens() {
    const lista = await api("GET", "/itens");
    const nome = h("input", { required: "" });
    const classe = h("select", {}, Object.entries(CLASSES).map(([v, t]) => h("option", { value: v }, t)));
    const un = h("select", {}, ["g", "kg", "ml", "l", "un", "fatia"].map((u) => h("option", { value: u }, u)));
    const form = h("form", { class: "cartao", onsubmit: async (ev) => {
      ev.preventDefault();
      try { await api("POST", "/itens", { nome: nome.value, classe: classe.value, unidade: un.value }); ok("Item cadastrado."); desenharSub(); } catch (e) { falha(e); }
    } }, h("h2", {}, "Novo item"), h("p", { class: "pequeno" }, "Insumo, preparo (massa, alho e óleo), embalagem, item de revenda ou material de consumo. Saldo e compra entram com Estoques."),
    h("div", { class: "linha" }, campo("Nome", nome), campo("Classe", classe), campo("Unidade", un)), h("button", { class: "principal", type: "submit" }, "Cadastrar"));
    const linhas = lista.map((i) => h("tr", {}, h("td", {}, i.nome), h("td", {}, CLASSES[i.classe]), h("td", {}, i.unidade), h("td", {}, i.ativo ? "ativo" : "inativo"),
      h("td", {}, h("button", { class: "sec", onclick: async () => { try { await api("PATCH", "/itens/" + i.id, { ativo: !i.ativo }); desenharSub(); } catch (e) { falha(e); } } }, i.ativo ? "Inativar" : "Reativar"))));
    return h("div", {}, form, h("div", { class: "cartao tabela" }, h("h2", {}, "Itens (" + lista.length + ")"),
      lista.length ? h("table", {}, h("thead", {}, h("tr", {}, ["Nome", "Classe", "Unidade", "Situação", ""].map((t) => h("th", {}, t)))), h("tbody", {}, linhas)) : h("p", {}, "Nenhum item cadastrado.")));
  }

  async function subFichas() {
    const [produtos, adicionais, itens] = await Promise.all([api("GET", "/produtos"), api("GET", "/adicionais"), api("GET", "/itens")]);
    const preparos = itens.filter((i) => i.classe === "preparo");
    const opcoes = [];
    produtos.forEach((p) => opcoes.push({ id: "produto/" + p.id, rotulo: rotuloTipo[p.tipo] + ": " + p.nome + (p.tipo === "pizza" ? " (meia Grande ou Broto)" : "") }));
    adicionais.forEach((a) => ["grande", "broto"].forEach((t) => opcoes.push({ id: "adicional/" + a.id + "/" + t, rotulo: (a.tipo === "borda" ? "Borda: " : "Adicional: ") + a.nome + " (" + t + ")" })));
    preparos.forEach((p) => opcoes.push({ id: "preparo/" + p.id, rotulo: "Preparo: " + p.nome }));
    ["grande", "broto"].forEach((t) => opcoes.push({ id: "base/" + t, rotulo: "Base da pizza " + t + " (massa aberta, caixa: um por pizza)" }));
    const sel = h("select", {}, [h("option", { value: "" }, "Escolha o que terá ficha")].concat(opcoes.map((o) => h("option", { value: o.id }, o.rotulo))));
    if (estado.fichaSel && opcoes.some((o) => o.id === estado.fichaSel)) sel.value = estado.fichaSel;
    const editor = h("div");
    const ativos = itens.filter((i) => i.ativo);
    let abertura = 0;
    async function abrir() {
      const dono = sel.value, minha = ++abertura;
      estado.fichaSel = dono; editor.replaceChildren();
      if (!dono) return;
      let f;
      try { f = await api("GET", "/fichas/" + dono); } catch (e) { falha(e); return; }
      if (minha !== abertura) return;  // resposta de uma escolha antiga
      const usados = new Set((f.linhas || []).map((l) => l.item_id));
      const ativos = itens.filter((i) => i.ativo || usados.has(i.id));
      const corpo = h("tbody");
      const novaLinha = (l) => {
        const item = h("select", {}, ativos.map((i) => h("option", { value: i.id }, i.nome + " (" + i.unidade + ")")));
        if (l) item.value = l.item_id;
        const q = h("input", { inputmode: "decimal", value: l ? String(l.quantidade).replace(".", ",") : "", placeholder: "0" });
        const perda = h("input", { inputmode: "decimal", value: l ? String(l.perda_pct).replace(".", ",") : "", placeholder: "padrão" });
        const fase = h("select", {}, [["montagem", "Antes do forno"], ["pos_forno", "Depois do forno"]].map(([v, t]) => h("option", { value: v }, t)));
        if (l) fase.value = l.fase;
        const tr = h("tr", {}, h("td", {}, item), h("td", {}, q), h("td", {}, perda), h("td", {}, fase),
          h("td", {}, h("button", { type: "button", class: "sec", onclick: () => tr.remove() }, "Tirar")));
        tr._ler = () => ({ item_id: Number(item.value), quantidade: q.value.trim(), perda_pct: perda.value.trim() || null, fase: fase.value });
        return tr;
      };
      (f.linhas || []).forEach((l) => corpo.append(novaLinha(l)));
      const salvar = h("button", { class: "principal", type: "button", onclick: async () => {
        try {
          const linhas = [...corpo.children].map((tr) => tr._ler());
          const r = await api("PUT", "/fichas/" + dono, { linhas });
          ok("Ficha salva (" + r.linhas.length + " linhas). A versão anterior fica guardada."); abrir();
        } catch (e) { falha(e); }
      } }, "Salvar ficha");
      editor.replaceChildren(h("div", { class: "cartao tabela" }, h("h2", {}, "Ficha"),
        h("p", { class: "pequeno" }, f.desde ? "Versão salva em " + fmtData(f.desde) + "." : "Ainda sem ficha: o produto aparece em 'O que falta', não como custo zero."),
        ativos.length ? null : aviso("alerta", "Cadastre primeiro os itens (aba Itens)."),
        h("table", {}, h("thead", {}, h("tr", {}, ["Item", "Quantidade", "Perda %", "Quando entra", ""].map((t) => h("th", {}, t)))), corpo),
        h("button", { type: "button", class: "sec", onclick: () => { if (ativos.length) corpo.append(novaLinha(null)); } }, "Adicionar ingrediente"), " ", salvar));
    }
    sel.onchange = abrir;
    const topo = h("div", { class: "cartao" }, h("h2", {}, "Ficha técnica"),
      h("p", { class: "pequeno" }, "Quantidades da pizza: meia Grande ou uma Broto. A Grande de um sabor usa o dobro; a de dois sabores soma a ficha de cada um. Perda em branco usa o padrão da loja."), sel);
    await abrir();
    return h("div", {}, topo, editor);
  }

  async function subEtapas() {
    const etapas = await api("GET", "/etapas");
    const produtos = await api("GET", "/produtos");
    const blocos = [];
    if (!etapas.length) {
      blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Etapas de produção"), h("p", {}, "Ainda não há etapas. Posso criar as cinco: preparo da massa, massa aberta, montagem, forno e acabamento."),
        h("button", { class: "principal", onclick: async () => { try { await api("POST", "/etapas/iniciar-padrao"); ok("Etapas criadas."); desenharSub(); } catch (e) { falha(e); } } }, "Criar as etapas padrão")));
      return h("div", {}, ...blocos);
    }
    const nome = h("input", { required: "" }), fn = h("select", {}, Object.entries(FUNCOES).map(([v, t]) => h("option", { value: v }, t)));
    blocos.push(h("form", { class: "cartao", onsubmit: async (ev) => {
      ev.preventDefault();
      try { await api("POST", "/etapas", { nome: nome.value, funcao: fn.value }); ok("Etapa criada."); desenharSub(); } catch (e) { falha(e); }
    } }, h("h2", {}, "Etapas cadastradas"),
    h("table", {}, h("tbody", {}, etapas.map((e) => h("tr", {}, h("td", {}, e.nome), h("td", {}, FUNCOES[e.funcao]), h("td", {}, e.ativo ? "ativa" : "inativa"),
      h("td", {}, h("button", { type: "button", class: "sec", onclick: async () => { try { await api("PATCH", "/etapas/" + e.id, { ativo: !e.ativo }); desenharSub(); } catch (x) { falha(x); } } }, e.ativo ? "Inativar" : "Reativar")))))),
    h("div", { class: "linha" }, campo("Nova etapa (ex.: Batata palha)", nome), campo("Quem faz", fn)), h("button", { class: "principal", type: "submit" }, "Criar etapa")));
    function editorSequencia(titulo, dica, atual, aoSalvar, extra) {
      const corpo = h("tbody");
      const linha = (p) => {
        const e = h("select", {}, etapas.filter((x) => x.ativo || atual.some((a) => a.etapa_id === x.id)).map((x) => h("option", { value: x.id }, x.nome))); if (p) e.value = p.etapa_id;
        const t = h("input", { inputmode: "decimal", placeholder: "minutos", value: p && p.tempo_min != null ? String(p.tempo_min).replace(".", ",") : "" });
        const tr = h("tr", {}, h("td", {}, e), h("td", {}, t),
          h("td", {}, h("button", { type: "button", class: "sec", onclick: () => { if (tr.previousSibling) tr.parentNode.insertBefore(tr, tr.previousSibling); } }, "Subir"), " ",
            h("button", { type: "button", class: "sec", onclick: () => tr.remove() }, "Tirar")));
        tr._ler = () => ({ etapa_id: Number(e.value), tempo_min: t.value.trim() || null });
        return tr;
      };
      atual.forEach((p) => corpo.append(linha(p)));
      return h("div", { class: "cartao tabela" }, h("h2", {}, titulo), h("p", { class: "pequeno" }, dica),
        h("table", {}, h("thead", {}, h("tr", {}, ["Etapa", "Tempo (min)", ""].map((x) => h("th", {}, x)))), corpo),
        h("button", { type: "button", class: "sec", onclick: () => corpo.append(linha(null)) }, "Adicionar etapa"), " ",
        h("button", { type: "button", class: "principal", onclick: () => aoSalvar([...corpo.children].map((tr) => tr._ler())) }, "Salvar"), extra || null);
    }
    for (const tipo of ["pizza", "calzone"]) {
      const m = await api("GET", "/modelo-etapas/" + tipo);
      blocos.push(editorSequencia("Modelo de " + rotuloTipo[tipo].toLowerCase(), "Etapas que todo produto deste tipo percorre, a menos que tenha exceção. Tempo em branco até ser medido.", m.etapas,
        async (etapasNovas) => { try { await api("PUT", "/modelo-etapas/" + tipo, { etapas: etapasNovas }); ok("Modelo salvo."); desenharSub(); } catch (e) { falha(e); } }));
    }
    const selp = h("select", {}, [h("option", { value: "" }, "Escolha o produto")].concat(produtos.filter((p) => p.tipo === "pizza" || p.tipo === "calzone").map((p) => h("option", { value: p.id }, rotuloTipo[p.tipo] + ": " + p.nome))));
    const exc = h("div");
    selp.onchange = async () => {
      exc.replaceChildren(); if (!selp.value) return;
      try {
        const r = await api("GET", "/produtos/" + selp.value + "/etapas");
        const volta = r.personalizado ? h("button", { type: "button", class: "sec", onclick: async () => { try { await api("DELETE", "/produtos/" + selp.value + "/etapas"); ok("Voltou ao modelo do tipo."); selp.onchange(); } catch (e) { falha(e); } } }, "Voltar ao modelo") : null;
        exc.replaceChildren(editorSequencia(r.personalizado ? "Etapas deste produto (exceção)" : "Etapas deste produto (seguem o modelo)", "Para um sabor com etapa a mais ou a menos, como a cobertura depois do forno. Salvar cria a exceção.", r.etapas,
          async (etapasNovas) => { try { await api("PUT", "/produtos/" + selp.value + "/etapas", { etapas: etapasNovas }); ok("Etapas do produto salvas."); selp.onchange(); } catch (e) { falha(e); } }, volta ? h("span", {}, " ", volta) : null));
      } catch (e) { falha(e); }
    };
    blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Exceção por produto"), selp), exc);
    return h("div", {}, ...blocos);
  }

  async function subQualidade() {
    const q = await api("GET", "/fichas/qualidade");
    const lista = (titulo, itens, f) => h("div", { class: "cartao" }, h("h2", {}, titulo + " (" + itens.length + ")"), itens.length ? h("ul", {}, itens.map((x) => h("li", {}, f(x)))) : h("p", { class: "pequeno" }, "Nada pendente."));
    return h("div", {}, lista("Bordas e adicionais sem ficha", q.adicionais_sem_ficha, (a) => (a.tipo === "borda" ? "Borda: " : "Adicional: ") + a.nome + " (" + a.tamanho + ")"),
      lista("Produtos ativos sem ficha", q.produtos_sem_ficha, (p) => rotuloTipo[p.tipo] + ": " + p.nome),
      lista("Preparos sem ficha", q.preparos_sem_ficha, (p) => p.nome),
      lista("Bases por tamanho sem ficha (massa aberta, caixa)", q.bases_sem_ficha, (t) => t),
      lista("Pizzas e calzones sem etapas", q.produtos_sem_etapas, (p) => rotuloTipo[p.tipo] + ": " + p.nome));
  }
  await desenharSub();
}

// ---------------------------------------------------------------- Fatia 1C: vendas de balcão
const rotuloSit = { "recebido": "recebido", "em producao": "em produção", "acabado": "acabado", "despachado ou retirado": "despachado ou retirado", "cancelado": "cancelado" };
const proxSit = { "recebido": "em producao", "em producao": "acabado", "acabado": "despachado ou retirado" };
const virgula = (v) => String(v).replace(".", ",");

// getRandomValues funciona também em http na rede da loja (randomUUID só em contexto seguro)
const novaChave = () => Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, "0")).join("");

function entradaAutorizacao() {
  const u = h("input", { autocomplete: "off" }), sn = h("input", { type: "password", autocomplete: "off" });
  return { u, sn, caixa: h("div", { class: "linha" }, campo("Usuário do gerente", u), campo("Senha do gerente", sn)),
    valor: () => u.value.trim() && sn.value ? { usuario: u.value.trim(), senha: sn.value } : null };
}

async function abaVendas() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  const subs = [["novo", "Novo pedido"], ["dia", "Pedidos do dia"]];
  if (!estado.subv) estado.subv = "novo";
  const falha = (e) => msg.replaceChildren(aviso("erro", e.message));
  const ok = (t) => msg.replaceChildren(aviso("ok", t));

  async function desenharSub() {
    const nav = h("div", { class: "subnav" }, subs.map(([id, nome]) => h("button", { class: id === estado.subv ? "ativo" : "", onclick: () => { estado.subv = id; msg.replaceChildren(); desenharSub(); } }, nome)));
    let corpo;
    try { corpo = await (estado.subv === "dia" ? subPedidosDia() : subNovoPedido())(); } catch (e) { corpo = aviso("erro", e.message); }
    alvo.replaceChildren(nav, msg, corpo);
  }
  const subNovoPedido = () => novoPedido;
  const subPedidosDia = () => pedidosDia;

  // ---- novo pedido: o servidor calcula preço, limite e troco; a tela só mostra o que ele devolve
  async function novoPedido() {
    const [produtos, adicionais, param] = await Promise.all([api("GET", "/produtos?ativo=true"), api("GET", "/adicionais?ativo=true"), api("GET", "/parametros")]);
    const formas = ((param.find ? param.find((x) => x.chave === "formas_pagamento_aceitas") : null) || {}).valor || ["dinheiro", "pix", "credito", "debito"];
    const r = estado.rascunho || (estado.rascunho = { chave: novaChave(), tipo: "retirada", cliente: null, itens: [], ajuste: null, pagamentos: [], taxa: "", taxaMotivo: "", obs: "", urgente: false });
    const corpoCalculo = () => ({ tipo: r.tipo, itens: r.itens.map((i) => i.dados), ajuste: r.ajuste, taxa_entrega: r.tipo === "entrega" && r.taxa.trim() ? r.taxa.trim() : null });
    let calc = null;
    if (r.itens.length) { try { calc = await api("POST", "/pedidos/calcular", corpoCalculo()); } catch (e) { falha(e); } }
    const redesenhar = () => desenharSub();

    // cliente
    const tel = h("input", { inputmode: "tel", placeholder: "Telefone com DDD", value: r.cliente ? r.cliente.telefone : "" });
    const clienteBox = h("div", { class: "pequeno" }, r.cliente ? r.cliente.nome + " · " + (r.cliente.endereco || "sem endereço") : "Sem cliente (balcão)");
    const novoNome = h("input", { placeholder: "Nome" }), novoEnd = h("input", { placeholder: "Endereço" });
    const cadastro = h("div", {});
    const buscar = async () => {
      cadastro.replaceChildren(); msg.replaceChildren();
      try { r.cliente = await api("GET", "/clientes/por-telefone/" + encodeURIComponent(tel.value)); redesenhar(); }
      catch (e) {
        cadastro.replaceChildren(h("p", { class: "pequeno" }, "Cliente novo: cadastre na primeira compra."), h("div", { class: "linha" }, campo("Nome", novoNome), campo("Endereço", novoEnd)),
          h("button", { class: "sec", onclick: async () => {
            try { r.cliente = await api("POST", "/clientes", { nome: novoNome.value, telefone: tel.value, endereco: novoEnd.value.trim() || null }); redesenhar(); } catch (x) { falha(x); }
          } }, "Cadastrar e usar"));
      }
    };
    const cartaoCliente = h("div", { class: "cartao" }, h("h2", {}, "1. Pedido e cliente"),
      h("div", { class: "subnav" }, [["retirada", "Retirada"], ["entrega", "Entrega"]].map(([id, nome]) => h("button", { class: id === r.tipo ? "ativo" : "", onclick: () => { r.tipo = id; redesenhar(); } }, nome))),
      h("div", { class: "linha" }, campo("Telefone do cliente", tel), h("div", {}, h("label", {}, " "), h("button", { class: "sec", onclick: buscar }, "Buscar"), " ",
        r.cliente ? h("button", { class: "sec", onclick: () => { r.cliente = null; redesenhar(); } }, "Tirar") : null)), clienteBox, cadastro);

    // item em montagem
    const tipo = h("select", {}, Object.keys(rotuloTipo).map((t) => h("option", { value: t }, rotuloTipo[t])));
    const tam = h("select", {}, [["grande", "Grande"], ["broto", "Broto"]].map(([v, n]) => h("option", { value: v }, n)));
    const nomeProd = (p) => p.nome + (p.categoria ? " (" + p.categoria + ")" : "");
    const sabor1 = h("select", {}), sabor2 = h("select", {}), outro = h("select", {}), borda = h("select", {});
    const qtd = h("input", { value: "1", inputmode: "numeric" }), obsItem = h("input", { placeholder: "opcional" });
    const caixasAd = adicionais.filter((a) => a.tipo === "adicional").map((a) => { const c = h("input", { type: "checkbox", value: a.id }); return [c, a]; });
    const blocoPizza = h("div", {}), blocoOutro = h("div", {});
    const preencher = () => {
      const pizzas = produtos.filter((p) => p.tipo === "pizza");
      sabor1.replaceChildren(...pizzas.map((p) => h("option", { value: p.id }, nomeProd(p))));
      sabor2.replaceChildren(h("option", { value: "" }, "Sem segundo sabor"), ...pizzas.map((p) => h("option", { value: p.id }, nomeProd(p))));
      outro.replaceChildren(...produtos.filter((p) => p.tipo === tipo.value).map((p) => h("option", { value: p.id }, p.nome + " (" + brl(p.preco_unico) + ")")));
      borda.replaceChildren(h("option", { value: "" }, "Sem borda"), ...adicionais.filter((a) => a.tipo === "borda").map((a) => h("option", { value: a.id }, a.nome)));
      const pizza = tipo.value === "pizza";
      blocoPizza.hidden = !pizza; blocoOutro.hidden = pizza;
      sabor2.disabled = tam.value === "broto"; if (sabor2.disabled) sabor2.value = "";
    };
    tipo.onchange = preencher; tam.onchange = preencher;
    blocoPizza.replaceChildren(campo("Tamanho", tam), campo("Sabor 1", sabor1), campo("Sabor 2 (só Grande)", sabor2), campo("Borda", borda),
      h("div", {}, h("label", {}, "Adicionais"), caixasAd.map(([c, a]) => h("label", { class: "inline" }, c, " " + a.nome + " "))));
    blocoOutro.replaceChildren(campo("Produto", outro));
    preencher();
    const adicionar = () => {
      const q = parseInt(qtd.value, 10);
      let dados, rotulo;
      if (tipo.value === "pizza") {
        dados = { tipo: "pizza", produto_id: Number(sabor1.value), tamanho: tam.value, quantidade: q, observacoes: obsItem.value.trim() || null,
          sabor2_id: sabor2.value ? Number(sabor2.value) : null, adicional_ids: caixasAd.filter(([c]) => c.checked).map(([c]) => Number(c.value)).concat(borda.value ? [Number(borda.value)] : []) };
      } else dados = { tipo: tipo.value, produto_id: Number(outro.value), quantidade: q, observacoes: obsItem.value.trim() || null };
      r.itens.push({ dados }); redesenhar();
    };
    const cartaoItem = h("div", { class: "cartao" }, h("h2", {}, "2. Itens"), campo("Tipo", tipo), blocoPizza, blocoOutro,
      h("div", { class: "linha" }, campo("Quantidade", qtd), campo("Observação do item", obsItem)), h("button", { class: "principal", onclick: adicionar }, "Adicionar ao pedido"));

    // resumo
    const linhasResumo = calc ? calc.itens.map((i, ix) => h("tr", {}, h("td", {}, i.quantidade + "x " + i.descricao + (i.adicionais.length ? " + " + i.adicionais.map((a) => a.nome).join(", ") : "")),
      h("td", {}, brl(i.total)), h("td", {}, h("button", { class: "sec", onclick: () => { r.itens.splice(ix, 1); redesenhar(); } }, "Remover")))) : [];
    const ajTipo = h("select", {}, [["", "Sem ajuste"], ["desconto", "Desconto"], ["acrescimo", "Acréscimo"]].map(([v, n]) => h("option", { value: v }, n)));
    ajTipo.value = r.ajuste ? r.ajuste.tipo : "";
    const ajValor = entradaPreco(r.ajuste ? r.ajuste.valor : null), ajMotivo = h("input", { value: r.ajuste ? r.ajuste.motivo : "", placeholder: "Motivo obrigatório" });
    const aplicarAjuste = () => { r.ajuste = ajTipo.value && ajValor.value.trim() ? { tipo: ajTipo.value, valor: ajValor.value.trim(), motivo: ajMotivo.value.trim() || " " } : null; redesenhar(); };
    const taxa = entradaPreco(r.taxa || null), taxaMotivo = h("input", { value: r.taxaMotivo, placeholder: "Motivo, se diferente do padrão" });
    taxa.onchange = () => { r.taxa = taxa.value; redesenhar(); }; taxaMotivo.onchange = () => { r.taxaMotivo = taxaMotivo.value; };
    const aut = entradaAutorizacao();
    const total = calc ? Number(calc.total) : 0;
    const pago = r.pagamentos.reduce((a, p) => a + Number(String(p.valor).replace(",", ".")), 0);
    const cartaoResumo = h("div", { class: "cartao" }, h("h2", {}, "3. Resumo"),
      calc ? h("div", { class: "tabela" }, h("table", {}, h("tbody", {}, linhasResumo))) : h("p", { class: "pequeno" }, "Nenhum item ainda."),
      h("h3", {}, "Desconto ou acréscimo"), h("div", { class: "linha" }, campo("Tipo", ajTipo), campo("Valor (R$)", ajValor), campo("Motivo", ajMotivo)),
      h("button", { class: "sec", onclick: aplicarAjuste }, "Aplicar ajuste"),
      r.tipo === "entrega" ? h("div", { class: "linha" }, campo("Taxa de entrega (padrão " + (calc ? brl(calc.taxa_entrega_padrao) : "") + ")", taxa), campo("Motivo da taxa", taxaMotivo)) : null,
      calc && calc.precisa_autorizacao ? h("div", {}, aviso("erro", "Desconto de " + virgula(calc.desconto_pct) + "% passa do seu limite de " + virgula(calc.limite_desconto_pct) + "%. Um gerente confirma abaixo."), aut.caixa) : null,
      calc ? h("div", { class: "resultado" }, h("div", { class: "pequeno" }, "Itens " + brl(calc.subtotal) + " · Entrega " + brl(calc.taxa_entrega) + " · Desconto " + brl(calc.desconto) + " · Acréscimo " + brl(calc.acrescimo)),
        h("div", { class: "total" }, "Total " + brl(calc.total))) : null);

    // pagamento
    const forma = h("select", {}, formas.map((f) => h("option", { value: f }, f))), valor = entradaPreco();
    const falta = total - pago;
    const cartaoPag = h("div", { class: "cartao" }, h("h2", {}, "4. Pagamento"),
      r.pagamentos.length ? h("div", { class: "tabela" }, h("table", {}, h("tbody", {}, r.pagamentos.map((p, ix) => h("tr", {}, h("td", {}, p.forma), h("td", {}, brl(Number(String(p.valor).replace(",", ".")).toFixed(2).replace(".", ","))),
        h("td", {}, h("button", { class: "sec", onclick: () => { r.pagamentos.splice(ix, 1); redesenhar(); } }, "Remover")))))) ) : null,
      h("div", { class: "linha" }, campo("Forma", forma), campo("Valor recebido (R$)", valor), h("div", {}, h("label", {}, " "), h("button", { class: "sec", onclick: () => {
        if (!valor.value.trim()) { falha(new Error("Informe o valor recebido.")); return; }
        r.pagamentos.push({ forma: forma.value, valor: valor.value.trim() }); redesenhar(); } }, "Lançar"))),
      h("p", { class: "pequeno" }, !calc ? "" : falta > 0.004 ? "Falta receber " + brl(falta.toFixed(2)) : falta < -0.004 ? "Troco " + brl((-falta).toFixed(2)) + " (só sai do dinheiro)" : "Pago por completo."));

    const obs = h("input", { value: r.obs, placeholder: "Observações do pedido (opcional)" }); obs.onchange = () => { r.obs = obs.value; };
    const urg = h("input", { type: "checkbox" }); urg.checked = r.urgente; urg.onchange = () => { r.urgente = urg.checked; };
    const confirmar = h("button", { class: "principal", onclick: async () => {
      if (!r.itens.length) { falha(new Error("Inclua ao menos um item.")); return; }
      if (confirmar.disabled) return;
      confirmar.disabled = true;
      try {
        const criado = await api("POST", "/pedidos", { ...corpoCalculo(), cliente_id: r.cliente ? r.cliente.id : null, taxa_motivo: r.taxaMotivo.trim() || null,
          pagamentos: r.pagamentos.map((p) => ({ forma: p.forma, valor: p.valor })), urgente: r.urgente, observacoes: r.obs.trim() || null, autorizacao: aut.valor(), chave: r.chave });
        estado.rascunho = null; estado.subv = "dia";
        await desenharSub(); msg.replaceChildren(aviso("ok", "Pedido " + criado.id_dia + " registrado. Total " + brl(criado.total) + (Number(criado.troco) > 0 ? ". Troco " + brl(criado.troco) + "." : ".")));
      } catch (e) { confirmar.disabled = false; falha(e); }
    } }, "Confirmar pedido");
    const cartaoFim = h("div", { class: "cartao" }, campo("Observações", obs), h("label", { class: "inline" }, urg, " Pedido urgente"), h("div", {}, confirmar, " ",
      h("button", { class: "sec", onclick: () => { estado.rascunho = null; redesenhar(); } }, "Limpar")));
    return h("div", {}, cartaoCliente, h("div", { class: "grade" }, cartaoItem, h("div", {}, cartaoResumo, cartaoPag, cartaoFim)));
  }

  // ---- pedidos do dia
  async function pedidosDia() {
    const lista = await api("GET", "/pedidos");
    const gerente = ehGerencia();
    const painel = h("div", {});
    const linhas = lista.map((p) => {
      const acoes = [];
      const passo = async (nova) => { msg.replaceChildren(); try { await api("POST", "/pedidos/" + p.id + "/situacao", { situacao: nova }); desenharSub(); } catch (e) { falha(e); } };
      const prox = proxSit[p.situacao];
      if (prox && (gerente || prox === "despachado ou retirado")) acoes.push(h("button", { class: "sec", onclick: () => passo(prox) }, "Avançar para " + rotuloSit[prox]));
      if (p.situacao === "recebido") acoes.push(h("button", { class: "sec", onclick: async () => { try { await api("POST", "/pedidos/" + p.id + "/urgente", { urgente: !p.urgente }); desenharSub(); } catch (e) { falha(e); } } }, p.urgente ? "Tirar urgência" : "Urgente"));
      if (p.situacao !== "cancelado" && p.situacao !== "despachado ou retirado") acoes.push(h("button", { class: "sec", onclick: () => formCancelar(p) }, "Cancelar"));
      acoes.push(h("button", { class: "sec", onclick: () => detalhe(p) }, "Ver"));
      return h("tr", { class: p.situacao === "cancelado" ? "inativo" : "" }, h("td", {}, "#" + p.id_dia + (p.urgente ? " ⚡" : "")), h("td", {}, p.tipo), h("td", {}, p.cliente_nome || "Balcão"),
        h("td", {}, brl(p.total)), h("td", {}, rotuloSit[p.situacao]), h("td", {}, acoes.flatMap((a) => [a, " "])));
    });
    function formCancelar(p) {
      const motivo = h("input", { placeholder: "Motivo obrigatório" }), aut = entradaAutorizacao();
      painel.replaceChildren(h("div", { class: "cartao" }, h("h2", {}, "Cancelar pedido #" + p.id_dia), campo("Motivo", motivo), gerente ? null : h("div", {}, h("p", { class: "pequeno" }, "Pedido pago: um gerente confirma com login e senha."), aut.caixa),
        h("button", { class: "principal", onclick: async () => {
          try { await api("POST", "/pedidos/" + p.id + "/cancelar", { motivo: motivo.value, autorizacao: aut.valor() }); desenharSub(); } catch (e) { falha(e); }
        } }, "Confirmar cancelamento"), " ", h("button", { class: "sec", onclick: () => painel.replaceChildren() }, "Voltar")));
    }
    async function detalhe(p) {
      try {
        const d = await api("GET", "/pedidos/" + p.id);
        painel.replaceChildren(h("div", { class: "cartao" }, h("h2", {}, "Pedido #" + d.id_dia + " · " + rotuloSit[d.situacao]),
          h("ul", {}, d.itens.map((i) => h("li", {}, i.quantidade + "x " + i.descricao + (i.adicionais.length ? " + " + i.adicionais.map((a) => a.nome).join(", ") : "") + " · " + brl(i.preco_unit)))),
          h("p", { class: "pequeno" }, "Pagamentos: " + d.pagamentos.map((x) => x.forma + " " + brl(x.valor) + (Number(x.troco) > 0 ? " (troco " + brl(x.troco) + ")" : "")).join(", ")),
          d.ajustes.length ? h("p", { class: "pequeno" }, d.ajustes.map((a) => a.tipo + " " + brl(a.valor) + ": " + a.motivo + (a.autorizado ? " (autorizado)" : "")).join("; ")) : null,
          h("p", { class: "pequeno" }, "Histórico: " + d.eventos.map((e) => rotuloSit[e.situacao] || e.situacao).join(" → ")),
          h("button", { class: "sec", onclick: () => painel.replaceChildren() }, "Fechar")));
      } catch (e) { falha(e); }
    }
    return h("div", {}, painel, h("div", { class: "cartao tabela" }, h("h2", {}, "Pedidos de hoje (" + lista.length + ")"),
      lista.length ? h("table", {}, h("thead", {}, h("tr", {}, ["Id", "Tipo", "Cliente", "Total", "Situação", ""].map((t) => h("th", {}, t)))), h("tbody", {}, linhas)) : h("p", {}, "Nenhum pedido hoje.")));
  }
  await desenharSub();
}

// ---------------------------------------------------------------- Fatia 1D: produção
const GER = ["administrador", "proprietario", "gerente", "subgerente"];
const SUBS_PRODUCAO = [
  ["massa", "Massa", [...GER, "massa"]],
  ["montagem", "Montagem", [...GER, "pizzaiolo"]],
  ["forno", "Forno", [...GER, "pizzaiolo", "acabamento"]],
  ["acabamento", "Acabamento", [...GER, "acabamento"]],
  ["andamento", "Andamento", [...GER, "atendente", "massa", "pizzaiolo", "acabamento"]],
  ["motivos", "Motivos", GER],
];
let relogioProducao = null, etiquetaAberta = null, desenhandoProducao = false;

async function abaProducao() {
  clearInterval(relogioProducao);
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  const subs = SUBS_PRODUCAO.filter(([, , perfis]) => perfis.includes(estado.eu.perfil));
  if (!subs.some(([id]) => id === estado.subp)) estado.subp = subs[0][0];
  const falha = (e) => msg.replaceChildren(aviso("erro", e.message));
  const ok = (t) => msg.replaceChildren(aviso("ok", t));
  const acao = async (metodo, caminho, corpo, textoOk) => {
    try { const r = await api(metodo, caminho, corpo); if (textoOk) ok(textoOk); await desenharSub(); return r; } catch (e) { falha(e); }
  };
  const seletorMotivo = (lista, rotulo, aoEscolher, confirmar) => {
    const s = h("select", {}, h("option", { value: "" }, rotulo), lista.filter((m) => m.ativo).map((m) => h("option", { value: m.id }, m.nome)));
    s.onchange = () => {
      if (!s.value) return;
      if (confirmar && !window.confirm(confirmar + " Motivo: " + s.options[s.selectedIndex].text + ".")) { s.value = ""; return; }  // o select age na hora: confirma as ações que não voltam
      aoEscolher(Number(s.value));
    };
    return s;
  };
  const linhaPizza = (p) => p.tipo === "pizza" ? (p.tamanho === "grande" ? "Grande" : "Broto") + " · " + p.sabores : "Calzone · " + p.sabores;
  const grande = (t) => h("div", { class: "resultado" }, h("div", { class: "total" }, t));

  async function desenharSub() {
    if (desenhandoProducao) return;  // atualizações não se sobrepõem
    desenhandoProducao = true;
    try { await desenharSubInterno(); } finally { desenhandoProducao = false; }
  }
  async function desenharSubInterno() {
    const nav = h("div", { class: "subnav" }, subs.map(([id, nome]) => h("button", { class: id === estado.subp ? "ativo" : "", onclick: () => { estado.subp = id; etiquetaAberta = null; msg.replaceChildren(); desenharSub(); } }, nome)),
      h("button", { class: "sec", onclick: () => desenharSub() }, "Atualizar"));
    let corpo;
    try { corpo = await ({ massa: subMassa, montagem: subMontagem, forno: subForno, acabamento: subAcabamento, andamento: subAndamento, motivos: subMotivos }[estado.subp])(); }
    catch (e) { corpo = aviso("erro", e.message); }
    alvo.replaceChildren(nav, msg, corpo);
  }

  async function subMassa() {
    const [m, mot] = await Promise.all([api("GET", "/producao/massa"), api("GET", "/producao/motivos")]);
    const linhas = ["grande", "broto"].map((t) => h("tr", {}, h("td", {}, t === "grande" ? "Grande" : "Broto"), h("td", {}, String(m[t].necessidade)), h("td", {}, String(m[t].saldo)), h("td", {}, String(m[t].falta))));
    const tam = h("select", {}, [["grande", "Grande"], ["broto", "Broto"]].map(([v, n]) => h("option", { value: v }, n))), qtd = h("input", { inputmode: "numeric", value: "" });
    const vai = (caminho, texto, extra) => async () => {
      const n = parseInt(qtd.value, 10); if (!(n >= 0)) { falha(new Error("Informe a quantidade.")); return; }
      await acao("POST", caminho, { tamanho: tam.value, quantidade: n, ...(extra || {}) }, texto);
    };
    return h("div", {}, h("div", { class: "cartao tabela" }, h("h2", {}, "Massa aberta"),
      h("table", {}, h("thead", {}, h("tr", {}, ["Tamanho", "Pizzas esperando", "Saldo de massa aberta", "Falta fazer"].map((t) => h("th", {}, t)))), h("tbody", {}, linhas)),
      h("p", { class: "pequeno" }, "Saldo = última contagem + lotes − massas usadas e perdidas depois dela. Esperando = pizzas ainda na lista.")),
      h("div", { class: "cartao" }, h("h2", {}, "Lançar"), h("div", { class: "linha" }, campo("Tamanho", tam), campo("Quantidade", qtd)),
        h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: vai("/producao/massa/lote", "Lote lançado.") }, "Lançar lote de massa"), " ",
          h("button", { class: "sec", onclick: vai("/producao/massa/contagem", "Contagem informada.") }, "Informar contagem de massa aberta"), " ",
          seletorMotivo(mot.perda, "Perda de massa (escolha o motivo)", (id) => vai("/producao/massa/perda", "Perda registrada.", { motivo_id: id })()))));
  }

  async function subMontagem() {
    const [f, mot] = await Promise.all([api("GET", "/producao/fila"), api("GET", "/producao/motivos")]);
    const minha = f.pizzas.find((p) => p.minha && p.situacao === "em montagem");
    const espera = f.pizzas.filter((p) => p.situacao === "na lista");
    let topo;
    if (minha) {
      topo = h("div", { class: "cartao" }, h("h2", {}, "Pizza atual"), grande(linhaPizza(minha)),
        h("p", {}, "Pedido #" + minha.id_dia + (minha.urgente ? " · URGENTE" : "")), minha.adicionais ? h("p", {}, "Adicionais: " + minha.adicionais) : null, minha.observacoes ? h("p", {}, "Obs.: " + minha.observacoes) : null,
        h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/producao/pizzas/" + minha.id + "/produzida", undefined, "Pizza foi ao forno.") }, "Produzida (vai ao forno)"), " ",
          seletorMotivo(mot.retrocesso, "Retroceder (motivo obrigatório)", (id) => acao("POST", "/producao/pizzas/" + minha.id + "/retroceder", { motivo_id: id }, "Pizza voltou uma posição.")), " ",
          seletorMotivo(mot.perda, "Perdeu a pizza (motivo)", (id) => acao("POST", "/producao/pizzas/" + minha.id + "/perder", { motivo_id: id }, "Perda registrada."), "Registrar a perda desta pizza?")));
    } else {
      topo = h("div", { class: "cartao" }, h("h2", {}, "Montagem"), h("p", {}, espera.length ? espera.length + " pizza(s) na lista." : "Nenhuma pizza na lista."),
        espera.length ? h("button", { class: "principal", onclick: () => acao("POST", "/producao/pizzas/proxima") }, "Pegar a próxima pizza") : null);
    }
    return h("div", {}, topo, h("div", { class: "cartao tabela" }, h("h2", {}, "Fila"), espera.length ? h("table", {}, h("tbody", {}, espera.slice(0, 8).map((p) =>
      h("tr", {}, h("td", {}, "#" + p.id_dia + (p.urgente ? " ⚡" : "")), h("td", {}, linhaPizza(p)), h("td", { class: "pequeno" }, p.adicionais || ""))))) : h("p", { class: "pequeno" }, "Fila vazia.")));
  }

  async function subForno() {
    const f = await api("GET", "/producao/fila");
    const no = f.pizzas.filter((p) => p.situacao === "no forno");
    const fo = f.forno;
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Forno: " + fo.quantidade + (fo.capacidade ? " de " + fo.capacidade : "") + " pizza(s)"),
      fo.tempo_min ? h("p", { class: "pequeno" }, "Tempo de forno: " + fo.tempo_min + " min por pizza.") : null,
      fo.acima_capacidade ? aviso("erro", "Acima da capacidade do forno. O sistema só avisa.") : null),
      h("div", { class: "cartao tabela" }, h("h2", {}, "No forno"), no.length ? h("table", {}, h("tbody", {}, no.map((p) => h("tr", {}, h("td", {}, "#" + p.id_dia), h("td", {}, linhaPizza(p)),
        h("td", {}, h("button", { class: "principal", onclick: () => acao("POST", "/producao/pizzas/" + p.id + "/saiu-do-forno") }, "Saiu do forno")))))) : h("p", { class: "pequeno" }, "Forno vazio.")));
  }

  async function subAcabamento() {
    const [f, peds, mot] = await Promise.all([api("GET", "/producao/fila"), api("GET", "/producao/pedidos"), api("GET", "/producao/motivos")]);
    const prontas = f.pizzas.filter((p) => p.situacao === "saiu do forno");
    const box = h("div", {});
    const etiqueta = (e) => box.replaceChildren(h("div", { class: "cartao etiqueta" }, h("h2", {}, "Etiqueta"), grande(e.cliente + " · Id " + e.id_dia), h("p", {}, e.sabores + " (" + e.tamanho + ")"),
      h("button", { class: "sec", onclick: () => window.print() }, "Imprimir"), " ", h("button", { class: "sec", onclick: () => { etiquetaAberta = null; box.replaceChildren(); } }, "Fechar")));
    if (etiquetaAberta) etiqueta(etiquetaAberta);  // sobrevive à atualização da lista até ser fechada
    return h("div", {}, box, h("div", { class: "cartao tabela" }, h("h2", {}, "Saíram do forno"), prontas.length ? h("table", {}, h("tbody", {}, prontas.map((p) => h("tr", {}, h("td", {}, "#" + p.id_dia + " " + (p.cliente || "Balcão")), h("td", {}, linhaPizza(p)),
      h("td", {}, h("button", { class: "principal", onclick: async () => { const r = await acao("POST", "/producao/pizzas/" + p.id + "/acabada"); if (r) { etiquetaAberta = r.etiqueta; await desenharSub(); } } }, "Acabada e etiqueta"), " ",
        seletorMotivo(mot.perda, "Refazer (motivo)", (id) => acao("POST", "/producao/pizzas/" + p.id + "/refazer", { motivo_id: id }, "Pizza será refeita."), "Refazer esta pizza? A atual vira perda.")))))) : h("p", { class: "pequeno" }, "Nenhuma pizza esperando acabamento.")),
      h("div", { class: "cartao tabela" }, h("h2", {}, "Pedidos em aberto"), peds.length ? h("table", {}, h("thead", {}, h("tr", {}, ["Pedido", "Cliente", "Pizzas", "Situação", ""].map((t) => h("th", {}, t)))), h("tbody", {}, peds.map((p) => h("tr", {}, h("td", {}, "#" + p.id_dia + (p.urgente ? " ⚡" : "")),
        h("td", {}, p.cliente || "Balcão"), h("td", {}, p.acabadas + " de " + p.pizzas), h("td", {}, rotuloSit[p.situacao]),
        h("td", {}, p.situacao !== "acabado" && p.acabadas === p.pizzas ? h("button", { class: "principal", onclick: () => acao("POST", "/producao/pedidos/" + p.id + "/acabado", undefined, "Pedido acabado.") }, "Marcar pedido acabado") : null))))) : h("p", { class: "pequeno" }, "Nenhum pedido em aberto.")),
      h("p", { class: "pequeno" }, "Bebida e acompanhamento não entram nesta lista."));
  }

  async function subAndamento() {
    const peds = await api("GET", "/producao/pedidos");
    return h("div", { class: "cartao tabela" }, h("h2", {}, "Pedidos em aberto"), peds.length ? h("table", {}, h("thead", {}, h("tr", {}, ["Pedido", "Cliente", "Tipo", "Pizzas acabadas", "Situação", "Entrega calculada"].map((t) => h("th", {}, t)))),
      h("tbody", {}, peds.map((p) => h("tr", {}, h("td", {}, "#" + p.id_dia + (p.urgente ? " ⚡" : "")), h("td", {}, p.cliente || "Balcão"), h("td", {}, p.tipo), h("td", {}, p.acabadas + " de " + p.pizzas),
        h("td", {}, rotuloSit[p.situacao]), h("td", {}, p.entrega_calculada ? new Date(p.entrega_calculada).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "")))))
      : h("p", { class: "pequeno" }, "Nenhum pedido em aberto."));
  }

  async function subMotivos() {
    const m = await api("GET", "/producao/motivos");
    const vazio = !m.retrocesso.length && !m.perda.length;
    const bloco = (tipo, titulo, lista) => {
      const nome = h("input", { placeholder: "Novo motivo" }), avisa = tipo === "retrocesso" ? h("input", { type: "checkbox" }) : null;
      return h("div", { class: "cartao tabela" }, h("h2", {}, titulo), h("table", {}, h("tbody", {}, lista.map((x) => h("tr", { class: x.ativo ? "" : "inativo" }, h("td", {}, x.nome), h("td", { class: "pequeno" }, x.avisa_estoque ? "avisa Estoques" : ""),
        h("td", {}, h("button", { class: "sec", onclick: () => acao("PATCH", "/producao/motivos/" + tipo + "/" + x.id, { ativo: !x.ativo }) }, x.ativo ? "Inativar" : "Reativar")))))),
        h("div", { class: "linha" }, campo("Motivo", nome), avisa ? h("label", { class: "inline" }, avisa, " Avisa Estoques") : null,
          h("button", { class: "sec", onclick: () => acao("POST", "/producao/motivos/" + tipo, { nome: nome.value, ...(avisa ? { avisa_estoque: avisa.checked } : {}) }, "Motivo criado.") }, "Adicionar")));
    };
    return h("div", {}, vazio ? h("div", { class: "cartao" }, h("p", {}, "Nenhum motivo cadastrado."), h("button", { class: "principal", onclick: () => acao("POST", "/producao/motivos/iniciar-padrao", undefined, "Motivos iniciais criados.") }, "Criar os motivos combinados")) : null,
      bloco("retrocesso", "Motivos de retrocesso", m.retrocesso), bloco("perda", "Motivos de perda", m.perda));
  }

  await desenharSub();
  {  // tablets: a lista se atualiza sozinha, sem atropelar quem está digitando; vale para qualquer sub, pois o menu muda de sub sem recriar a aba
    relogioProducao = setInterval(() => {
      if (estado.aba !== "producao" || !estado.token) { clearInterval(relogioProducao); return; }
      const a = document.activeElement;
      if (a && (a.tagName === "INPUT" || a.tagName === "SELECT")) return;
      if (!["montagem", "forno", "acabamento"].includes(estado.subp)) return;
      desenharSub();
    }, 8000);
  }
}

async function abaCaixa() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  const subs = [["dia", "Caixa do dia"], ["entregas", "Entregas"], ["cadastros", "Motivos e maquininhas"]];
  if (!estado.subc) estado.subc = "dia";
  const falha = (e) => msg.replaceChildren(aviso("erro", e.message));
  const ok = (t) => msg.replaceChildren(aviso("ok", t));
  const acao = async (metodo, caminho, corpo, texto) => { try { await api(metodo, caminho, corpo); await desenharSub(); ok(texto); } catch (e) { falha(e); } };
  const linhaTabela = (cols, dados) => h("table", {}, h("thead", {}, h("tr", {}, cols.map((t) => h("th", {}, t)))), h("tbody", {}, dados));
  const dif = (v) => (Number(v) > 0 ? "+" : "") + brl(v);

  async function desenharSub() {
    const nav = h("div", { class: "subnav" }, subs.map(([id, nome]) => h("button", { class: id === estado.subc ? "ativo" : "", onclick: () => { estado.subc = id; msg.replaceChildren(); desenharSub(); } }, nome)));
    let corpo;
    try { corpo = await ({ dia: subDia, entregas: subEntregas, cadastros: subCadastros }[estado.subc])(); } catch (e) { corpo = aviso("erro", e.message); }
    alvo.replaceChildren(nav, msg, corpo);
  }

  async function subDia() {
    const [s, motivos] = await Promise.all([api("GET", "/caixa/hoje"), api("GET", "/caixa/motivos")]);
    const c = s.caixa;
    const avisoAnterior = c && c.situacao !== "fechado" && c.data < new Date(Date.now() - 3 * 3600 * 1000).toISOString().slice(0, 10) ? aviso("erro", "Este caixa está aberto desde " + c.data + ": conte e feche para abrir o de hoje.") : null;
    if (!c) {
      const fundo = h("input", { inputmode: "decimal", value: s.fundo_padrao ? String(s.fundo_padrao).replace(".", ",") : "", placeholder: "Fundo de troco" });
      return h("div", {}, avisoAnterior, h("div", { class: "cartao" }, h("h2", {}, "Abrir o caixa de hoje"), h("p", { class: "pequeno" }, "Conte o dinheiro da gaveta e informe o fundo de troco."),
        campo("Fundo de troco (R$)", fundo), h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/caixa/abrir", { fundo_troco: fundo.value.trim() || null }, "Caixa aberto.") }, "Abrir caixa"))));
    }
    const resumo = h("div", { class: "cartao" }, h("h2", {}, "Caixa de " + c.data + " · " + c.situacao), h("p", {}, "Fundo de troco: " + brl(c.fundo_troco)),
      s.recebido_por_forma ? h("p", {}, "Vendas do dia: " + brl(s.vendas) + " em " + s.pedidos + " pedidos. Descontos " + brl(s.descontos) + ", cancelamentos " + s.cancelamentos.n + " (" + brl(s.cancelamentos.valor) + ").")
        : h("p", { class: "pequeno" }, "Contagem cega: o esperado só aparece depois que você informar o que contou."));
    const blocos = [avisoAnterior, resumo];
    if (c.situacao === "aberto") {
      const tipo = h("select", {}, [["sangria", "Sangria (saída)"], ["suprimento", "Suprimento (entrada)"]].map(([v, n]) => h("option", { value: v }, n)));
      const motivo = h("select", {}), valor = h("input", { inputmode: "decimal", placeholder: "0,00" }), obs = h("input", { placeholder: "opcional" });
      const preencher = () => motivo.replaceChildren(...motivos.filter((m) => m.tipo === tipo.value && m.ativo).map((m) => h("option", { value: m.id }, m.nome)));
      tipo.onchange = preencher; preencher();
      const aut = entradaAutorizacao();
      blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Sangria e suprimento"),
        motivos.length ? h("div", {}, h("div", { class: "linha" }, campo("Tipo", tipo), campo("Motivo", motivo), campo("Valor (R$)", valor), campo("Observação", obs)),
          h("p", { class: "pequeno" }, "Acima do limite do parâmetro, um gerente autoriza aqui:"), aut.caixa,
          h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/caixa/movimentos", { tipo: tipo.value, motivo_id: Number(motivo.value), valor: valor.value, observacao: obs.value.trim() || null, autorizacao: aut.valor() }, "Lançamento registrado.") }, "Lançar")))
          : h("p", {}, "Cadastre os motivos na aba Motivos e maquininhas."),
        s.movimentos.length ? linhaTabela(["Tipo", "Motivo", "Valor"], s.movimentos.map((m) => h("tr", {}, h("td", {}, m.tipo), h("td", {}, m.motivo), h("td", {}, brl(m.valor))))) : null));
      const campos = s.formas.map((f) => [f, h("input", { inputmode: "decimal", placeholder: "0,00" })]);
      blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Contagem do fim do dia"),
        s.entregas_pendentes.length ? aviso("erro", "Acerte os entregadores antes de contar: " + s.entregas_pendentes.length + " entrega(s) sem acerto.") : null,
        h("p", { class: "pequeno" }, "Informe o que há de fato em cada forma (gaveta, extrato do Pix, comprovantes das maquininhas)."),
        h("div", { class: "linha" }, campos.map(([f, i]) => campo(f, i))),
        h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => { if (campos.some(([, i]) => !i.value.trim())) return falha(new Error("Preencha todas as formas (use 0 quando não houver nada).")); if (confirm("Confirmar a contagem? Ela não pode ser refeita.")) acao("POST", "/caixa/contagem", { contagens: campos.map(([f, i]) => ({ forma: f, valor: i.value.trim() })) }, "Contagem registrada."); } }, "Registrar contagem"))));
    } else {
      blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Resultado da contagem"),
        linhaTabela(["Forma", "Contado", "Esperado", "Diferença"], (s.contagens || []).map((x) => h("tr", {}, h("td", {}, x.forma), h("td", {}, brl(x.contado)), h("td", {}, brl(x.esperado)), h("td", {}, dif(x.diferenca))))),
        h("p", { class: "pequeno" }, "Tolerância: " + brl(s.tolerancia) + ".")));
      if (c.situacao === "contado") {
        const just = h("input", { placeholder: "Obrigatória se a diferença passar da tolerância" });
        const aut = entradaAutorizacao();
        blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Fechar o caixa"), campo("Justificativa", just),
          s.pode_aprovar ? h("p", { class: "pequeno" }, "Você pode aprovar a diferença.") : h("p", { class: "pequeno" }, "Se houver diferença acima da tolerância, o gerente aprova com login e senha:"),
          s.pode_aprovar ? null : aut.caixa,
          h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/caixa/fechar", { justificativa: just.value.trim() || null, autorizacao: s.pode_aprovar ? null : aut.valor() }, "Caixa fechado.") }, "Fechar caixa"))));
      } else if (c.justificativa) blocos.push(h("div", { class: "cartao" }, h("p", {}, "Justificativa: " + c.justificativa)));
    }
    if (s.estornos.length) blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Estornos do dia"), linhaTabela(["Pedido", "Forma", "Valor", "Motivo"], s.estornos.map((e) => h("tr", {}, h("td", {}, "#" + e.id_dia), h("td", {}, e.forma), h("td", {}, brl(e.valor)), h("td", {}, e.motivo))))));
    if (s.pedidos_sem_cf.length) blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Pedidos sem número de CF"), h("p", { class: "pequeno" }, "Informe o número do cupom emitido no outro software."),
      linhaTabela(["Pedido", "Total", "CF", ""], s.pedidos_sem_cf.map((p) => { const n = h("input", { placeholder: "Nº do CF" }); return h("tr", {}, h("td", {}, "#" + p.id_dia), h("td", {}, brl(p.total)), h("td", {}, n), h("td", {}, h("button", { class: "sec", onclick: () => acao("PATCH", "/pedidos/" + p.id + "/cf", { numero_cf: n.value }, "CF informado.") }, "Salvar"))); }))));
    return h("div", {}, blocos);
  }

  async function subEntregas() {
    const [lista, entregadores, s] = await Promise.all([api("GET", "/caixa/entregas"), api("GET", "/entregadores?ativo=true"), api("GET", "/caixa/hoje")]);
    const aberto = s.caixa && s.caixa.situacao === "aberto";
    const linhas = lista.map((e) => {
      const sel = h("select", {}, entregadores.map((x) => h("option", { value: x.id }, x.nome)));
      return h("tr", {}, h("td", {}, "#" + e.id_dia), h("td", {}, e.situacao), h("td", {}, brl(e.total)),
        h("td", {}, e.entregador ? e.entregador + " (" + brl(e.valor_entrega) + ")" + (e.acerto_id ? " · acertado" : "") : h("div", { class: "acoes-linha" }, sel,
          h("button", { class: "sec", disabled: !aberto, onclick: () => acao("POST", "/caixa/entregas/" + e.pedido_id, { entregador_id: Number(sel.value) }, "Entregador atribuído.") }, "Atribuir"))));
    });
    const selAc = h("select", {}, entregadores.map((x) => h("option", { value: x.id }, x.nome))), dia = h("input", { inputmode: "decimal", placeholder: "padrão" });
    return h("div", {}, aberto ? null : aviso("erro", "Abra o caixa do dia para atribuir e acertar entregas."),
      h("div", { class: "cartao" }, h("h2", {}, "Entregas de hoje"), lista.length ? linhaTabela(["Pedido", "Situação", "Total", "Entregador"], linhas) : h("p", {}, "Nenhuma entrega hoje.")),
      h("div", { class: "cartao" }, h("h2", {}, "Acerto do entregador"), h("p", { class: "pequeno" }, "O entregador devolve o dinheiro que recebeu dos clientes e recebe o valor das entregas mais a diária (uma vez por dia). Só entram pedidos já marcados como entregues."),
        h("div", { class: "linha" }, campo("Entregador", selAc), campo("Diária (R$, vazio usa o padrão)", dia)),
        h("div", { class: "acoes-linha" }, h("button", { class: "principal", disabled: !aberto, onclick: async () => {
          try { const r = await api("POST", "/caixa/acertos", { entregador_id: Number(selAc.value), diaria: dia.value.trim() || null }); await desenharSub();
            ok("Acerto feito: " + r.pedidos + " entrega(s), devido " + brl(r.total_devido) + ", saldo na gaveta " + brl(r.saldo_gaveta) + "."); } catch (e) { falha(e); } } }, "Acertar"))));
  }

  async function subCadastros() {
    const [motivos, maq, regras] = await Promise.all([api("GET", "/caixa/motivos"), api("GET", "/caixa/maquininhas"), api("GET", "/caixa/regras-recebimento")]);
    const nome = h("input", { placeholder: "Nome do motivo" }), tipo = h("select", {}, [["sangria", "Sangria"], ["suprimento", "Suprimento"]].map(([v, n]) => h("option", { value: v }, n)));
    const desp = h("input", { type: "checkbox" }), nmaq = h("input", { placeholder: "Nome da maquininha" });
    const forma = h("select", {}, ["dinheiro", "pix", "credito", "debito"].map((f) => h("option", { value: f }, f)));
    const mq = h("select", {}, h("option", { value: "" }, "Todas"), ...maq.map((m) => h("option", { value: m.id }, m.nome)));
    const taxa = h("input", { inputmode: "decimal", placeholder: "0" }), prazo = h("input", { inputmode: "numeric", placeholder: "0" });
    const vig = regras.vigentes.map((r) => h("tr", {}, h("td", {}, r.forma), h("td", {}, (maq.find((m) => m.id === r.maquininha_id) || { nome: "Todas" }).nome), h("td", {}, r.taxa_pct + "%"), h("td", {}, r.prazo_dias + " dias")));
    return h("div", {},
      h("div", { class: "cartao" }, h("h2", {}, "Motivos de sangria e suprimento"),
        motivos.length ? null : h("div", {}, h("p", {}, "Nenhum motivo cadastrado."), h("button", { class: "principal", onclick: () => acao("POST", "/caixa/motivos/iniciar-padrao", undefined, "Motivos iniciais criados.") }, "Criar os motivos combinados")),
        motivos.length ? linhaTabela(["Motivo", "Tipo", "Vira despesa", "Situação", ""], motivos.map((m) => h("tr", {}, h("td", {}, m.nome), h("td", {}, m.tipo), h("td", {}, m.vira_despesa ? "sim" : "não"), h("td", {}, m.ativo ? "ativo" : "inativo"),
          h("td", {}, h("button", { class: "sec", onclick: () => acao("PATCH", "/caixa/motivos/" + m.id, { ativo: !m.ativo }, "Motivo atualizado.") }, m.ativo ? "Inativar" : "Reativar"))))) : null,
        h("div", { class: "linha" }, campo("Nome", nome), campo("Tipo", tipo), h("label", { class: "inline" }, desp, " Sangria que vira despesa")),
        h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/caixa/motivos", { nome: nome.value, tipo: tipo.value, vira_despesa: desp.checked }, "Motivo criado.") }, "Adicionar motivo"))),
      h("div", { class: "cartao" }, h("h2", {}, "Maquininhas"),
        maq.length ? linhaTabela(["Nome", "Situação", ""], maq.map((m) => h("tr", {}, h("td", {}, m.nome), h("td", {}, m.ativo ? "ativa" : "inativa"),
          h("td", {}, h("button", { class: "sec", onclick: () => acao("PATCH", "/caixa/maquininhas/" + m.id, { ativo: !m.ativo }, "Maquininha atualizada.") }, m.ativo ? "Inativar" : "Reativar"))))) : h("p", {}, "Nenhuma maquininha cadastrada."),
        h("div", { class: "linha" }, campo("Nome", nmaq)),
        h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/caixa/maquininhas", { nome: nmaq.value }, "Maquininha criada.") }, "Adicionar maquininha"))),
      h("div", { class: "cartao" }, h("h2", {}, "Taxa e prazo de recebimento"), h("p", { class: "pequeno" }, "Cada nova regra vale daqui para frente; o histórico fica guardado."),
        vig.length ? linhaTabela(["Forma", "Maquininha", "Taxa", "Prazo"], vig) : null,
        h("div", { class: "linha" }, campo("Forma", forma), campo("Maquininha (só cartão)", mq), campo("Taxa (%)", taxa), campo("Prazo (dias)", prazo)),
        h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/caixa/regras-recebimento", { forma: forma.value, maquininha_id: mq.value ? Number(mq.value) : null, taxa_pct: taxa.value.trim() || "0", prazo_dias: parseInt(prazo.value || "0", 10) }, "Regra registrada.") }, "Registrar regra"))));
  }

  await desenharSub();
}

async function abaEstoque() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  const subs = [["saldos", "Saldos"], ["movimentar", "Lançar movimento"], ["inventario", "Inventário"], ["alertas", "Alertas"], ["locais", "Locais"]];
  if (!estado.sube) estado.sube = "saldos";
  const falha = (e) => msg.replaceChildren(aviso("erro", e.message));
  const ok = (t) => msg.replaceChildren(aviso("ok", t));
  const acao = async (metodo, caminho, corpo, texto) => { try { const r = await api(metodo, caminho, corpo); await desenharSub(); ok(texto); return r; } catch (e) { falha(e); } };
  const tabela = (cols, dados) => h("table", {}, h("thead", {}, h("tr", {}, cols.map((t) => h("th", {}, t)))), h("tbody", {}, dados));
  const num = (v) => v == null ? "" : String(v).replace(".", ",");

  async function desenharSub() {
    const nav = h("div", { class: "subnav" }, subs.map(([id, nome]) => h("button", { class: id === estado.sube ? "ativo" : "", onclick: () => { estado.sube = id; estado.itemEst = null; msg.replaceChildren(); desenharSub(); } }, nome)));
    let corpo;
    try { corpo = await ({ saldos: subSaldos, movimentar: subMovimentar, inventario: subInventario, alertas: subAlertas, locais: subLocais }[estado.sube])(); } catch (e) { corpo = aviso("erro", e.message); }
    alvo.replaceChildren(nav, msg, corpo);
  }

  async function subSaldos() {
    if (estado.itemEst) return detalheItem(estado.itemEst);
    const q = h("input", { placeholder: "Buscar item", value: estado.qEst || "" });
    const so = h("input", { type: "checkbox" }); so.checked = !!estado.atEst;
    const itens = await api("GET", "/estoque/itens?atencao=" + (estado.atEst ? "true" : "false") + (estado.qEst ? "&q=" + encodeURIComponent(estado.qEst) : ""));
    const buscar = () => { estado.qEst = q.value.trim(); estado.atEst = so.checked; desenharSub(); };
    return h("div", { class: "cartao" }, h("h2", {}, "Saldos"), h("div", { class: "acoes-linha" }, q, h("label", { class: "inline" }, so, " Só o que pede ação"), h("button", { class: "sec", onclick: buscar }, "Filtrar")),
      itens.length ? tabela(["Item", "Classe", "Saldo", "Situação", "Custo médio", ""], itens.map((i) => h("tr", {}, h("td", {}, i.nome), h("td", {}, i.classe), h("td", {}, num(i.saldo) + " " + i.unidade),
        h("td", {}, i.situacao), h("td", {}, i.custo_medio ? "R$ " + num(Number(i.custo_medio).toFixed(4)) : ""), h("td", {}, h("button", { class: "sec", onclick: () => { estado.itemEst = i.id; desenharSub(); } }, "Abrir"))))) : h("p", {}, "Nenhum item encontrado. Cadastre os itens em Fichas e etapas."));
  }

  async function detalheItem(id) {
    const [d, locais] = await Promise.all([api("GET", "/estoque/itens/" + id), api("GET", "/estoque/locais")]);
    const campo_ = (rot, valor, ph) => { const i = h("input", { value: valor == null ? "" : num(valor), placeholder: ph || "" }); return [campo(rot, i), i]; };
    const [c1, minimo] = campo_("Estoque mínimo", d.estoque_minimo), [c2, ponto] = campo_("Ponto de pedido", d.ponto_pedido), [c3, maximo] = campo_("Estoque máximo", d.estoque_maximo);
    const [c4, ucompra] = campo_("Unidade de compra (caixa, saco)", d.unidade_compra), [c5, fator] = campo_("Quantas " + d.unidade + " em cada unidade de compra", d.fator_compra);
    const critico = h("input", { type: "checkbox" }); critico.checked = d.critico;
    const lote = h("input", { type: "checkbox" }); lote.checked = d.controla_lote;
    const local = h("select", {}, h("option", { value: "" }, "Automático"), ...locais.filter((l) => l.ativo).map((l) => h("option", { value: l.id, selected: l.id === d.local_padrao_id }, l.nome)));
    const v = (i) => i.value.trim() ? i.value.trim() : null;
    return h("div", {}, h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => { estado.itemEst = null; desenharSub(); } }, "Voltar")),
      h("div", { class: "cartao" }, h("h2", {}, d.nome + " · saldo " + num(d.saldo) + " " + d.unidade + " · " + d.situacao),
        d.por_local.length ? tabela(["Local", "Saldo"], d.por_local.map((x) => h("tr", {}, h("td", {}, x.local), h("td", {}, num(x.saldo))))) : null,
        d.lotes.length ? tabela(["Lote", "Validade", "Saldo"], d.lotes.map((x) => h("tr", {}, h("td", {}, x.codigo), h("td", {}, x.validade || "sem validade"), h("td", {}, num(x.saldo))))) : null,
        h("p", { class: "pequeno" }, "Últimos custos médios: " + (d.ultimos_custos_medios.map((c) => "R$ " + Number(c.custo_medio).toFixed(4)).join(" · ") || "sem compras ainda") + ". Últimos preços pagos: " + (d.ultimos_precos_pagos.map((c) => "R$ " + Number(c.preco_unit).toFixed(4) + " (" + (c.fornecedor || "sem fornecedor") + ")").join(" · ") || "nenhum") + ".")),
      h("div", { class: "cartao" }, h("h2", {}, "Parâmetros de estoque"), h("div", { class: "linha" }, c1, c2, c3), h("div", { class: "linha" }, c4, c5, campo("Local padrão", local)),
        h("div", { class: "acoes-linha" }, h("label", { class: "inline" }, critico, " Item crítico (contagem diária)"), h("label", { class: "inline" }, lote, " Controla lote e validade"),
          h("button", { class: "principal", onclick: () => acao("PUT", "/estoque/itens/" + id + "/config", { estoque_minimo: v(minimo), ponto_pedido: v(ponto), estoque_maximo: v(maximo), unidade_compra: v(ucompra), fator_compra: v(fator) || "1",
            local_padrao_id: local.value ? Number(local.value) : null, critico: critico.checked, controla_lote: lote.checked }, "Parâmetros salvos.") }, "Salvar"))),
      h("div", { class: "cartao" }, h("h2", {}, "Últimos movimentos"), tabela(["Quando", "Tipo", "Quantidade", "Local", "Lote", "Motivo", "Quem"], d.movimentos.map((m) => h("tr", {}, h("td", {}, String(m.criado_em).slice(0, 16).replace("T", " ")), h("td", {}, m.tipo), h("td", {}, num(m.quantidade)), h("td", {}, m.local), h("td", {}, m.lote || ""), h("td", {}, m.motivo || ""), h("td", {}, m.usuario || ""))))));
  }

  async function subMovimentar() {
    const [itens, locais] = await Promise.all([api("GET", "/estoque/itens"), api("GET", "/estoque/locais")]);
    const tipo = h("select", {}, [["perda", "Perda"], ["consumo_interno", "Consumo interno (refeição, uso da loja)"], ["entrada_inicial", "Estoque inicial (gerência)"], ["transferencia", "Transferência entre locais"]].map(([v, n]) => h("option", { value: v }, n)));
    const item = h("select", {}, itens.map((i) => h("option", { value: i.id }, i.nome + " (" + i.unidade + ")")));
    const qtd = h("input", { inputmode: "decimal", placeholder: "0" }), motivo = h("input", { placeholder: "Motivo" }), custo = h("input", { inputmode: "decimal", placeholder: "só no estoque inicial" });
    const lot = h("input", { placeholder: "Lote (opcional)" }), val = h("input", { type: "date" });
    const origem = h("select", {}, h("option", { value: "" }, "Qualquer"), ...locais.filter((l) => l.ativo).map((l) => h("option", { value: l.id }, l.nome)));
    const destino = h("select", {}, ...locais.filter((l) => l.ativo).map((l) => h("option", { value: l.id }, l.nome)));
    const lancar = () => acao("POST", "/estoque/movimentos", { tipo: tipo.value, item_id: Number(item.value), quantidade: qtd.value.trim(), motivo: motivo.value.trim() || null,
      custo_unit: tipo.value === "entrada_inicial" ? custo.value.trim() || null : null, lote_codigo: lot.value.trim() || null, validade: val.value || null,
      local_id: origem.value ? Number(origem.value) : null, destino_id: tipo.value === "transferencia" ? Number(destino.value) : null }, "Movimento registrado.");
    const hist = await api("GET", "/estoque/movimentos?limite=30");
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Lançar movimento"), h("p", { class: "pequeno" }, "A entrada de compras vem do Recebimento e os ajustes vêm do Inventário. A baixa das vendas é automática, pela ficha técnica."),
      h("div", { class: "linha" }, campo("Tipo", tipo), campo("Item", item), campo("Quantidade", qtd), campo("Motivo", motivo)),
      h("div", { class: "linha" }, campo("Local de origem", origem), campo("Destino (transferência)", destino), campo("Custo unitário (R$)", custo), campo("Lote", lot), campo("Validade", val)),
      h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: lancar }, "Lançar"))),
      h("div", { class: "cartao" }, h("h2", {}, "Movimentos recentes"), tabela(["Quando", "Item", "Tipo", "Quantidade", "Local", "Motivo"], hist.map((m) => h("tr", {}, h("td", {}, String(m.criado_em).slice(0, 16).replace("T", " ")), h("td", {}, m.item), h("td", {}, m.tipo), h("td", {}, num(m.quantidade) + " " + m.unidade), h("td", {}, m.local), h("td", {}, m.motivo || ""))))));
  }

  async function subInventario() {
    const lista = await api("GET", "/estoque/inventarios");
    const aberto = lista.find((i) => i.situacao !== "fechado");
    if (!aberto) {
      const tipo = h("select", {}, [["diario", "Diário (itens críticos)"], ["mensal", "Mensal (todos os itens)"]].map(([v, n]) => h("option", { value: v }, n)));
      return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Abrir inventário"), campo("Tipo", tipo), h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/estoque/inventarios", { tipo: tipo.value }, "Inventário aberto.") }, "Abrir"))),
        h("div", { class: "cartao" }, h("h2", {}, "Anteriores"), lista.length ? tabela(["Número", "Tipo", "Situação", "Itens", "Fechado em"], lista.map((i) => h("tr", {}, h("td", {}, "#" + i.id), h("td", {}, i.tipo), h("td", {}, i.situacao), h("td", {}, i.itens), h("td", {}, i.fechado_em ? String(i.fechado_em).slice(0, 16).replace("T", " ") : "")))) : h("p", {}, "Nenhum inventário ainda.")));
    }
    const inv = await api("GET", "/estoque/inventarios/" + aberto.id);
    if (inv.situacao === "aberto") {
      const campos = inv.linhas.map((l) => [l, h("input", { inputmode: "decimal", value: l.contado == null ? "" : num(l.contado) })]);
      return h("div", { class: "cartao" }, h("h2", {}, "Inventário #" + inv.id + " · contagem cega"), h("p", { class: "pequeno" }, "Conte o que há de fato. O esperado só aparece depois da conferência."),
        tabela(["Item", "Contado"], campos.map(([l, i]) => h("tr", {}, h("td", {}, l.item + " (" + l.unidade + ")"), h("td", {}, i)))),
        h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("PUT", "/estoque/inventarios/" + inv.id + "/contagem", { linhas: campos.filter(([, i]) => i.value.trim()).map(([l, i]) => ({ item_id: l.item_id, contado: i.value.trim() })) }, "Contagem salva.") }, "Salvar contagem"),
          h("button", { class: "principal", onclick: async () => { try { await api("PUT", "/estoque/inventarios/" + inv.id + "/contagem", { linhas: campos.filter(([, i]) => i.value.trim()).map(([l, i]) => ({ item_id: l.item_id, contado: i.value.trim() })) }); if (confirm("Conferir revela o esperado e encerra a contagem. Continuar?")) await acao("POST", "/estoque/inventarios/" + inv.id + "/conferir", undefined, "Inventário conferido."); } catch (e) { falha(e); } } }, "Conferir")));
    }
    const motivos = inv.linhas.filter((l) => l.contado != null && Number(l.diferenca) !== 0).map((l) => [l, h("input", { placeholder: "Motivo da diferença" })]);
    return h("div", { class: "cartao" }, h("h2", {}, "Inventário #" + inv.id + " · conferido"),
      tabela(["Item", "Contado", "Esperado", "Diferença", "Motivo"], inv.linhas.filter((l) => l.contado != null).map((l) => { const m = motivos.find(([x]) => x.item_id === l.item_id); return h("tr", {}, h("td", {}, l.item), h("td", {}, num(l.contado)), h("td", {}, num(l.esperado)), h("td", {}, num(l.diferenca)), h("td", {}, m ? m[1] : "")); })),
      h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/estoque/inventarios/" + inv.id + "/fechar", { motivos: motivos.map(([l, i]) => ({ item_id: l.item_id, motivo: i.value.trim() })), confirmar_nao_contados: true }, "Inventário fechado e estoque ajustado.") }, "Fechar e ajustar")));
  }

  async function subAlertas() {
    const a = await api("GET", "/estoque/alertas");
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Repor"), a.repor.length ? tabela(["Item", "Saldo", "Situação"], a.repor.map((i) => h("tr", {}, h("td", {}, i.nome), h("td", {}, num(i.saldo) + " " + i.unidade), h("td", {}, i.situacao)))) : h("p", {}, "Nada abaixo do mínimo.")),
      h("div", { class: "cartao" }, h("h2", {}, "Validade (até " + a.dias_alerta + " dias)"), a.validade.length ? tabela(["Item", "Lote", "Validade", "Saldo", ""], a.validade.map((l) => h("tr", {}, h("td", {}, l.item), h("td", {}, l.codigo), h("td", {}, l.validade), h("td", {}, num(l.saldo)), h("td", {}, l.vencido ? "VENCIDO" : "")))) : h("p", {}, "Nenhum lote perto de vencer.")),
      h("div", { class: "cartao" }, h("h2", {}, "Faltas apontadas pela Produção"), h("p", {}, a.faltas_producao_24h + " retrocesso(s) por falta de insumo nas últimas 24 horas.")),
      h("div", { class: "cartao" }, h("h2", {}, "Baixas que não saíram"), a.pendencias.length ? tabela(["Tipo", "Produto", "Vezes"], a.pendencias.map((p) => h("tr", {}, h("td", {}, p.tipo === "sem_ficha" ? "Produto sem ficha técnica" : "Erro na baixa"), h("td", {}, p.produto || ""), h("td", {}, p.vezes)))) : h("p", {}, "Tudo baixando pela ficha técnica.")));
  }

  async function subLocais() {
    const locais = await api("GET", "/estoque/locais");
    const nome = h("input", { placeholder: "Nome do local" });
    return h("div", { class: "cartao" }, h("h2", {}, "Locais de armazenamento"),
      locais.length < 2 ? h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/estoque/locais/iniciar-padrao", undefined, "Locais criados.") }, "Criar freezer, câmara fria e estoque seco")) : null,
      locais.length ? tabela(["Local", "Situação", ""], locais.map((l) => h("tr", {}, h("td", {}, l.nome), h("td", {}, l.ativo ? "ativo" : "inativo"), h("td", {}, h("button", { class: "sec", onclick: () => acao("PATCH", "/estoque/locais/" + l.id, { ativo: !l.ativo }, "Local atualizado.") }, l.ativo ? "Inativar" : "Reativar"))))) : null,
      h("div", { class: "linha" }, campo("Novo local", nome)), h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/estoque/locais", { nome: nome.value }, "Local criado.") }, "Adicionar")));
  }

  await desenharSub();
}

async function abaCompras() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  const subs = [["listas", "Lista de compras"], ["pedidos", "Pedidos"], ["receber", "Recebimento"], ["fornecedores", "Fornecedores"]];
  if (!estado.subk) estado.subk = "listas";
  const falha = (e) => msg.replaceChildren(aviso("erro", e.message));
  const ok = (t) => msg.replaceChildren(aviso("ok", t));
  const acao = async (metodo, caminho, corpo, texto) => { try { const r = await api(metodo, caminho, corpo); await desenharSub(); ok(texto); return r; } catch (e) { falha(e); } };
  const tabela = (cols, dados) => h("table", {}, h("thead", {}, h("tr", {}, cols.map((t) => h("th", {}, t)))), h("tbody", {}, dados));
  const num = (v) => v == null ? "" : String(v).replace(".", ",");
  const quando = (v) => v ? String(v).slice(0, 16).replace("T", " ") : "";

  async function desenharSub() {
    const nav = h("div", { class: "subnav" }, subs.map(([id, nome]) => h("button", { class: id === estado.subk ? "ativo" : "", onclick: () => { estado.subk = id; estado.listaK = null; msg.replaceChildren(); desenharSub(); } }, nome)));
    let corpo;
    try { corpo = await ({ listas: subListas, pedidos: subPedidos, receber: subReceber, fornecedores: subFornecedores }[estado.subk])(); } catch (e) { corpo = aviso("erro", e.message); }
    alvo.replaceChildren(nav, msg, corpo);
  }

  async function subListas() {
    if (estado.listaK) return detalheLista(estado.listaK);
    const [listas, previa] = await Promise.all([api("GET", "/compras/listas"), api("GET", "/compras/necessidades")]);
    const sug = h("input", { type: "checkbox" }); sug.checked = true;
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Lista de necessidades"),
      h("p", { class: "pequeno" }, "O sistema aponta o que está no ponto de pedido ou perto de vencer. Você acrescenta o que faltar e ajusta antes de cotar."),
      previa.length ? tabela(["Item", "Saldo", "Sugerido", "Motivo"], previa.map((p) => h("tr", {}, h("td", {}, p.item), h("td", {}, num(p.saldo) + " " + p.unidade), h("td", {}, num(p.quantidade) + " " + p.unidade), h("td", {}, p.origem === "minimo" ? "Estoque baixo" : "Perto de vencer")))) : h("p", {}, "Nada abaixo do mínimo agora."),
      h("div", { class: "acoes-linha" }, h("label", { class: "inline" }, sug, " Incluir as sugestões"), h("button", { class: "principal", onclick: async () => { const r = await acao("POST", "/compras/listas", { incluir_sugeridos: sug.checked, itens: [] }, "Lista criada."); if (r) { estado.listaK = r.id; desenharSub(); } } }, "Criar lista"))),
      h("div", { class: "cartao" }, h("h2", {}, "Listas"), listas.length ? tabela(["Número", "Situação", "Itens", "Total", ""], listas.map((l) => h("tr", {}, h("td", {}, "#" + l.id), h("td", {}, l.situacao), h("td", {}, l.itens), h("td", {}, l.total ? "R$ " + num(l.total) : ""),
        h("td", {}, h("button", { class: "sec", onclick: () => { estado.listaK = l.id; desenharSub(); } }, "Abrir"))))) : h("p", {}, "Nenhuma lista ainda.")));
  }

  async function detalheLista(id) {
    const [l, forn, itensEst] = await Promise.all([api("GET", "/compras/listas/" + id), api("GET", "/compras/fornecedores?ativo=true"), api("GET", "/estoque/itens")]);
    const edita = l.situacao === "rascunho" || l.situacao === "cotando";
    const ativos = l.itens.filter((i) => !i.removido);
    const novoItem = h("select", {}, itensEst.map((i) => h("option", { value: i.id }, i.nome + " (" + i.unidade + ")"))), novaQtd = h("input", { inputmode: "decimal", placeholder: "Quantidade" });
    const linhas = l.itens.map((i) => {
      const q = h("input", { value: num(i.quantidade), disabled: !edita || i.removido }), mot = h("input", { placeholder: i.origem === "manual" ? "motivo (opcional)" : "motivo (obrigatório)", value: i.motivo || "", disabled: !edita });
      return h("tr", {}, h("td", {}, i.item + (i.removido ? " (removido)" : "")), h("td", {}, i.origem === "manual" ? "Avulso" : i.origem === "minimo" ? "Estoque baixo" : "Validade"), h("td", {}, num(i.saldo) + " " + i.unidade), h("td", {}, q),
        h("td", {}, i.cotacoes.map((c) => c.fornecedor + ": R$ " + num(c.preco_embalagem)).join(" · ")), h("td", {}, i.ultimos_precos.map((p) => "R$ " + Number(p.preco_unit).toFixed(2)).join(" · ")),
        h("td", {}, edita ? h("div", { class: "acoes-linha" }, mot, h("button", { class: "sec", onclick: () => acao("PATCH", "/compras/listas/" + id + "/itens/" + i.id, { quantidade: q.value.trim(), motivo: mot.value.trim() || null }, "Item ajustado.") }, "Ajustar"),
          h("button", { class: "sec", onclick: () => acao("PATCH", "/compras/listas/" + id + "/itens/" + i.id, { removido: !i.removido, motivo: mot.value.trim() || null }, i.removido ? "Item de volta." : "Item removido.") }, i.removido ? "Voltar" : "Remover")) : ""));
    });
    const blocos = [h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => { estado.listaK = null; desenharSub(); } }, "Voltar")),
      h("div", { class: "cartao" }, h("h2", {}, "Lista #" + l.id + " · " + l.situacao + (l.total ? " · R$ " + num(l.total) : "")),
        tabela(["Item", "Origem", "Saldo", "Quantidade", "Cotações (por unidade de compra)", "Últimos preços", ""], linhas))];
    if (edita) {
      const sel = h("select", {}, l.itens.filter((i) => !i.removido).map((i) => h("option", { value: i.id }, i.item)));
      const fo = h("select", {}, forn.map((f) => h("option", { value: f.id }, f.nome))), preco = h("input", { inputmode: "decimal", placeholder: "Preço por unidade de compra" }), prazo = h("input", { inputmode: "numeric", placeholder: "Prazo (dias)" }), cond = h("input", { placeholder: "Condição" });
      const copiar = async () => { const t = await api("GET", "/compras/listas/" + id + "/por-fornecedor"); try { await navigator.clipboard.writeText(t.texto); ok("Texto copiado para colar no WhatsApp."); } catch (e) { alert(t.texto); } };
      blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Acrescentar item"), h("div", { class: "linha" }, campo("Item", novoItem), campo("Quantidade", novaQtd)),
        h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/compras/listas/" + id + "/itens", { item_id: Number(novoItem.value), quantidade: novaQtd.value.trim() }, "Item acrescentado.") }, "Acrescentar"))),
        h("div", { class: "cartao" }, h("h2", {}, "Cotação"), h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: copiar }, "Copiar a lista para pedir preço")),
          forn.length ? h("div", {}, h("div", { class: "linha" }, campo("Item", sel), campo("Fornecedor", fo), campo("Preço (R$)", preco), campo("Prazo", prazo), campo("Condição", cond)),
            h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/compras/listas/" + id + "/cotacoes", { lista_item_id: Number(sel.value), fornecedor_id: Number(fo.value), preco: preco.value.trim(), prazo_dias: prazo.value.trim() ? parseInt(prazo.value, 10) : null, condicao: cond.value.trim() || null }, "Cotação registrada.") }, "Registrar resposta")))
            : h("p", {}, "Cadastre fornecedores na aba Fornecedores.")));
      const esc = ativos.map((i) => { const fs = h("select", {}, forn.map((f) => h("option", { value: f.id, selected: i.cotacoes[0] ? i.cotacoes[0].fornecedor_id === f.id : f.id === i.fornecedor_habitual_id }, f.nome))); const p = h("input", { placeholder: "preço (se sem cotação)", inputmode: "decimal" }); return [i, fs, p]; });
      blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Lista definitiva"), h("p", { class: "pequeno" }, "Escolha o fornecedor de cada item (o mais barato já vem marcado). Cada item vai inteiro a um fornecedor; para dividir, use a API ou peça para incluir a divisão."),
        tabela(["Item", "Quantidade", "Fornecedor", "Preço"], esc.map(([i, fs, p]) => h("tr", {}, h("td", {}, i.item), h("td", {}, num(i.quantidade)), h("td", {}, fs), h("td", {}, p)))),
        h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/compras/listas/" + id + "/definir", { escolhas: esc.map(([i, fs, p]) => ({ lista_item_id: i.id, fornecedor_id: Number(fs.value), quantidade: String(i.quantidade), preco: p.value.trim() || null })) }, "Lista definida.") }, "Definir lista"),
          h("button", { class: "sec", onclick: () => { if (confirm("Cancelar esta lista?")) acao("POST", "/compras/listas/" + id + "/cancelar", undefined, "Lista cancelada."); } }, "Cancelar lista"))));
    } else if (l.situacao === "definida") {
      blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Aguardando aprovação"), h("p", {}, "O total passa do valor de aprovação: outra pessoa, que não montou a lista, precisa aprovar."), h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/compras/listas/" + id + "/aprovar", undefined, "Lista aprovada, pedidos emitidos.") }, "Aprovar"))));
    }
    if (l.escolhas.length) blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Escolhas"), tabela(["Fornecedor", "Item", "Quantidade", "Preço", "Valor"], l.escolhas.map((e) => h("tr", {}, h("td", {}, e.fornecedor), h("td", {}, (l.itens.find((i) => i.id === e.lista_item_id) || {}).item), h("td", {}, num(e.quantidade)), h("td", {}, "R$ " + Number(e.preco_unit).toFixed(4)), h("td", {}, "R$ " + num(e.valor)))))));
    if (l.pedidos.length) blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Pedidos emitidos"), h("p", {}, l.pedidos.map((p) => "#" + p.id + " (R$ " + num(p.total) + ")").join(" · "))));
    return h("div", {}, blocos);
  }

  async function subPedidos() {
    const ped = await api("GET", "/compras/pedidos");
    return h("div", { class: "cartao" }, h("h2", {}, "Pedidos de compra"), ped.length ? tabela(["Número", "Fornecedor", "Situação", "Total", "Emitido", ""], ped.map((p) => h("tr", {}, h("td", {}, "#" + p.id), h("td", {}, p.fornecedor), h("td", {}, p.situacao), h("td", {}, "R$ " + num(p.total)), h("td", {}, quando(p.criado_em)),
      h("td", {}, p.situacao === "emitido" ? h("button", { class: "sec", onclick: () => { if (confirm("Cancelar o pedido?")) acao("POST", "/compras/pedidos/" + p.id + "/cancelar", undefined, "Pedido cancelado."); } }, "Cancelar") : "")))) : h("p", {}, "Nenhum pedido ainda."));
  }

  async function subReceber() {
    const [pedidos, forn, itens, rec] = await Promise.all([api("GET", "/compras/pedidos"), api("GET", "/compras/fornecedores?ativo=true"), api("GET", "/estoque/itens"), api("GET", "/compras/recebimentos")]);
    const abertos = pedidos.filter((p) => p.situacao === "emitido" || p.situacao === "parcial");
    const sel = h("select", {}, h("option", { value: "" }, "Compra sem pedido"), ...abertos.map((p) => h("option", { value: p.id }, "#" + p.id + " " + p.fornecedor + " (R$ " + num(p.total) + ")")));
    const fo = h("select", {}, forn.map((f) => h("option", { value: f.id }, f.nome)));
    const nota = h("input", { placeholder: "Número da nota" }), data = h("input", { type: "date", value: new Date(Date.now() - 3 * 3600 * 1000).toISOString().slice(0, 10) }), frete = h("input", { inputmode: "decimal", placeholder: "Frete" }), desc = h("input", { inputmode: "decimal", placeholder: "Desconto" });
    const venc = h("input", { type: "date" }), sangria = h("input", { inputmode: "numeric", placeholder: "Nº da sangria (compra urgente paga do caixa)" });
    const corpoItens = h("div", {}); let linhasR = [];
    const precoEmbalagem = (pre) => { const c = itens.find((i) => i.id === pre.item_id); const f = c && c.fator_compra ? Number(c.fator_compra) : 1; return (Number(pre.preco) * f).toFixed(4).replace(/0+$/, "").replace(/\.$/, ""); };
    const addLinha = (pre) => {
      const it = h("select", {}, itens.map((i) => h("option", { value: i.id, selected: pre && pre.item_id === i.id }, i.nome + " (" + i.unidade + ")"))), q = h("input", { inputmode: "decimal", placeholder: "Quantidade", value: pre ? num(pre.pendente) : "" }), p = h("input", { inputmode: "decimal", placeholder: "Preço por unidade de compra", value: pre ? num(precoEmbalagem(pre)) : "" });
      const lo = h("input", { placeholder: "Lote" }), va = h("input", { type: "date" }), dm = h("input", { placeholder: "Motivo da diferença (se houver)" });
      linhasR.push({ it, q, p, lo, va, dm }); corpoItens.append(h("div", { class: "linha" }, campo("Item", it), campo("Quantidade", q), campo("Preço (R$)", p), campo("Lote", lo), campo("Validade", va), campo("Diferença", dm)));
    };
    sel.onchange = async () => { linhasR = []; corpoItens.replaceChildren(); if (!sel.value) { addLinha(); return; } const pd = await api("GET", "/compras/pedidos/" + sel.value); fo.value = pd.fornecedor_id; pd.itens.forEach((i) => addLinha({ item_id: i.item_id, pendente: Number(i.quantidade) - Number(i.recebido), preco: i.preco_unit })); };
    addLinha();
    const enviar = () => acao("POST", "/compras/recebimentos", { pedido_id: sel.value ? Number(sel.value) : null, fornecedor_id: sel.value ? null : Number(fo.value), numero_nota: nota.value.trim() || null, data_nota: data.value,
      frete: frete.value.trim() || null, desconto: desc.value.trim() || null, vencimento: venc.value || null, movimento_caixa_id: sangria.value.trim() ? parseInt(sangria.value, 10) : null,
      itens: linhasR.map((x) => ({ item_id: Number(x.it.value), quantidade: x.q.value.trim(), preco: x.p.value.trim(), lote_codigo: x.lo.value.trim() || null, validade: x.va.value || null, diferenca_motivo: x.dm.value.trim() || null })) }, "Entrega recebida e estoque atualizado.");
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Receber entrega e dar entrada na nota"), h("p", { class: "pequeno" }, "Confira a entrega contra o pedido. Quantidade ou preço diferente do pedido pede o motivo. A nota digitada aqui alimenta Contas a Pagar."),
      h("div", { class: "linha" }, campo("Pedido", sel), campo("Fornecedor (sem pedido)", fo), campo("Nota", nota), campo("Data da nota", data), campo("Vencimento", venc)), h("div", { class: "linha" }, campo("Frete (R$)", frete), campo("Desconto (R$)", desc), campo("Sangria do caixa", sangria)),
      corpoItens, h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => addLinha() }, "Mais um item"), h("button", { class: "principal", onclick: (ev) => { ev.target.disabled = true; enviar().finally(() => { ev.target.disabled = false; }); } }, "Registrar recebimento"))),
      h("div", { class: "cartao" }, h("h2", {}, "Notas recebidas"), rec.length ? tabela(["Nota", "Fornecedor", "Data", "Total", "Vencimento", "Conferente"], rec.map((r) => h("tr", {}, h("td", {}, r.numero_nota || "sem nota"), h("td", {}, r.fornecedor), h("td", {}, r.data_nota), h("td", {}, "R$ " + num(r.total_nota)), h("td", {}, r.vencimento || ""), h("td", {}, r.conferente || "")))) : h("p", {}, "Nenhum recebimento ainda.")));
  }

  async function subFornecedores() {
    const lista = await api("GET", "/compras/fornecedores");
    const nome = h("input", { placeholder: "Nome" }), contato = h("input", { placeholder: "Contato" }), tel = h("input", { placeholder: "Telefone" }), prazo = h("input", { inputmode: "numeric", placeholder: "Prazo (dias)" });
    const forma = h("select", {}, h("option", { value: "" }, "Forma de pagamento"), ...["dinheiro", "pix", "boleto", "cartao", "prazo", "outro"].map((f) => h("option", { value: f }, f)));
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Novo fornecedor"), h("div", { class: "linha" }, campo("Nome", nome), campo("Contato", contato), campo("Telefone", tel), campo("Prazo", prazo), campo("Pagamento", forma)),
      h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/compras/fornecedores", { nome: nome.value, contato: contato.value.trim() || null, telefone: tel.value.trim() || null, prazo_dias: prazo.value.trim() ? parseInt(prazo.value, 10) : null, forma_pagamento: forma.value || null }, "Fornecedor criado.") }, "Adicionar"))),
      h("div", { class: "cartao" }, h("h2", {}, "Fornecedores"), lista.length ? tabela(["Nome", "Contato", "Prazo", "Pagamento", "Situação", ""], lista.map((f) => h("tr", {}, h("td", {}, f.nome), h("td", {}, (f.contato || "") + " " + (f.telefone || "")), h("td", {}, f.prazo_dias == null ? "" : f.prazo_dias + " dias"), h("td", {}, f.forma_pagamento || ""), h("td", {}, f.ativo ? "ativo" : "inativo"),
        h("td", {}, h("button", { class: "sec", onclick: () => acao("PATCH", "/compras/fornecedores/" + f.id, { ativo: !f.ativo }, "Fornecedor atualizado.") }, f.ativo ? "Inativar" : "Reativar"))))) : h("p", {}, "Nenhum fornecedor ainda.")));
  }

  await desenharSub();
}

async function abaContas() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  const subs = [["fluxo", "Fluxo de caixa"], ["pagar", "A pagar"], ["receber", "A receber"], ["lancar", "Lançar"], ["conciliar", "Conciliação"], ["cadastros", "Cadastros"]];
  if (!estado.subc) estado.subc = "fluxo";
  const falha = (e) => msg.replaceChildren(aviso("erro", e.message));
  const ok = (t) => msg.replaceChildren(aviso("ok", t));
  const acao = async (metodo, caminho, corpo, texto) => { try { const r = await api(metodo, caminho, corpo); await desenharSub(); ok(texto); return r; } catch (e) { falha(e); } };
  const tabela = (cols, dados) => h("table", {}, h("thead", {}, h("tr", {}, cols.map((t) => h("th", {}, t)))), h("tbody", {}, dados));
  const num = (v) => v == null ? "" : String(v).replace(".", ",");
  const reais = (v) => v == null ? "" : "R$ " + num(v);
  const dia = (iso) => iso ? String(iso).slice(8, 10) + "/" + String(iso).slice(5, 7) + "/" + String(iso).slice(0, 4) : "";
  const hoje = () => new Date(Date.now() - 3 * 3600 * 1000).toISOString().slice(0, 10);
  const podeAprovar = ["administrador", "proprietario"].includes(estado.eu.perfil);

  async function desenharSub() {
    const nav = h("div", { class: "subnav" }, subs.map(([id, nome]) => h("button", { class: id === estado.subc ? "ativo" : "", onclick: () => { estado.subc = id; msg.replaceChildren(); desenharSub(); } }, nome)));
    let corpo;
    try { corpo = await ({ fluxo: subFluxo, pagar: () => subTitulos("pagar"), receber: () => subTitulos("receber"), lancar: subLancar, conciliar: subConciliar, cadastros: subCadastros }[estado.subc])(); } catch (e) { corpo = aviso("erro", e.message); }
    alvo.replaceChildren(nav, msg, corpo);
  }

  async function subFluxo() {
    const f = await api("GET", "/contas/fluxo?dias=30");
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Saldo das contas hoje: " + reais(f.saldo_atual)),
      h("p", { class: "pequeno" }, "A projeção usa os títulos em aberto, no vencimento (atrasados contam hoje). O dinheiro da gaveta fica no Fechamento de Caixa. Menor saldo previsto: " + reais(f.menor_saldo) + "."),
      f.contas.length ? tabela(["Conta", "Saldo"], f.contas.map((c) => h("tr", {}, h("td", {}, c.nome), h("td", {}, reais(c.saldo))))) : h("p", {}, "Cadastre uma conta bancária na aba Cadastros.")),
      h("div", { class: "cartao" }, h("h2", {}, "Próximos 30 dias (os 7 primeiros em destaque)"),
        tabela(["Dia", "Entradas", "Saídas", "Saldo previsto"], f.projecao.map((p) => h("tr", { class: p.destaque ? "destaque" : "" }, h("td", {}, dia(p.data)), h("td", {}, reais(p.entradas)), h("td", {}, reais(p.saidas)), h("td", { class: p.negativo ? "negativo" : "" }, reais(p.saldo)))))),
      h("div", { class: "cartao" }, h("h2", {}, "Realizado nos últimos 30 dias"), f.realizado_30d.length ? tabela(["Dia", "Entradas", "Saídas"], f.realizado_30d.map((r) => h("tr", {}, h("td", {}, dia(r.data)), h("td", {}, reais(r.entradas)), h("td", {}, reais(r.saidas))))) : h("p", {}, "Nenhuma baixa em conta no período.")));
  }

  async function subTitulos(sentido) {
    const [ts, contas] = await Promise.all([api("GET", "/contas/titulos?sentido=" + sentido), api("GET", "/contas/contas-bancarias")]);
    const abertos = ts.filter((t) => ["aberto", "parcial"].includes(t.situacao) || !t.aprovado && t.situacao !== "cancelado");
    const feitos = ts.filter((t) => !abertos.includes(t)).slice(-30).reverse();
    const linha = (t) => {
      const forma = h("select", {}, ["pix", "dinheiro", "boleto", "transferencia", "credito", "debito"].map((f) => h("option", { value: f }, f)));
      const conta = h("select", {}, contas.filter((c) => c.ativo).map((c) => h("option", { value: c.id }, c.nome)));
      const valor = h("input", { inputmode: "decimal", placeholder: "Valor", value: num(t.saldo) }), desc = h("input", { inputmode: "decimal", placeholder: sentido === "receber" ? "Taxa/desconto" : "Desconto" }), jur = h("input", { inputmode: "decimal", placeholder: "Juros e multa" });
      const baixar = (ev) => { ev.target.disabled = true; return acao("POST", "/contas/titulos/" + t.id + "/baixas", { forma: forma.value, conta_id: Number(conta.value), valor: valor.value.trim() || null, desconto: desc.value.trim() || "0", juros: jur.value.trim() || "0" }, "Baixa registrada.").finally(() => { ev.target.disabled = false; }); };
      const cancelar = () => { const m = prompt("Motivo do cancelamento:"); if (m) acao("POST", "/contas/titulos/" + t.id + "/cancelar", { motivo: m }, "Título cancelado."); };
      return h("tr", { class: t.atrasado ? "atrasado" : "" }, h("td", {}, dia(t.vencimento) + (t.atrasado ? " (" + t.dias_atraso + " d de atraso)" : "")), h("td", {}, t.descricao + (t.parcela_total ? " " + t.parcela_num + "/" + t.parcela_total : "")), h("td", {}, t.tipo_despesa || t.canal || ""),
        h("td", {}, reais(t.valor)), h("td", {}, reais(t.saldo)),
        h("td", {}, !t.aprovado ? h("div", { class: "acoes-linha" }, "Aguarda aprovação", podeAprovar ? h("button", { class: "sec", onclick: () => acao("POST", "/contas/titulos/" + t.id + "/aprovar", undefined, "Título aprovado.") }, "Aprovar") : "")
          : h("div", { class: "acoes-linha" }, forma, conta, valor, desc, jur, h("button", { class: "sec", onclick: baixar }, sentido === "pagar" ? "Pagar" : "Receber"),
            ["manual", "parcela", "recorrencia"].includes(t.origem_tipo) && t.situacao === "aberto" ? h("button", { class: "sec", onclick: cancelar }, "Cancelar") : "")));
    };
    const total = abertos.reduce((s, t) => s + Number(t.saldo), 0);
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, (sentido === "pagar" ? "A pagar" : "A receber") + " em aberto: " + reais(total.toFixed(2))),
      abertos.length ? tabela(["Vencimento", "Descrição", "Tipo", "Valor", "Saldo", ""], abertos.map(linha)) : h("p", {}, "Nada em aberto."),
      !contas.length ? h("p", { class: "pequeno" }, "Para dar baixa, cadastre antes uma conta bancária (ou conta 'caixa físico') na aba Cadastros.") : ""),
      h("div", { class: "cartao" }, h("h2", {}, "Últimos baixados ou cancelados"), feitos.length ? tabela(["Vencimento", "Descrição", "Valor", "Situação", "Taxa real"], feitos.map((t) => h("tr", {}, h("td", {}, dia(t.vencimento)), h("td", {}, t.descricao), h("td", {}, reais(t.valor)), h("td", {}, t.situacao), h("td", {}, t.taxa_real_pct ? num(t.taxa_real_pct) + "%" : "")))) : h("p", {}, "Nada ainda.")));
  }

  async function subLancar() {
    const [tipos, forn] = await Promise.all([api("GET", "/contas/tipos-despesa"), api("GET", "/compras/fornecedores?ativo=true")]);
    const sent = h("select", {}, h("option", { value: "pagar" }, "A pagar"), h("option", { value: "receber" }, "A receber"));
    const desc = h("input", { placeholder: "Descrição" }), valor = h("input", { inputmode: "decimal", placeholder: "Valor total" }), venc = h("input", { type: "date", value: hoje() }), parc = h("input", { inputmode: "numeric", value: "1" });
    const tipo = h("select", {}, h("option", { value: "" }, "Tipo de despesa"), ...tipos.filter((t) => t.ativo).map((t) => h("option", { value: t.id }, t.nome)));
    const fo = h("select", {}, h("option", { value: "" }, "Fornecedor (opcional)"), ...forn.map((f) => h("option", { value: f.id }, f.nome))), canal = h("input", { placeholder: "Canal (a receber)" }), comp = h("input", { placeholder: "Comprovante" });
    return h("div", { class: "cartao" }, h("h2", {}, "Lançar título"), h("p", { class: "pequeno" }, "Notas de compra, despesas do caixa, acertos de entregador, vendas em cartão e Pix e despesas recorrentes entram sozinhas. Aqui vai o que não tem origem em outra área."),
      !tipos.length ? h("p", {}, "Crie os tipos de despesa na aba Cadastros.") : "",
      h("div", { class: "linha" }, campo("Tipo", sent), campo("Descrição", desc), campo("Valor (R$)", valor), campo("1º vencimento", venc), campo("Parcelas", parc)),
      h("div", { class: "linha" }, campo("Despesa", tipo), campo("Fornecedor", fo), campo("Canal", canal), campo("Comprovante", comp)),
      h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/contas/titulos", { sentido: sent.value, descricao: desc.value, valor: valor.value.trim(), vencimento: venc.value, parcelas: parseInt(parc.value, 10) || 1,
        tipo_despesa_id: tipo.value ? Number(tipo.value) : null, fornecedor_id: fo.value ? Number(fo.value) : null, canal: canal.value.trim() || null, comprovante: comp.value.trim() || null }, "Título lançado.") }, "Lançar")));
  }

  async function subConciliar() {
    const contas = (await api("GET", "/contas/contas-bancarias")).filter((c) => c.ativo);
    if (!contas.length) return h("div", { class: "cartao" }, h("p", {}, "Cadastre uma conta bancária na aba Cadastros."));
    if (!estado.contaC || !contas.some((c) => c.id === estado.contaC)) estado.contaC = contas[0].id;
    const sel = h("select", { onchange: () => { estado.contaC = Number(sel.value); desenharSub(); } }, contas.map((c) => h("option", { value: c.id, selected: c.id === estado.contaC }, c.nome)));
    const p = await api("GET", "/contas/conciliacao/" + estado.contaC);
    const ed = h("input", { type: "date", value: hoje() }), edesc = h("input", { placeholder: "Descrição do extrato" }), ev = h("input", { inputmode: "decimal", placeholder: "Valor (negativo para saída)" });
    let ext = null, bx = null;
    const casar = () => ext && bx ? acao("POST", "/contas/conciliacao", { extrato_id: ext, baixa_id: bx }, "Casados.") : falha(new Error("Escolha uma linha do extrato e uma baixa."));
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Conta"), h("div", { class: "linha" }, campo("Conta", sel)), h("h2", {}, "Lançar linha do extrato"),
      h("div", { class: "linha" }, campo("Data", ed), campo("Descrição", edesc), campo("Valor (R$)", ev)),
      h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/contas/extrato", { conta_id: estado.contaC, data: ed.value, descricao: edesc.value, valor: ev.value.trim() }, "Linha lançada.") }, "Lançar"))),
      h("div", { class: "cartao" }, h("h2", {}, "Casar extrato com baixa"), h("p", { class: "pequeno" }, "Os valores precisam ser iguais. Se o banco pagou menos, ajuste a baixa com o desconto (taxa) antes."),
        h("div", { class: "linha" }, h("div", {}, h("h3", {}, "Extrato"), p.extrato.length ? p.extrato.map((e) => h("label", { class: "inline" }, h("input", { type: "radio", name: "ext", onchange: () => { ext = e.id; } }), " " + dia(e.data) + " " + e.descricao + " " + reais(e.valor))) : h("p", {}, "Tudo casado.")),
          h("div", {}, h("h3", {}, "Baixas"), p.baixas.length ? p.baixas.map((b) => h("label", { class: "inline" }, h("input", { type: "radio", name: "bx", onchange: () => { bx = b.id; } }), " " + dia(b.data) + " " + b.descricao + " " + reais(b.valor_com_sinal))) : h("p", {}, "Tudo casado."))),
        h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: casar }, "Casar"))));
  }

  async function subCadastros() {
    const [contas, tipos, canais, rec] = await Promise.all([api("GET", "/contas/contas-bancarias"), api("GET", "/contas/tipos-despesa"), api("GET", "/contas/canais"), api("GET", "/contas/recorrentes")]);
    const cn = h("input", { placeholder: "Nome da conta" }), cb = h("input", { placeholder: "Banco" }), cs = h("input", { inputmode: "decimal", placeholder: "Saldo inicial" }), cd = h("input", { type: "date", value: hoje() });
    const ct = h("select", {}, [["corrente", "Corrente"], ["poupanca", "Poupança"], ["caixa_fisico", "Caixa físico"], ["outro", "Outro"]].map(([v, n]) => h("option", { value: v }, n)));
    const tn = h("input", { placeholder: "Nome do tipo" }), tnat = h("select", {}, ["fixa", "variavel", "pessoal", "tributo", "financiamento", "retirada", "outra"].map((n) => h("option", { value: n }, n)));
    const kn = h("input", { placeholder: "Canal (Anota Aí, iFood)" }), kt = h("input", { inputmode: "decimal", placeholder: "Taxa %" }), kp = h("input", { inputmode: "numeric", placeholder: "Prazo (dias)" });
    const rd = h("input", { placeholder: "Descrição" }), rt = h("select", {}, tipos.filter((t) => t.ativo).map((t) => h("option", { value: t.id }, t.nome))), rv = h("input", { inputmode: "decimal", placeholder: "Valor" }), rdia = h("input", { inputmode: "numeric", placeholder: "Dia (1 a 28)" }), ri = h("input", { type: "date", value: hoje() });
    const ativar = (caminho, x) => h("button", { class: "sec", onclick: () => acao("PATCH", caminho + x.id, { ativo: !x.ativo }, "Atualizado.") }, x.ativo ? "Inativar" : "Reativar");
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Contas bancárias"), tabela(["Conta", "Tipo", "Saldo", ""], contas.map((c) => h("tr", {}, h("td", {}, c.nome + (c.banco ? " (" + c.banco + ")" : "")), h("td", {}, c.tipo), h("td", {}, reais(c.saldo)), h("td", {}, ativar("/contas/contas-bancarias/", c))))),
      h("div", { class: "linha" }, campo("Nome", cn), campo("Banco", cb), campo("Tipo", ct), campo("Saldo inicial", cs), campo("Em", cd)),
      h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/contas/contas-bancarias", { nome: cn.value, banco: cb.value.trim() || null, tipo: ct.value, saldo_inicial: cs.value.trim() || "0", saldo_inicial_data: cd.value }, "Conta criada.") }, "Adicionar conta"))),
      h("div", { class: "cartao" }, h("h2", {}, "Tipos de despesa"), tipos.length ? h("p", {}, tipos.map((t) => t.nome + " (" + t.natureza + ")" + (t.ativo ? "" : " [inativo]")).join(" · ")) : h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/contas/tipos-despesa/iniciar-padrao", undefined, "Tipos criados.") }, "Criar os tipos padrão")),
        h("div", { class: "linha" }, campo("Nome", tn), campo("Natureza", tnat)), h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/contas/tipos-despesa", { nome: tn.value, natureza: tnat.value }, "Tipo criado.") }, "Adicionar tipo"))),
      h("div", { class: "cartao" }, h("h2", {}, "Canais de repasse"), canais.length ? tabela(["Canal", "Taxa", "Prazo", ""], canais.map((c) => h("tr", {}, h("td", {}, c.canal), h("td", {}, num(c.taxa_pct) + "%"), h("td", {}, c.prazo_dias + " dias"), h("td", {}, ativar("/contas/canais/", c))))) : h("p", {}, "Nenhum canal."),
        h("div", { class: "linha" }, campo("Canal", kn), campo("Taxa %", kt), campo("Prazo", kp)), h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/contas/canais", { canal: kn.value, taxa_pct: kt.value.trim() || "0", prazo_dias: parseInt(kp.value, 10) || 0 }, "Canal criado.") }, "Adicionar canal"))),
      h("div", { class: "cartao" }, h("h2", {}, "Despesas recorrentes"), rec.length ? tabela(["Descrição", "Tipo", "Valor", "Dia", ""], rec.map((r) => h("tr", {}, h("td", {}, r.descricao), h("td", {}, r.tipo), h("td", {}, reais(r.valor)), h("td", {}, r.dia_vencimento), h("td", {}, ativar("/contas/recorrentes/", r))))) : h("p", {}, "Nenhuma recorrente."),
        h("div", { class: "linha" }, campo("Descrição", rd), campo("Tipo", rt), campo("Valor", rv), campo("Dia", rdia), campo("Início", ri)),
        h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/contas/recorrentes", { descricao: rd.value, tipo_despesa_id: Number(rt.value), valor: rv.value.trim(), dia_vencimento: parseInt(rdia.value, 10), inicio: ri.value }, "Recorrente criada.") }, "Adicionar recorrente"))));
  }

  await desenharSub();
}

async function abaBi() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  const subs = [["painel", "Painel do dia"], ["dre", "DRE"], ["lucro", "Lucratividade"], ["prod", "Produção"]];
  if (!estado.subbi) estado.subbi = "painel";
  const num = (v) => v == null ? "—" : String(v).replace(".", ",");
  const reais = (v) => v == null ? "—" : "R$ " + num(v);
  const pct = (v) => v == null ? "—" : num(v) + "%";
  const tabela = (cols, dados) => h("table", {}, h("thead", {}, h("tr", {}, cols.map((t) => h("th", {}, t)))), h("tbody", {}, dados));
  const mesAtual = () => new Date(Date.now() - 3 * 3600 * 1000).toISOString().slice(0, 7);
  if (!estado.mesBi) estado.mesBi = mesAtual();
  const seletorMes = () => { const m = h("input", { type: "month", value: estado.mesBi, onchange: () => { estado.mesBi = m.value || mesAtual(); desenhar(); } }); return h("label", {}, "Mês", m); };
  const cartao = (rotulo, valor, destaque) => h("div", { class: "cartao" + (destaque ? " destaque" : "") }, h("p", { class: "pequeno" }, rotulo), h("h2", {}, valor));
  async function baixarCsv(caminho, nome) {
    try {
      const r = await fetch("/api" + caminho, { headers: { Authorization: "Bearer " + estado.token } });
      if (!r.ok) throw new Error("Erro " + r.status);
      const url = URL.createObjectURL(await r.blob());
      const a = h("a", { href: url, download: nome }); document.body.append(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    } catch (e) { msg.replaceChildren(aviso("erro", e.message)); }
  }

  async function subPainel() {
    const p = await api("GET", "/bi/painel");
    const d = new Set(p.destaques);
    const mapa = { alta: "erro", media: "aviso" };
    return h("div", {}, h("div", { class: "grade" },
      cartao("Vendas de hoje", reais(p.vendas) + (p.variacao_pct != null ? " (" + pct(p.variacao_pct) + " na semana)" : ""), d.has("vendas")),
      cartao("Pedidos", String(p.pedidos) + " · cancelados " + p.cancelados), cartao("Ticket médio", reais(p.ticket_medio)),
      cartao("Tempo médio", p.tempo_medio_min + " min"), cartao("Entregues com atraso", String(p.entregues_com_atraso)), cartao("Perdas", String(p.perdas)),
      cartao("Diferença de caixa", reais(p.diferenca_caixa)), cartao("CMV do mês", reais(p.cmv_mes) + " (" + pct(p.cmv_pct) + ")", d.has("cmv_mes")),
      p.saldo_contas != null ? cartao("Saldo das contas", reais(p.saldo_contas), d.has("saldo_contas")) : ""),
      h("div", { class: "cartao" }, h("h2", {}, "Alertas"), p.alertas.length ? p.alertas.map((a) => aviso(mapa[a.gravidade] || "ok", a.texto)) : h("p", {}, "Nenhum alerta agora.")));
  }

  async function subDre() {
    const d = await api("GET", "/bi/dre?mes=" + estado.mesBi);
    const linhas = [["Receita bruta", d.receita_bruta], ["(-) Descontos", d.descontos], ["= Receita", d.receita], ["(-) CMV", d.cmv], ["(-) Taxas de cartão", d.taxas_cartao], ["(-) Taxas de canal", d.taxas_canal],
      ["(-) Entregas", d.entregas], ["(-) Outras variáveis", d.outras_variaveis], ["= Margem de contribuição", d.margem_contribuicao], ["(-) Despesas fixas", d.fixas], ["(-) Outras fixas", d.outras_fixas],
      ["(-) Pessoal", d.pessoal], ["= EBITDA", d.ebitda], ["(-) Depreciação", d.depreciacao], ["= Resultado operacional", d.resultado_operacional], ["Tributos (fora do resultado)", d.tributos], ["Ponto de equilíbrio", d.ponto_equilibrio]];
    return h("div", { class: "cartao" }, h("h2", {}, "DRE de " + estado.mesBi + (d.cmv_fechado ? " (CMV fechado)" : " (CMV em andamento)")), h("div", { class: "linha" }, seletorMes(),
      h("button", { class: "sec", onclick: () => baixarCsv("/bi/dre.csv?mes=" + estado.mesBi, "dre_" + estado.mesBi + ".csv") }, "Baixar CSV")),
      h("p", { class: "pequeno" }, "Por competência. Linhas que revelam a folha aparecem só para quem pode ver salários."),
      tabela(["Linha", "Valor"], linhas.map(([n, v]) => h("tr", {}, h("td", {}, n), h("td", {}, reais(v))))));
  }

  const tab = (nome, lista) => h("div", { class: "cartao" }, h("h2", {}, nome), tabela(["Nome", "Qtd", "Receita", "Custo", "Margem", "Margem %"], lista.map((x) => h("tr", {}, h("td", {}, x.nome), h("td", {}, String(x.quantidade)), h("td", {}, reais(x.receita)), h("td", {}, reais(x.custo)), h("td", {}, reais(x.margem)), h("td", {}, pct(x.margem_pct))))));
  async function subLucro() {
    const l = await api("GET", "/bi/lucratividade?mes=" + estado.mesBi);
    return h("div", {}, h("div", { class: "linha" }, seletorMes()), h("p", { class: "pequeno" }, "Custo pela ficha técnica; sabor sem ficha ou insumo sem custo aparece com custo menor que o real."),
      tab("Por sabor", l.por_sabor), tab("Por categoria", l.por_categoria), tab("Por canal", l.por_canal), tab("Por dia da semana", l.por_dia_semana));
  }

  async function subProd() {
    const p = await api("GET", "/bi/producao?mes=" + estado.mesBi);
    return h("div", {}, h("div", { class: "linha" }, seletorMes()), h("div", { class: "grade" }, cartao("Pizzas acabadas", String(p.pizzas_acabadas)), cartao("Refações", String(p.refacoes))),
      h("div", { class: "cartao" }, h("h2", {}, "Tempo médio por etapa"), tabela(["Etapa", "Ocorrências", "Minutos"], p.tempo_por_etapa.map((e) => h("tr", {}, h("td", {}, e.etapa), h("td", {}, String(e.ocorrencias)), h("td", {}, num(e.minutos_medios)))))),
      h("div", { class: "cartao" }, h("h2", {}, "Retrocessos por motivo"), tabela(["Motivo", "Quantidade"], p.retrocessos_por_motivo.map((e) => h("tr", {}, h("td", {}, e.motivo), h("td", {}, String(e.quantidade)))))),
      h("div", { class: "cartao" }, h("h2", {}, "Perdas por motivo"), tabela(["Motivo", "Quantidade"], p.perdas_por_motivo.map((e) => h("tr", {}, h("td", {}, e.motivo), h("td", {}, String(e.quantidade)))))));
  }

  async function desenhar() {
    const nav = h("div", { class: "subnav" }, subs.map(([id, nome]) => h("button", { class: id === estado.subbi ? "ativo" : "", onclick: () => { estado.subbi = id; msg.replaceChildren(); desenhar(); } }, nome)));
    let corpo;
    try { corpo = await ({ painel: subPainel, dre: subDre, lucro: subLucro, prod: subProd }[estado.subbi])(); } catch (e) { corpo = aviso("erro", e.message); }
    alvo.replaceChildren(nav, msg, corpo);
  }
  await desenhar();
  clearInterval(estado.timerBi);
  estado.timerBi = setInterval(() => { if (!alvo.isConnected) { clearInterval(estado.timerBi); return; } if (estado.subbi === "painel") desenhar(); }, 180000);
}

async function abaCustos() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  const subs = [["produtos", "Custo dos produtos"], ["cmv", "CMV"], ["resultado", "Resultado do mês"], ["fatores", "Fator de correção"]];
  if (!estado.subu) estado.subu = "produtos";
  const falha = (e) => msg.replaceChildren(aviso("erro", e.message));
  const ok = (t) => msg.replaceChildren(aviso("ok", t));
  const tabela = (cols, dados) => h("table", {}, h("thead", {}, h("tr", {}, cols.map((t) => h("th", {}, t)))), h("tbody", {}, dados));
  const num = (v) => v == null ? "" : String(v).replace(".", ",");
  const reais = (v) => v == null ? "" : "R$ " + num(v);
  const pct = (v) => v == null ? "" : num(v) + "%";
  const mesAtual = () => new Date(Date.now() - 3 * 3600 * 1000).toISOString().slice(0, 7);
  if (!estado.mesC) estado.mesC = mesAtual();

  async function desenharSub() {
    const nav = h("div", { class: "subnav" }, subs.map(([id, nome]) => h("button", { class: id === estado.subu ? "ativo" : "", onclick: () => { estado.subu = id; msg.replaceChildren(); desenharSub(); } }, nome)));
    let corpo;
    try { corpo = await ({ produtos: subProdutos, cmv: subCmv, resultado: subResultado, fatores: subFatores }[estado.subu])(); } catch (e) { corpo = aviso("erro", e.message); }
    alvo.replaceChildren(nav, msg, corpo);
  }
  const seletorMes = () => { const m = h("input", { type: "month", value: estado.mesC, onchange: () => { estado.mesC = m.value || mesAtual(); desenharSub(); } }); return campo("Mês", m); };

  async function subProdutos() {
    const r = await api("GET", "/custos/produtos");
    const det = h("div");
    const ver = async (p) => {
      try {
        const d = await api("GET", "/custos/produtos/" + p.produto_id + "?tamanho=" + p.tamanho);
        const mar = h("input", { inputmode: "decimal", placeholder: "Margem desejada %" }), sug = h("p");
        const sugerir = async () => { try { const s = await api("GET", "/custos/produtos/" + p.produto_id + "?tamanho=" + p.tamanho + "&margem_desejada=" + encodeURIComponent(mar.value.trim())); sug.replaceChildren("Preço sugerido: " + reais(s.preco_sugerido) + " (a decisão do preço é sua)."); } catch (e) { falha(e); } };
        det.replaceChildren(h("div", { class: "cartao" }, h("h2", {}, d.produto + " · " + d.tamanho + " · custo " + reais(d.custo) + " · preço " + reais(d.preco)),
          d.sem_ficha ? h("p", {}, "Produto sem ficha técnica: o custo está incompleto.") : "",
          tabela(["Insumo", "Quantidade", "Custo médio", "Fator", "Valor"], d.linhas.map((l) => h("tr", {}, h("td", {}, l.item), h("td", {}, num(l.quantidade) + " " + l.unidade), h("td", {}, reais(l.custo_medio)), h("td", {}, num(l.fator)), h("td", {}, reais(l.valor))))),
          h("div", { class: "linha" }, campo("Margem desejada (%)", mar)), h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: sugerir }, "Sugerir preço")), sug));
      } catch (e) { falha(e); }
    };
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Custo e margem por produto"),
      h("p", { class: "pequeno" }, "Custo dos insumos pela ficha técnica (custo médio e fator de correção). Margem já desconta a taxa média de cartão (" + pct(r.taxa_cartao_media_pct) + "). A Grande de dois sabores soma meia receita de cada."),
      tabela(["Produto", "Tamanho", "Preço", "Custo", "Margem", "Margem %", ""], r.produtos.map((p) => h("tr", {}, h("td", {}, p.nome), h("td", {}, p.tamanho), h("td", {}, reais(p.preco)), h("td", {}, p.sem_ficha ? "sem ficha" : reais(p.custo)),
        h("td", {}, reais(p.margem)), h("td", {}, pct(p.margem_pct) + (p.itens_sem_custo.length ? " (insumo sem custo)" : "")), h("td", {}, h("button", { class: "sec", onclick: () => ver(p) }, "Detalhar")))))), det);
  }

  async function subCmv() {
    const c = await api("GET", "/custos/cmv?mes=" + estado.mesC);
    const fechar = async () => { if (!confirm("Fechar o CMV deste mês? O valor gravado não muda depois.")) return; try { await api("POST", "/custos/cmv/fechar", { mes: estado.mesC }); await desenharSub(); ok("CMV fechado."); } catch (e) { falha(e); } };
    return h("div", { class: "cartao" }, h("h2", {}, "CMV de " + estado.mesC + (c.fechado ? " (fechado)" : " (em andamento)")), h("div", { class: "linha" }, seletorMes()),
      tabela(["", "Valor"], [["Estoque inicial", c.estoque_inicial], ["+ Compras", c.compras], ["- Estoque final", c.estoque_final], ["= CMV real", c.cmv_real], ["CMV teórico (fichas das vendas)", c.cmv_teorico], ["Diferença (real - teórico)", c.diferenca], ["Perdas", c.perdas], ["Consumo interno", c.consumo_interno], ["Vendas", c.vendas]].map(([n, v]) => h("tr", {}, h("td", {}, n), h("td", {}, reais(v))))),
      h("p", {}, "CMV sobre as vendas: " + pct(c.cmv_pct)), h("p", { class: "pequeno" }, "A diferença mede desperdício, porcionamento fora do padrão e desvios. Feche o mês depois do inventário completo."),
      c.fechado ? "" : h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: fechar }, "Fechar o mês")));
  }

  async function subResultado() {
    const r = await api("GET", "/custos/resultado?mes=" + estado.mesC);
    const L = (n, v, forte) => h("tr", { class: forte ? "destaque" : "" }, h("td", {}, n), h("td", {}, reais(v)));
    return h("div", { class: "cartao" }, h("h2", {}, "Resultado de " + estado.mesC), h("div", { class: "linha" }, seletorMes()),
      tabela(["", "Valor"], [L("Receita (produtos + entrega, sem descontos)", r.receita, true), L("- CMV" + (r.cmv_fechado ? "" : " (provisório)"), r.cmv), L("- Taxas de cartão", r.taxas_cartao), L("- Taxas de canal", r.taxas_canal), L("- Entregas", r.entregas), L("- Outras variáveis", r.outras_variaveis),
        L("= Margem de contribuição (" + pct(r.margem_contribuicao_pct) + ")", r.margem_contribuicao, true), L("- Custos fixos", r.custos_fixos), L("   fixas", r.fixos_detalhe.fixas), L("   pessoal", r.fixos_detalhe.pessoal), L("   depreciação", r.fixos_detalhe.depreciacao),
        L("= Resultado operacional", r.resultado_operacional, true), L("Tributos (fora do resultado, com o contador)", r.tributos), L("Retiradas do proprietário (fora)", r.retiradas), L("Ponto de equilíbrio (faturamento)", r.ponto_equilibrio, true)]),
      h("p", { class: "pequeno" }, r.pedidos + " pedido(s) no mês. Despesas entram pela competência do título; descontos reduzem a receita."));
  }

  async function subFatores() {
    const lista = await api("GET", "/custos/fatores");
    return h("div", { class: "cartao" }, h("h2", {}, "Fator de correção por insumo"), h("p", { class: "pequeno" }, "1,0 quando não há perda na limpeza ou no preparo. Ex.: 1,25 se de cada 1 kg comprado aproveita 800 g."),
      tabela(["Insumo", "Fator", ""], lista.map((f) => { const i = h("input", { inputmode: "decimal", value: num(f.fator_correcao) }); return h("tr", {}, h("td", {}, f.nome), h("td", {}, i),
        h("td", {}, h("button", { class: "sec", onclick: async () => { try { await api("PUT", "/custos/fatores/" + f.item_id, { fator_correcao: i.value.trim() }); ok("Fator salvo."); } catch (e) { falha(e); } } }, "Salvar"))); })));
  }

  await desenharSub();
}

async function abaImobilizado() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  const subs = [["alertas", "Alertas"], ["bens", "Bens"], ["os", "Ordens de serviço"], ["planos", "Plano de manutenção"], ["inventario", "Inventário"], ["categorias", "Categorias"]];
  if (!estado.subi) estado.subi = "alertas";
  const falha = (e) => msg.replaceChildren(aviso("erro", e.message));
  const ok = (t) => msg.replaceChildren(aviso("ok", t));
  const acao = async (metodo, caminho, corpo, texto) => { try { const r = await api(metodo, caminho, corpo); await desenharSub(); ok(texto); return r; } catch (e) { falha(e); } };
  const tabela = (cols, dados) => h("table", {}, h("thead", {}, h("tr", {}, cols.map((t) => h("th", {}, t)))), h("tbody", {}, dados));
  const num = (v) => v == null ? "" : String(v).replace(".", ",");
  const reais = (v) => v == null ? "" : "R$ " + num(v);
  const dia = (iso) => iso ? String(iso).slice(8, 10) + "/" + String(iso).slice(5, 7) + "/" + String(iso).slice(0, 4) : "";
  const hoje = () => new Date(Date.now() - 3 * 3600 * 1000).toISOString().slice(0, 10);
  const podeAprovar = ["administrador", "proprietario"].includes(estado.eu.perfil);

  async function desenharSub() {
    const nav = h("div", { class: "subnav" }, subs.map(([id, nome]) => h("button", { class: id === estado.subi ? "ativo" : "", onclick: () => { estado.subi = id; estado.osAberta = null; msg.replaceChildren(); desenharSub(); } }, nome)));
    let corpo;
    try { corpo = await ({ alertas: subAlertas, bens: subBens, os: subOs, planos: subPlanos, inventario: subInventario, categorias: subCategorias }[estado.subi])(); } catch (e) { corpo = aviso("erro", e.message); }
    alvo.replaceChildren(nav, msg, corpo);
  }

  async function subAlertas() {
    const a = await api("GET", "/imobilizado/alertas");
    const bloco = (titulo, itens, vazio) => h("div", { class: "cartao" }, h("h2", {}, titulo), itens.length ? h("ul", {}, itens.map((t) => h("li", {}, t))) : h("p", {}, vazio));
    return h("div", {}, bloco("Bens críticos parados", a.bens_criticos_parados.map((p) => "Ordem " + p.numero + ": " + p.bem + " parado desde " + dia(p.parada_inicio)), "Nenhum bem crítico parado."),
      bloco("Manutenção a fazer", a.planos.map((p) => p.bem + ": " + p.tarefa + " (" + p.situacao + ", vence " + dia(p.proximo) + ")"), "Nada vencendo."),
      bloco("Leituras fora do normal", a.leituras_fora.map((l) => l.bem + ": " + l.grandeza + " " + num(l.valor) + " em " + dia(l.data)), "Nenhuma leitura fora do normal."),
      bloco("Garantias e seguros", a.garantias_e_seguros.map((g) => g.nome + ": " + g.o_que + (g.vencido ? " vencida em " : " vence em ") + dia(g.data)), "Nada vencendo em 30 dias."),
      bloco("Ordens aguardando aprovação", a.ordens_aguardando_aprovacao.map((o) => "Ordem " + o.numero + ": " + reais(o.custo_total)), "Nenhuma."),
      h("div", { class: "cartao" }, h("p", {}, "Bens pendentes de conferência no inventário anual: " + a.inventario_pendente)));
  }

  async function subBens() {
    const [bens, cats, forn] = await Promise.all([api("GET", "/imobilizado/bens"), api("GET", "/imobilizado/categorias"), api("GET", "/compras/fornecedores?ativo=true")]);
    const f = {}; ["codigo", "nome", "valor", "data", "inicio", "numero_nota", "local", "responsavel", "serie", "residual", "vida", "garantia", "seguro"].forEach((k) => { f[k] = h("input", { placeholder: k }); });
    f.data.type = "date"; f.data.value = hoje(); f.inicio.type = "date"; f.garantia.type = "date"; f.seguro.type = "date";
    const cat = h("select", {}, cats.filter((c) => c.ativo).map((c) => h("option", { value: c.id }, c.nome + " (" + num(c.taxa_fiscal_pct) + "% a.a.)")));
    const fo = h("select", {}, h("option", { value: "" }, "Fornecedor"), ...forn.map((x) => h("option", { value: x.id }, x.nome)));
    const metodo = h("select", {}, h("option", { value: "fiscal" }, "Taxa fiscal"), h("option", { value: "vida_util" }, "Vida útil real"));
    const crit = h("input", { type: "checkbox" });
    const criar = () => acao("POST", "/imobilizado/bens", { codigo: f.codigo.value, nome: f.nome.value, categoria_id: Number(cat.value), valor_aquisicao: f.valor.value.trim(), data_aquisicao: f.data.value, inicio_uso: f.inicio.value || null,
      fornecedor_id: fo.value ? Number(fo.value) : null, numero_nota: f.numero_nota.value.trim() || null, local_texto: f.local.value.trim() || null, responsavel: f.responsavel.value.trim() || null, numero_serie: f.serie.value.trim() || null,
      critico: crit.checked, metodo: metodo.value, vida_util_meses: f.vida.value.trim() ? parseInt(f.vida.value, 10) : null, valor_residual: f.residual.value.trim() || "0", garantia_ate: f.garantia.value || null, seguro_ate: f.seguro.value || null }, "Bem cadastrado.");
    const baixar = (b) => { const motivo = prompt("Motivo da baixa:"); if (!motivo) return; const tipo = prompt("Tipo (venda, perda, descarte, doacao):", "descarte"); if (!tipo) return; const valor = prompt("Valor recebido (0 se não houve):", "0"); acao("POST", "/imobilizado/bens/" + b.id + "/baixa", { tipo, data: hoje(), valor: (valor || "0").trim(), motivo }, "Baixa registrada."); };
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Bens da loja"), bens.length ? tabela(["Plaqueta", "Bem", "Categoria", "Valor", "Depreciado", "Valor contábil", "Situação", ""], bens.map((b) => h("tr", {}, h("td", {}, b.codigo), h("td", {}, b.nome + (b.critico ? " ★" : "")), h("td", {}, b.categoria), h("td", {}, reais(b.valor_aquisicao)),
        h("td", {}, reais(b.depreciacao_acumulada)), h("td", {}, reais(b.valor_contabil)), h("td", {}, b.situacao + (b.inicio_uso ? "" : " (sem início de uso)")), h("td", {}, b.situacao === "ativo" && podeAprovar ? h("button", { class: "sec", onclick: () => baixar(b) }, "Dar baixa") : "")))) : h("p", {}, "Nenhum bem ainda."),
      h("p", { class: "pequeno" }, "★ bem crítico. A depreciação é mensal em linha reta, a partir do mês de início de uso; sem início de uso o bem ainda não deprecia.")),
      h("div", { class: "cartao" }, h("h2", {}, "Cadastrar bem"), !cats.length ? h("p", {}, "Crie as categorias na aba Categorias.") : "",
        h("div", { class: "linha" }, campo("Plaqueta", f.codigo), campo("Nome", f.nome), campo("Categoria", cat), campo("Valor (R$)", f.valor), campo("Compra", f.data), campo("Início de uso", f.inicio)),
        h("div", { class: "linha" }, campo("Fornecedor", fo), campo("Nota", f.numero_nota), campo("Local", f.local), campo("Responsável", f.responsavel), campo("Nº de série", f.serie)),
        h("div", { class: "linha" }, campo("Método", metodo), campo("Vida útil (meses)", f.vida), campo("Valor residual", f.residual), campo("Garantia até", f.garantia), campo("Seguro até", f.seguro), campo("Bem crítico", crit)),
        h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: criar }, "Cadastrar"))));
  }

  async function subOs() {
    if (estado.osAberta) return detalheOs(estado.osAberta);
    const [lista, bens] = await Promise.all([api("GET", "/imobilizado/os"), api("GET", "/imobilizado/bens?situacao=ativo")]);
    const bem = h("select", {}, bens.map((b) => h("option", { value: b.id }, b.nome + " (" + b.codigo + ")")));
    const tipo = h("select", {}, [["corretiva", "Corretiva"], ["preventiva", "Preventiva"], ["preditiva", "Preditiva"]].map(([v, n]) => h("option", { value: v }, n)));
    const desc = h("input", { placeholder: "O que aconteceu ou o que fazer" }), parou = h("input", { type: "checkbox" });
    const abrir = async () => { const r = await acao("POST", "/imobilizado/os", { bem_id: Number(bem.value), tipo: tipo.value, descricao: desc.value, parou: parou.checked }, "Ordem aberta."); if (r) { estado.osAberta = r.id; desenharSub(); } };
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Abrir ordem de serviço"), h("div", { class: "linha" }, campo("Bem", bem), campo("Tipo", tipo), campo("Descrição", desc), campo("Parou a produção", parou)),
      h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: abrir }, "Abrir"))),
      h("div", { class: "cartao" }, h("h2", {}, "Ordens"), lista.length ? tabela(["Nº", "Bem", "Tipo", "Situação", "Custo", ""], lista.map((o) => h("tr", {}, h("td", {}, o.numero), h("td", {}, o.bem), h("td", {}, o.tipo), h("td", {}, o.situacao), h("td", {}, reais(o.custo_total)),
        h("td", {}, h("button", { class: "sec", onclick: () => { estado.osAberta = o.id; desenharSub(); } }, "Abrir"))))) : h("p", {}, "Nenhuma ordem.")));
  }

  async function detalheOs(id) {
    const [o, forn, itens] = await Promise.all([api("GET", "/imobilizado/os/" + id), api("GET", "/compras/fornecedores?ativo=true"), api("GET", "/estoque/itens?classe=consumo")]);
    const blocos = [h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => { estado.osAberta = null; desenharSub(); } }, "Voltar")),
      h("div", { class: "cartao" }, h("h2", {}, "Ordem " + o.numero + " · " + o.bem + " · " + o.tipo + " · " + o.situacao), h("p", {}, o.descricao), o.parada_minutos != null ? h("p", {}, "Tempo parado: " + o.parada_minutos + " min") : "",
        o.pecas.length ? tabela(["Peça", "Quantidade", "Custo unitário"], o.pecas.map((p) => h("tr", {}, h("td", {}, p.item), h("td", {}, num(p.quantidade)), h("td", {}, reais(p.custo_unit))))) : "",
        h("p", {}, "Peças " + reais(o.custo_pecas) + " · mão de obra " + reais(o.mao_obra) + " · total " + reais(o.custo_total)), o.servico_feito ? h("p", {}, "Serviço: " + o.servico_feito) : "")];
    if (o.situacao === "aberta") {
      const et = h("select", {}, h("option", { value: "funcionario" }, "Funcionário"), h("option", { value: "terceiro" }, "Terceiro")), nome = h("input", { placeholder: "Nome" });
      const fo = h("select", {}, h("option", { value: "" }, "Fornecedor (terceiro)"), ...forn.map((x) => h("option", { value: x.id }, x.nome)));
      blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Iniciar execução"), h("div", { class: "linha" }, campo("Quem executa", et), campo("Nome", nome), campo("Fornecedor", fo)),
        h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/imobilizado/os/" + id + "/iniciar", { executor_tipo: et.value, executor_nome: nome.value.trim() || null, fornecedor_id: fo.value ? Number(fo.value) : null }, "Execução iniciada.") }, "Iniciar"),
          h("button", { class: "sec", onclick: () => acao("POST", "/imobilizado/os/" + id + "/cancelar", undefined, "Ordem cancelada.") }, "Cancelar ordem"))));
    }
    if (o.situacao === "em_execucao") {
      const it = h("select", {}, itens.map((i) => h("option", { value: i.id }, i.nome + " (saldo " + num(i.saldo) + ")"))), q = h("input", { inputmode: "decimal", placeholder: "Quantidade" });
      const feito = h("input", { placeholder: "Serviço feito" }), causa = h("input", { placeholder: "Causa" }), mao = h("input", { inputmode: "decimal", placeholder: "Mão de obra (R$)" });
      blocos.push(h("div", { class: "cartao" }, h("h2", {}, "Peças usadas"), itens.length ? h("div", { class: "linha" }, campo("Peça", it), campo("Quantidade", q)) : h("p", {}, "Cadastre as peças como itens da classe material de consumo em Estoque."),
        h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/imobilizado/os/" + id + "/pecas", { item_id: Number(it.value), quantidade: q.value.trim() }, "Peça lançada.") }, "Lançar peça"))),
        h("div", { class: "cartao" }, h("h2", {}, "Fechar ordem"), h("div", { class: "linha" }, campo("Serviço feito", feito), campo("Causa", causa), campo("Mão de obra", mao)),
          h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/imobilizado/os/" + id + "/fechar", { servico_feito: feito.value, causa: causa.value.trim() || null, mao_obra: mao.value.trim() || "0" }, "Ordem fechada.") }, "Fechar"),
            podeAprovar && !o.aprovado_por ? h("button", { class: "sec", onclick: () => acao("POST", "/imobilizado/os/" + id + "/aprovar", undefined, "Ordem aprovada.") }, "Aprovar custo") : "",
            h("button", { class: "sec", onclick: () => acao("POST", "/imobilizado/os/" + id + "/cancelar", undefined, "Ordem cancelada.") }, "Cancelar ordem"))));
    }
    return h("div", {}, blocos);
  }

  async function subPlanos() {
    const [planos, bens] = await Promise.all([api("GET", "/imobilizado/planos"), api("GET", "/imobilizado/bens?situacao=ativo")]);
    const bem = h("select", {}, bens.map((b) => h("option", { value: b.id }, b.nome))), tarefa = h("input", { placeholder: "Tarefa (ex.: limpeza do forno)" }), per = h("input", { inputmode: "numeric", placeholder: "A cada (dias)" }), ant = h("input", { inputmode: "numeric", placeholder: "Avisar antes (dias)", value: "7" });
    const lim = {}; ["bem", "grandeza", "unidade", "min", "max", "valor"].forEach((k) => { lim[k] = h("input", { placeholder: k }); });
    const bem2 = h("select", {}, bens.map((b) => h("option", { value: b.id }, b.nome)));
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Plano de manutenção preventiva"), planos.length ? tabela(["Bem", "Tarefa", "Periodicidade", "Último", "Próximo", "Situação", ""], planos.map((p) => h("tr", {}, h("td", {}, p.bem), h("td", {}, p.tarefa), h("td", {}, "a cada " + p.periodicidade_dias + " dias"), h("td", {}, dia(p.ultima_em)), h("td", {}, dia(p.proximo)), h("td", {}, p.situacao),
        h("td", {}, h("button", { class: "sec", onclick: () => acao("PATCH", "/imobilizado/planos/" + p.id, { ativo: !p.ativo }, "Plano atualizado.") }, p.ativo ? "Pausar" : "Retomar"))))) : h("p", {}, "Nenhuma tarefa. Comece pelo forno, a câmara e o freezer."),
      h("div", { class: "linha" }, campo("Bem", bem), campo("Tarefa", tarefa), campo("A cada (dias)", per), campo("Avisar antes", ant)),
      h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/imobilizado/bens/" + bem.value + "/planos", { tarefa: tarefa.value, periodicidade_dias: parseInt(per.value, 10), antecedencia_dias: parseInt(ant.value, 10) || 0 }, "Tarefa criada.") }, "Adicionar tarefa"))),
      h("div", { class: "cartao" }, h("h2", {}, "Inspeção (manutenção preditiva)"), h("p", { class: "pequeno" }, "Defina o normal de uma medida (ex.: temperatura do forno entre 250 e 300) e digite as leituras da inspeção. Fora do normal vira alerta."),
        h("div", { class: "linha" }, campo("Bem", bem2), campo("Medida", lim.grandeza), campo("Unidade", lim.unidade), campo("Mínimo", lim.min), campo("Máximo", lim.max)),
        h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("PUT", "/imobilizado/bens/" + bem2.value + "/limites", { grandeza: lim.grandeza.value, unidade: lim.unidade.value.trim() || null, minimo: lim.min.value.trim() || null, maximo: lim.max.value.trim() || null }, "Limite salvo.") }, "Salvar limite")),
        h("div", { class: "linha" }, campo("Leitura", lim.valor)), h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: async () => { const r = await acao("POST", "/imobilizado/bens/" + bem2.value + "/leituras", { grandeza: lim.grandeza.value, valor: lim.valor.value.trim() }, "Leitura registrada."); if (r && r.fora_do_normal) falha(new Error("Leitura fora do normal: veja os alertas.")); } }, "Registrar leitura"))));
  }

  async function subInventario() {
    const l = await api("GET", "/imobilizado/inventario");
    const conf = async (b, achou) => { const local = achou ? prompt("Onde está? (deixe em branco se não mudou)", b.local_texto || "") : null; return acao("POST", "/imobilizado/bens/" + b.id + "/conferencias", { encontrado: achou, local_encontrado: local || null }, "Conferência registrada."); };
    return h("div", { class: "cartao" }, h("h2", {}, "Inventário anual dos bens"), l.length ? tabela(["Plaqueta", "Bem", "Local", "Última conferência", "Situação", ""], l.map((b) => h("tr", {}, h("td", {}, b.codigo), h("td", {}, b.nome), h("td", {}, b.local_texto || ""), h("td", {}, dia(b.ultima)), h("td", {}, b.pendente ? "pendente" : "em dia"),
      h("td", {}, h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => conf(b, true) }, "Encontrado"), h("button", { class: "sec", onclick: () => conf(b, false) }, "Não encontrado")))))) : h("p", {}, "Nenhum bem."));
  }

  async function subCategorias() {
    const cats = await api("GET", "/imobilizado/categorias");
    const nome = h("input", { placeholder: "Nome" }), taxa = h("input", { inputmode: "decimal", placeholder: "Taxa fiscal % ao ano" }), vei = h("input", { type: "checkbox" });
    return h("div", { class: "cartao" }, h("h2", {}, "Categorias de bens"), cats.length ? tabela(["Categoria", "Taxa ao ano", "Veículo", ""], cats.map((c) => h("tr", {}, h("td", {}, c.nome), h("td", {}, num(c.taxa_fiscal_pct) + "%"), h("td", {}, c.veiculo ? "sim" : "não"),
      h("td", {}, h("button", { class: "sec", onclick: () => acao("PATCH", "/imobilizado/categorias/" + c.id, { ativo: !c.ativo }, "Atualizado.") }, c.ativo ? "Inativar" : "Reativar"))))) : h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/imobilizado/categorias/iniciar-padrao", undefined, "Categorias criadas.") }, "Criar as categorias padrão (confirmar taxas com o contador)")),
      h("div", { class: "linha" }, campo("Nome", nome), campo("Taxa %", taxa), campo("Veículo", vei)), h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/imobilizado/categorias", { nome: nome.value, taxa_fiscal_pct: taxa.value.trim(), veiculo: vei.checked }, "Categoria criada.") }, "Adicionar")));
  }

  await desenharSub();
}

async function abaRh() {
  const alvo = h("div"); moldura(alvo);
  const msg = h("div");
  const veSalario = ["administrador", "proprietario"].includes(estado.eu.perfil);
  const subs = [["equipe", "Equipe"], ["escala", "Escala"], ["ponto", "Ponto e banco de horas"], ["ausencias", "Ausências e documentos"], ...(veSalario ? [["folha", "Folha gerencial"]] : []), ["cadastros", "Cadastros"]];
  if (!estado.subr || !subs.some(([id]) => id === estado.subr)) estado.subr = "equipe";
  const falha = (e) => msg.replaceChildren(aviso("erro", e.message));
  const ok = (t) => msg.replaceChildren(aviso("ok", t));
  const acao = async (metodo, caminho, corpo, texto) => { try { const r = await api(metodo, caminho, corpo); await desenharSub(); ok(texto); return r; } catch (e) { falha(e); } };
  const tabela = (cols, dados) => h("table", {}, h("thead", {}, h("tr", {}, cols.map((t) => h("th", {}, t)))), h("tbody", {}, dados));
  const num = (v) => v == null ? "" : String(v).replace(".", ",");
  const reais = (v) => v == null ? "" : "R$ " + num(v);
  const dia = (iso) => iso ? String(iso).slice(8, 10) + "/" + String(iso).slice(5, 7) + "/" + String(iso).slice(0, 4) : "";
  const hoje = () => new Date(Date.now() - 3 * 3600 * 1000).toISOString().slice(0, 10);
  const horas = (min) => (min < 0 ? "-" : "") + Math.floor(Math.abs(min) / 60) + "h" + String(Math.abs(min) % 60).padStart(2, "0");
  const opcoes = (lista, rotulo) => lista.map((x) => h("option", { value: x.id }, rotulo(x)));

  async function desenharSub() {
    const nav = h("div", { class: "subnav" }, subs.map(([id, nome]) => h("button", { class: id === estado.subr ? "ativo" : "", onclick: () => { estado.subr = id; msg.replaceChildren(); desenharSub(); } }, nome)));
    let corpo;
    try { corpo = await ({ equipe: subEquipe, escala: subEscala, ponto: subPonto, ausencias: subAusencias, folha: subFolha, cadastros: subCadastros }[estado.subr])(); } catch (e) { corpo = aviso("erro", e.message); }
    alvo.replaceChildren(nav, msg, corpo);
  }

  async function subEquipe() {
    const [fs, funcoes, escalas] = await Promise.all([api("GET", "/rh/funcionarios"), api("GET", "/rh/funcoes"), api("GET", "/rh/escalas")]);
    const nome = h("input", { placeholder: "Nome" }), tel = h("input", { placeholder: "Telefone" }), adm = h("input", { type: "date", value: hoje() }), fn = h("select", {}, opcoes(funcoes.filter((f) => f.ativo), (f) => f.nome)), pe = h("input", { type: "checkbox" });
    const ct = h("select", {}, ["clt", "intermitente", "freelancer", "diarista", "prolabore", "outro"].map((t) => h("option", { value: t }, t))), es = h("select", {}, h("option", { value: "" }, "Sem escala"), ...opcoes(escalas.filter((e) => e.ativo), (e) => e.nome));
    const fp = h("select", {}, [["mensal", "Mensal"], ["diaria", "Por diária"], ["hora", "Por hora"]].map(([v, n]) => h("option", { value: v }, n))), val = h("input", { inputmode: "decimal", placeholder: "Valor" });
    const criar = async () => {
      const r = await acao("POST", "/rh/funcionarios", { nome: nome.value, telefone: tel.value.trim() || null, funcao_id: Number(fn.value), admissao: adm.value, preco_especial: pe.checked }, "Funcionário cadastrado.");
      if (r && veSalario && val.value.trim()) await acao("POST", "/rh/funcionarios/" + r.id + "/contratos", { tipo: ct.value, escala_id: es.value ? Number(es.value) : null, forma_pagamento: fp.value, valor: val.value.trim(), vigente_desde: adm.value }, "Funcionário e contrato cadastrados.");
    };
    const desligar = (f) => { const motivo = prompt("Motivo do desligamento:"); if (motivo && confirm("Desligar " + f.nome + "? O login pessoal será bloqueado.")) acao("POST", "/rh/funcionarios/" + f.id + "/desligar", { data: hoje(), motivo }, "Funcionário desligado."); };
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Equipe"), fs.length ? tabela(["Nome", "Função", "Admissão", "Contrato", ...(veSalario ? ["Valor"] : []), "Situação", ""], fs.map((f) => h("tr", {}, h("td", {}, f.nome), h("td", {}, f.funcao), h("td", {}, dia(f.admissao)),
        h("td", {}, f.contrato ? f.contrato.tipo + (f.contrato.escala ? " · " + f.contrato.escala : "") : "sem contrato"), ...(veSalario ? [h("td", {}, f.contrato ? reais(f.contrato.valor) + " (" + f.contrato.forma_pagamento + ")" : "")] : []), h("td", {}, f.ativo ? "ativo" : "desligado"),
        h("td", {}, f.ativo ? h("button", { class: "sec", onclick: () => desligar(f) }, "Desligar") : "")))) : h("p", {}, "Nenhum funcionário ainda.")),
      h("div", { class: "cartao" }, h("h2", {}, "Cadastrar funcionário"), !funcoes.length ? h("p", {}, "Crie as funções na aba Cadastros.") : "", h("div", { class: "linha" }, campo("Nome", nome), campo("Telefone", tel), campo("Função", fn), campo("Admissão", adm), campo("Preço de funcionário", pe)),
        veSalario ? h("div", { class: "linha" }, campo("Contrato", ct), campo("Escala", es), campo("Pagamento", fp), campo("Valor (R$)", val)) : h("p", { class: "pequeno" }, "O contrato e o salário são cadastrados pelo administrador ou proprietário."),
        h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: criar }, "Cadastrar"))));
  }

  async function subEscala() {
    const ini = new Date(Date.now() - 3 * 3600 * 1000).toISOString().slice(0, 10), fim = new Date(Date.now() + 11 * 24 * 3600 * 1000).toISOString().slice(0, 10);
    const [ts, fs, funcoes] = await Promise.all([api("GET", "/rh/turnos?de=" + ini + "&ate=" + fim), api("GET", "/rh/funcionarios?ativo=true"), api("GET", "/rh/funcoes")]);
    const f = h("select", {}, opcoes(fs, (x) => x.nome)), d = h("input", { type: "date", value: hoje() }), fn = h("select", {}, opcoes(funcoes.filter((x) => x.ativo), (x) => x.nome)), i = h("input", { type: "time", value: "17:00" }), t = h("input", { type: "time", value: "23:00" });
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Escala dos próximos 14 dias"), ts.length ? tabela(["Dia", "Pessoa", "Função", "Turno", ""], ts.map((x) => h("tr", {}, h("td", {}, dia(x.data)), h("td", {}, x.funcionario), h("td", {}, x.funcao), h("td", {}, x.inicio + " às " + x.fim),
      h("td", {}, h("button", { class: "sec", onclick: () => acao("DELETE", "/rh/turnos/" + x.id, undefined, "Turno removido.") }, "Remover"))))) : h("p", {}, "Nenhum turno lançado.")),
      h("div", { class: "cartao" }, h("h2", {}, "Lançar turno"), h("div", { class: "linha" }, campo("Pessoa", f), campo("Dia", d), campo("Função", fn), campo("Início", i), campo("Fim", t)),
        h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("PUT", "/rh/turnos", { funcionario_id: Number(f.value), data: d.value, funcao_id: Number(fn.value), inicio: i.value, fim: t.value }, "Turno lançado.") }, "Lançar"))));
  }

  async function subPonto() {
    const fs = await api("GET", "/rh/funcionarios?ativo=true");
    if (!fs.length) return h("div", { class: "cartao" }, h("p", {}, "Cadastre funcionários primeiro."));
    if (!estado.funcP || !fs.some((x) => x.id === estado.funcP)) estado.funcP = fs[0].id;
    const sel = h("select", { onchange: () => { estado.funcP = Number(sel.value); desenharSub(); } }, fs.map((x) => h("option", { value: x.id, selected: x.id === estado.funcP }, x.nome)));
    const s = await api("GET", "/rh/ponto/saldo?funcionario_id=" + estado.funcP);
    const d = h("input", { type: "date", value: hoje() }), e = h("input", { type: "time", value: "17:00" }), sa = h("input", { type: "time", value: "23:00" });
    const bm = h("input", { inputmode: "numeric", placeholder: "Minutos (negativo compensa)" }), bmo = h("input", { placeholder: "Motivo" });
    return h("div", {}, h("div", { class: "cartao" }, h("h2", {}, "Ponto do mês · banco de horas " + horas(s.banco_horas_min)), h("div", { class: "linha" }, campo("Pessoa", sel)),
      tabela(["Dia", "Trabalhado", "Previsto", "Saldo", ""], s.dias.map((x) => h("tr", {}, h("td", {}, dia(x.data)), h("td", {}, horas(x.trabalhado_min)), h("td", {}, horas(x.previsto_min)), h("td", {}, horas(x.saldo_min)), h("td", {}, x.falta_ponto ? "sem ponto" : "")))), h("p", {}, "Saldo do mês: " + horas(s.saldo_mes_min))),
      h("div", { class: "cartao" }, h("h2", {}, "Lançar ponto"), h("div", { class: "linha" }, campo("Dia", d), campo("Entrada", e), campo("Saída", sa)),
        h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("PUT", "/rh/ponto", { funcionario_id: estado.funcP, data: d.value, entrada: e.value, saida: sa.value }, "Ponto lançado.") }, "Lançar ponto"))),
      h("div", { class: "cartao" }, h("h2", {}, "Hora extra ou compensação (administrador ou gerente)"), h("div", { class: "linha" }, campo("Minutos", bm), campo("Motivo", bmo)),
        h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/rh/banco-horas", { funcionario_id: estado.funcP, data: hoje(), minutos: parseInt(bm.value, 10), motivo: bmo.value }, "Lançado no banco de horas.") }, "Lançar no banco"))));
  }

  async function subAusencias() {
    const [aus, fs, al] = await Promise.all([api("GET", "/rh/ausencias"), api("GET", "/rh/funcionarios?ativo=true"), api("GET", "/rh/alertas")]);
    const f = h("select", {}, opcoes(fs, (x) => x.nome)), tp = h("select", {}, [["ferias", "Férias"], ["afastamento", "Afastamento"], ["atestado", "Atestado"], ["falta", "Falta"]].map(([v, n]) => h("option", { value: v }, n))), i = h("input", { type: "date", value: hoje() }), t = h("input", { type: "date", value: hoje() });
    const f2 = h("select", {}, opcoes(fs, (x) => x.nome)), dn = h("input", { placeholder: "Documento (ex.: Manipulação de alimentos)" }), dv = h("input", { type: "date" });
    const lista = (titulo, itens, vazio) => h("div", { class: "cartao" }, h("h2", {}, titulo), itens.length ? h("ul", {}, itens.map((x) => h("li", {}, x))) : h("p", {}, vazio));
    return h("div", {}, lista("Alertas", [...al.documentos.map((d) => d.funcionario + ": " + d.nome + (d.vencido ? " vencido em " : " vence em ") + dia(d.validade)), ...al.ferias_vencendo.map((x) => x.funcionario + ": " + x.dias_sem_ferias + " dias sem férias"), ...al.sem_contrato.map((x) => x.nome + ": sem contrato")], "Nada pendente."),
      h("div", { class: "cartao" }, h("h2", {}, "Ausências"), aus.length ? tabela(["Pessoa", "Tipo", "De", "Até"], aus.map((a) => h("tr", {}, h("td", {}, a.funcionario), h("td", {}, a.tipo), h("td", {}, dia(a.inicio)), h("td", {}, dia(a.fim))))) : h("p", {}, "Nenhuma."),
        h("div", { class: "linha" }, campo("Pessoa", f), campo("Tipo", tp), campo("De", i), campo("Até", t)), h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/rh/ausencias", { funcionario_id: Number(f.value), tipo: tp.value, inicio: i.value, fim: t.value }, "Ausência lançada.") }, "Lançar"))),
      h("div", { class: "cartao" }, h("h2", {}, "Treinamento e documento com validade"), h("div", { class: "linha" }, campo("Pessoa", f2), campo("Documento", dn), campo("Validade", dv)),
        h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/rh/documentos", { funcionario_id: Number(f2.value), nome: dn.value, validade: dv.value }, "Documento lançado.") }, "Lançar"))));
  }

  async function subFolha() {
    const mes = hoje().slice(0, 7);
    const p = await api("GET", "/rh/folha/previa?mes=" + mes);
    return h("div", { class: "cartao" }, h("h2", {}, "Folha gerencial de " + mes + ": " + reais(p.total)), h("p", { class: "pequeno" }, "Estimativa de custo de pessoal (salário, encargos pelo percentual dos parâmetros e benefícios). A folha legal é do contador; lance os valores dele no resumo quando tiver."),
      p.linhas.length ? tabela(["Pessoa", "Tipo", "Bruto", "Encargos", "Benefícios", "Total"], p.linhas.map((l) => h("tr", {}, h("td", {}, l.funcionario), h("td", {}, l.tipo), h("td", {}, reais(l.bruto)), h("td", {}, reais(l.encargos)), h("td", {}, reais(l.beneficios)), h("td", {}, reais(l.total))))) : h("p", {}, "Nenhum contrato vigente."),
      h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => { if (confirm("Lançar a folha de " + mes + " em Contas a Pagar?")) acao("POST", "/rh/folha/lancar", { competencia: mes }, "Folha lançada em Contas a Pagar."); } }, "Lançar em Contas a Pagar")));
  }

  async function subCadastros() {
    const [funcoes, escalas] = await Promise.all([api("GET", "/rh/funcoes"), api("GET", "/rh/escalas")]);
    const fn = h("input", { placeholder: "Nova função" }), en = h("input", { placeholder: "Nome (ex.: 6x1)" }), edt = h("input", { inputmode: "numeric", placeholder: "Dias de trabalho" }), edf = h("input", { inputmode: "numeric", placeholder: "Dias de folga" }), ehs = h("input", { inputmode: "decimal", placeholder: "Horas por semana" });
    return h("div", {}, !funcoes.length && !escalas.length ? h("div", { class: "cartao" }, h("div", { class: "acoes-linha" }, h("button", { class: "principal", onclick: () => acao("POST", "/rh/iniciar-padrao", undefined, "Funções e escalas criadas.") }, "Criar funções e escalas de partida (6x1 e 5x2)"))) : "",
      h("div", { class: "cartao" }, h("h2", {}, "Funções"), h("p", {}, funcoes.map((f) => f.nome).join(" · ") || "Nenhuma."), h("div", { class: "linha" }, campo("Nova função", fn)), h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/rh/funcoes", { nome: fn.value }, "Função criada.") }, "Adicionar"))),
      h("div", { class: "cartao" }, h("h2", {}, "Tipos de escala (a lei pode mudar: é cadastro)"), escalas.length ? tabela(["Escala", "Trabalho", "Folga", "Horas/semana", ""], escalas.map((e) => h("tr", {}, h("td", {}, e.nome), h("td", {}, e.dias_trabalho), h("td", {}, e.dias_folga), h("td", {}, num(e.horas_semana)),
        h("td", {}, h("button", { class: "sec", onclick: () => acao("PATCH", "/rh/escalas/" + e.id, { ativo: !e.ativo }, "Atualizado.") }, e.ativo ? "Inativar" : "Reativar"))))) : "",
        h("div", { class: "linha" }, campo("Nome", en), campo("Dias de trabalho", edt), campo("Dias de folga", edf), campo("Horas/semana", ehs)),
        h("div", { class: "acoes-linha" }, h("button", { class: "sec", onclick: () => acao("POST", "/rh/escalas", { nome: en.value, dias_trabalho: parseInt(edt.value, 10), dias_folga: parseInt(edf.value, 10), horas_semana: ehs.value.trim() }, "Escala criada.") }, "Adicionar escala"))));
  }

  await desenharSub();
}

async function abaMeusDados() {
  const alvo = h("div"); moldura(alvo);
  let d;
  try { d = await api("GET", "/rh/meus-dados"); } catch (e) { alvo.replaceChildren(aviso("erro", e.message)); return; }
  const dia = (iso) => String(iso).slice(8, 10) + "/" + String(iso).slice(5, 7);
  alvo.replaceChildren(h("div", { class: "cartao" }, h("h2", {}, d.funcionario + " · " + d.funcao), h("p", {}, "Banco de horas: " + (d.banco_horas_min < 0 ? "-" : "") + Math.floor(Math.abs(d.banco_horas_min) / 60) + "h" + String(Math.abs(d.banco_horas_min) % 60).padStart(2, "0"))),
    h("div", { class: "cartao" }, h("h2", {}, "Minha escala"), d.turnos.length ? h("ul", {}, d.turnos.map((t) => h("li", {}, dia(t.data) + ": " + t.inicio + " às " + t.fim))) : h("p", {}, "Nenhum turno lançado.")),
    h("div", { class: "cartao" }, h("h2", {}, "Meu ponto"), d.ponto.length ? h("ul", {}, d.ponto.map((p) => h("li", {}, dia(p.data) + ": " + p.entrada + " às " + p.saida))) : h("p", {}, "Nenhum ponto lançado."),
      d.ausencias.length ? h("p", {}, "Ausências: " + d.ausencias.map((a) => a.tipo + " " + dia(a.inicio) + " a " + dia(a.fim)).join(" · ")) : ""));
}

async function desenhar() {
  if (!estado.token) return telaLogin();
  if (!estado.eu) {
    try { estado.eu = await api("GET", "/auth/me"); } catch (e) { return telaLogin(); }
  }
  if (estado.eu.deve_trocar_senha) return telaTrocaSenha();
  const abas = { painel: abaPainel, vendas: abaVendas, producao: abaProducao, caixa: abaCaixa, estoque: abaEstoque, compras: abaCompras, contas: abaContas, custos: abaCustos, bi: abaBi, imobilizado: abaImobilizado, rh: abaRh, meusdados: abaMeusDados, cardapio: abaCardapio, fichas: abaFichas, clientes: abaClientes, entregadores: abaEntregadores, usuarios: abaUsuarios, parametros: abaParametros, auditoria: abaAuditoria };
  await (abas[estado.aba] || abaPainel)();
}

desenhar();
