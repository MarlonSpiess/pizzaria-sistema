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
  estado.token = null; estado.eu = null;
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

async function desenhar() {
  if (!estado.token) return telaLogin();
  if (!estado.eu) {
    try { estado.eu = await api("GET", "/auth/me"); } catch (e) { return telaLogin(); }
  }
  if (estado.eu.deve_trocar_senha) return telaTrocaSenha();
  const abas = { painel: abaPainel, cardapio: abaCardapio, fichas: abaFichas, clientes: abaClientes, entregadores: abaEntregadores, usuarios: abaUsuarios, parametros: abaParametros, auditoria: abaAuditoria };
  await (abas[estado.aba] || abaPainel)();
}

desenhar();
