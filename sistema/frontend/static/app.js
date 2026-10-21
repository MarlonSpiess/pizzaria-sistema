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
  raiz.replaceChildren(h("div", { class: "login" }, h("h1", {}, "Sistema da Pizzaria"), form));
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
  ["painel", "Painel", null],
  ["usuarios", "Usuários", ["administrador", "proprietario"]],
  ["parametros", "Parâmetros", ["administrador", "proprietario", "gerente", "subgerente"]],
  ["auditoria", "Auditoria", ["administrador", "proprietario", "gerente", "subgerente"]],
];

function moldura(conteudo) {
  const abas = ABAS.filter(([, , perfis]) => !perfis || perfis.includes(estado.eu.perfil));
  raiz.replaceChildren(
    h("header", {}, h("h1", {}, "Sistema da Pizzaria"), h("span", {}, estado.eu.nome + " (" + estado.eu.perfil + ")"),
      h("button", { class: "sec", onclick: () => sair() }, "Sair")),
    h("nav", {}, abas.map(([id, nome]) => h("button", { class: id === estado.aba ? "ativo" : "", onclick: () => { estado.aba = id; desenhar(); } }, nome))),
    h("main", {}, conteudo));
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
      else cart.append(aviso(b.atrasado ? "alerta" : "ok", (b.atrasado ? "Backup atrasado. " : "Backup em dia. ") + "Último: " + fmtData(b.ultimo_sucesso.concluido_em)
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
      h("button", { class: "sec", onclick: async () => {
        const nova = window.prompt("Senha provisória para " + x.usuario + " (mínimo 8 caracteres):");
        if (!nova) return; msg.replaceChildren();
        try { await api("POST", "/usuarios/" + x.id + "/redefinir-senha", { senha_nova: nova }); msg.replaceChildren(aviso("ok", "Senha redefinida. O usuário troca no próximo acesso.")); }
        catch (e) { msg.replaceChildren(aviso("erro", e.message)); }
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

async function desenhar() {
  if (!estado.token) return telaLogin();
  if (!estado.eu) {
    try { estado.eu = await api("GET", "/auth/me"); } catch (e) { return telaLogin(); }
  }
  if (estado.eu.deve_trocar_senha) return telaTrocaSenha();
  const abas = { painel: abaPainel, usuarios: abaUsuarios, parametros: abaParametros, auditoria: abaAuditoria };
  await (abas[estado.aba] || abaPainel)();
}

desenhar();
