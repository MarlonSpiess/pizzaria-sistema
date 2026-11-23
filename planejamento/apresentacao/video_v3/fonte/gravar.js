// Grava as cenas do vídeo: o sistema real (banco de demonstração, dados fictícios) dentro de um "palco" 1920x1080
// com moldura de navegador ou de tablet, cursor, toques, realces e anotações. Cada cena dura o tempo da sua narração.
//
// Uso (Linux com Xvfb e ffmpeg; sistema rodando em http://127.0.0.1:8080 sobre o banco pizzaria_demo):
//   DEMO_SENHA=... DB_NAME=pizzaria_demo DB_PASS=... SISTEMA=.../sistema node gravar.js [saida] [cena1,...]   grava em MP4 (x11grab, só Linux)
//   DEMO_SENHA=... TESTE=1 node gravar.js [saida] [cenas]          ensaio sem vídeo: só capturas de tela por passo
"use strict";
const { chromium } = require("playwright");
const { spawn, spawnSync } = require("child_process");
const fs = require("fs");
const http = require("http");
const path = require("path");

const AQUI = __dirname;
const SAIDA = path.resolve(process.argv[2] || path.join(AQUI, "..", "saida", "cenas"));
const SO = process.argv[3] ? process.argv[3].split(",") : null;
const TESTE = process.env.TESTE === "1";
const APP = process.env.APP_URL || "http://127.0.0.1:8080";
const SENHA = process.env.DEMO_SENHA || "";
const DISPLAY = process.env.DISPLAY_GRAVACAO || ":99";
const PORTA_PALCO = 8090;
const ENTRADA = 0.6;  // segundos de imagem antes de a narração começar
const SAIDA_CENA = 1.0;  // segundos depois do fim da narração
const ROTEIRO = JSON.parse(fs.readFileSync(path.join(AQUI, "narracao.json"), "utf8"));
const AUDIO = path.join(AQUI, "audio");
if (SENHA.length < 8) { console.error("Defina DEMO_SENHA (a mesma usada em semear_demo.py)."); process.exit(1); }
fs.mkdirSync(SAIDA, { recursive: true });

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
const normal = (t) => t.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");

// ---------------------------------------------------------------- tempos da narração
function tempos(id) {
  const cena = ROTEIRO.cenas.find((c) => c.id === id);
  const arq = path.join(AUDIO, id + ".json");
  let palavras;
  if (fs.existsSync(arq)) palavras = JSON.parse(fs.readFileSync(arq, "utf8")).palavras;
  else if (!TESTE) throw new Error(`Falta a narração ${arq}: rode gerar_narracao.py antes de gravar`);
  else {  // sem áudio ainda: estimativa de 2,6 palavras por segundo (só para ensaio)
    palavras = cena.texto.split(/\s+/).map((p, i) => ({ palavra: p, inicio: i / 2.6, fim: (i + 1) / 2.6 }));
  }
  const fim = palavras.length ? palavras[palavras.length - 1].fim : 3;
  return {
    duracao: ENTRADA + fim + SAIDA_CENA,
    // instante (s, desde o começo da cena) em que a n-ésima ocorrência da palavra começa a ser dita
    em(palavra, n = 1) {
      const alvo = normal(palavra);
      let vistos = 0;
      for (const p of palavras) if (normal(p.palavra) === alvo && ++vistos === n) return ENTRADA + p.inicio;
      throw new Error(`Palavra "${palavra}" (${n}) não está na narração de ${id}`);
    },
  };
}

// ---------------------------------------------------------------- servidor do palco
function servirPalco() {
  const tipos = { ".html": "text/html; charset=utf-8", ".svg": "image/svg+xml" };
  const srv = http.createServer((req, res) => {
    const nome = path.basename(decodeURIComponent(new URL(req.url, "http://x").pathname)) || "palco.html";
    const arq = path.join(AQUI, "palco", nome);
    if (!fs.existsSync(arq)) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { "Content-Type": tipos[path.extname(arq)] || "application/octet-stream" });
    fs.createReadStream(arq).pipe(res);
  });
  return new Promise((ok) => srv.listen(PORTA_PALCO, "127.0.0.1", () => ok(srv)));
}

// ---------------------------------------------------------------- gravação de tela
// Captura só a área da página (abaixo das barras do navegador): deslocamento medido na abertura.
let TOPO = 0;
function iniciarFfmpeg(arquivo) {
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "x11grab", "-draw_mouse", "0", "-framerate", "30", "-video_size", "1920x1080",
    "-i", `${DISPLAY}.0+0,${TOPO}`, "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", arquivo], { stdio: ["pipe", "inherit", "inherit"] });
  let fechou = null;
  ff.on("close", (cod) => { fechou = cod; });
  return {
    vivo: () => fechou === null,
    parar: () => new Promise((ok, falha) => {
      if (fechou !== null) { falha(new Error("O ffmpeg parou antes da hora (código " + fechou + ")")); return; }
      ff.on("close", (cod) => (cod === 0 ? ok() : falha(new Error("ffmpeg saiu com código " + cod))));
      ff.stdin.write("q");
    }),
  };
}

// ---------------------------------------------------------------- ajudantes de cena
class Cena {
  constructor(page, id) { this.page = page; this.id = id; this.t = tempos(id); this.n = 0; }
  P(fn, ...args) { return this.page.evaluate(([f, a]) => window.P[f](...a), [fn, args]); }
  async ate(seg) {  // espera até o instante seg (desde o começo da cena)
    const falta = this.t0 + seg * 1000 - Date.now();
    if (falta > 0) await dormir(falta);
  }
  async quando(palavra, n = 1, adianto = 0) { await this.ate(this.t.em(palavra, n) - adianto); }
  async foto(rotulo) { if (TESTE) await this.page.screenshot({ path: path.join(SAIDA, `${this.id}_${String(++this.n).padStart(2, "0")}_${rotulo}.png`) }); }
  frame(sel) { return this.page.$(sel).then((e) => e.contentFrame()); }
  async apontar(loc, { toque = false, ms = 650 } = {}) {
    await loc.scrollIntoViewIfNeeded();
    const b = await loc.boundingBox();
    if (!b) throw new Error("Elemento sem caixa na tela");
    await this.P("cursor", b.x + Math.min(b.width / 2, 60), b.y + b.height / 2, ms, toque);
    return b;
  }
  async clicar(loc, opc = {}) { await this.apontar(loc, opc); await this.P("onda"); await loc.click(); await dormir(250); }
  async escolher(loc, valor, opc = {}) { await this.apontar(loc, opc); await this.P("onda"); await loc.selectOption({ label: valor }); await dormir(300); }
  async digitar(loc, texto, opc = {}) { await this.apontar(loc, opc); await this.P("onda"); await loc.click(); await loc.fill(""); await loc.pressSequentially(texto, { delay: texto.length > 12 ? 40 : 70 }); }
  async realcar(loc) { await loc.scrollIntoViewIfNeeded(); await dormir(450); const b = await loc.boundingBox(); await this.P("realce", b); }
  // Câmera: aproxima o aparelho para o elemento ficar no centro da tela (escala 1 volta ao normal).
  async foco(sel, loc, escala) {
    await this.P("realce", null);
    if (!loc || escala === 1) { await this.P("camera", sel, 1, 0, 0); this.zoom = false; await dormir(1100); return; }
    await this.P("camera", sel, 1, 0, 0); await dormir(this.zoom ? 1150 : 50);  // mede só com a câmera parada na escala 1
    const b = await loc.boundingBox();
    const { L, T } = await this.page.evaluate((s) => { const e = document.querySelector(s); return { L: e.offsetLeft, T: e.offsetTop }; }, sel);
    const px = b.x + b.width / 2, py = b.y + b.height / 2;
    await this.P("camera", sel, escala, 960 - L - (px - L) * escala, 520 - T - (py - T) * escala);
    this.zoom = true;
    await dormir(1150);
  }
}
const campo = (f, rotulo, tag = "select") => f.locator(`div:has(> label:text-is("${rotulo}")) > ${tag}`).first();
const botao = (f, texto) => f.locator(`button:text-is("${texto}")`).first();

async function entrar(page, sel, usuario) {
  const f = await (await page.$(sel)).contentFrame();
  await f.waitForSelector("#u");
  await f.fill("#u", usuario); await f.fill("#s", SENHA); await f.press("#s", "Enter");
  await f.waitForSelector("#principal");
  await dormir(500);
  return f;
}
async function abrirApp(page, sel, usuario) {
  // Os aparelhos do palco são a mesma origem e dividem o sessionStorage: limpa o token salvo para cada um entrar com o seu login.
  // Quem já entrou segue com o token na memória da própria tela.
  await page.evaluate(([s, u]) => window.P.carregar(s, u), [sel, APP + "/?v=" + Date.now()]);
  const f = await (await page.$(sel)).contentFrame();
  await f.waitForSelector("#u, #principal");
  if (!(await f.$("#u"))) {
    await f.evaluate(() => sessionStorage.removeItem("pz-token"));
    await page.evaluate(([s, u]) => window.P.carregar(s, u), [sel, APP + "/?v=" + Date.now()]);
  }
  return entrar(page, sel, usuario);
}
// Clique fora do ar (aparelho ainda oculto, sem eventos de ponteiro): pelo próprio elemento.
const fora = async (loc) => { await loc.evaluate((e) => e.click()); await dormir(400); };
const menu = (f, nome) => f.locator(`nav.menu button:has-text("${nome}")`).first();
const area = (f, nome) => f.locator(`button.area:has-text("${nome}")`).first();
const sub = (f, nome) => f.locator(`.subnav button:text-is("${nome}")`).first();

// ---------------------------------------------------------------- cenas
// Cada cena tem prep (fora do ar, antes de gravar) e roda (no ar, com o relógio da narração).
const CENAS = {
  c01_abertura: {
    async roda(c) {
      await c.P("aparelho", "nenhum"); await c.P("capitulo", "", "");
      await c.P("camada", `<div class="linha relogio" id="hora">19:58</div><div class="linha medio" style="margin-top:10px">sexta-feira</div>
        <div class="chips"><div class="chip linha">🧾 o balcão enche</div><div class="chip linha">📞 o telefone toca</div><div class="chip linha">📱 o aplicativo apita</div></div>
        <div class="linha grande" style="margin-top:60px">Cada minuto vale <span class="ouro">dinheiro</span>.</div>
        <div class="linha grande">E cada erro também.</div>`);
      await c.P("linha", 0); await c.P("linha", 1); await c.P("relogio", "hora", 19 * 60 + 58, 20 * 60, 1800);
      await c.quando("balcão"); await c.P("linha", 2);
      await c.quando("telefone"); await c.P("linha", 3);
      await c.quando("aplicativo"); await c.P("linha", 4);
      await c.foto("chips");
      await c.quando("minuto"); await c.P("linha", 5);
      await c.quando("erro", 1, 0.3); await c.P("linha", 6);
      await c.foto("fim");
    },
  },
  c02_problema: {
    async roda(c) {
      await c.P("camada", `<div class="linha medio">Na maioria das pizzarias, a operação depende de</div>
        <div class="chips"><div class="chip ruim linha">🧠 memória</div><div class="chip ruim linha">📝 papel</div><div class="chip ruim linha">📊 planilha</div></div>
        <div class="etapas" style="margin-top:60px"><div class="etapa linha"><i>?</i>Quanto custou cada pizza?</div><div class="etapa linha"><i>?</i>Quanto sobrou no estoque?</div><div class="etapa linha"><i>?</i>Por que o caixa não bateu?</div></div>`);
      await c.P("linha", 0);
      await c.quando("memória"); await c.P("linha", 1);
      await c.quando("papel"); await c.P("linha", 2);
      await c.quando("planilha"); await c.P("linha", 3);
      await c.quando("custou"); await c.P("linha", 4);
      await c.quando("sobrou"); await c.P("linha", 5);
      await c.quando("caixa"); await c.P("linha", 6);
      await c.foto("fim");
    },
  },
  c03_solucao: {
    async roda(c) {
      await c.P("camada", `<img class="logo-grande linha" src="logo.svg" alt=""><div class="linha enorme">Sistema Integrado<br><span class="ouro">da Pizzaria</span></div>`);
      await c.P("linha", 0); await dormir(300); await c.P("linha", 1);
      await c.quando("servidor");
      await c.P("camada", `<div class="chips"><div class="chip linha">🖥️ 1 servidor dentro da loja</div><div class="chip linha">🔑 1 login por pessoa</div></div>
        <div class="areas3"><div class="area3 linha"><div class="ic">👨‍🍳</div><h3>Produção</h3><p>massa, montagem, forno, acabamento e despacho</p></div>
        <div class="area3 linha"><div class="ic">🧾</div><h3>Vendas</h3><p>balcão, caixa, clientes e entregas</p></div>
        <div class="area3 linha"><div class="ic">🏢</div><h3>Administrativo</h3><p>estoque, compras, contas, custos, RH e BI</p></div></div>
        <div class="linha grande" style="margin-top:50px">Cada pessoa vê <span class="ouro">só o que precisa</span>.</div>`);
      await dormir(200); await c.P("linha", 0);
      await c.quando("login"); await c.P("linha", 1);
      await c.quando("produção"); await c.P("linha", 2);
      await c.quando("vendas"); await c.P("linha", 3);
      await c.quando("administrativo"); await c.P("linha", 4);
      await c.quando("exatamente"); await c.P("linha", 5);
      await c.foto("fim");
    },
  },
  c04_pedido: {
    async prep(c, page) {
      await c.P("camada", "");
      c.f = await abrirApp(page, "#f1", "bruno");
    },
    async roda(c) {
      const f = c.f;
      await c.P("capitulo", "02", "Vendas · pedido no balcão"); await c.P("aparelho", "navegador");
      await c.quando("monta");
      await c.escolher(campo(f, "Sabor 1"), "Margherita (Tradicionais)");
      await c.quando("quatro");
      await c.escolher(campo(f, "Sabor 2 (só Grande)"), "Quatro Queijos (Especiais)");
      await c.quando("borda");
      await c.escolher(campo(f, "Borda"), "Borda de Catupiry");
      await c.clicar(botao(f, "Adicionar ao pedido"));
      await c.foto("item");
      await c.quando("regra");
      await c.realcar(f.locator(".resultado").first());
      await c.P("nota", "Regra da casa", "Meio a meio: metade do preço de cada sabor. R$ 17,50 + R$ 25,00 + borda R$ 10,00", 640, 600);
      await c.foto("regra");
      await c.quando("pagamento", 1, 0.5);
      await c.P("realce", null); await c.P("nota", "", "");
      await c.escolher(campo(f, "Forma"), "pix", { ms: 350 });
      await c.digitar(campo(f, "Valor recebido (R$)", "input"), "52,50", { ms: 350 });
      await c.clicar(botao(f, "Lançar"), { ms: 350 });
      await c.quando("urgente", 1, 0.3);
      await c.clicar(f.locator("label.inline:has-text('Pedido urgente') input"), { ms: 400 });
      await c.quando("confirmado", 1, 0.4);
      await c.clicar(botao(f, "Confirmar pedido"));
      await c.quando("número", 1, 0.2);
      await c.realcar(f.locator(".aviso.ok").first());
      await c.foto("confirmado");
    },
  },
  c05_pizzaiolo: {
    async prep(c, page) {
      await c.P("realce", null); await c.P("esconderCursor");
      c.f = await abrirApp(page, "#ft", "diego");
      await c.P("rotulo", "#rt", "📱 Tablet da montagem · <b>Diego, pizzaiolo</b>");
    },
    async roda(c) {
      const f = c.f;
      await c.P("capitulo", "03", "Produção · montagem"); await c.P("aparelho", "tablet");
      await c.foto("fila");
      await c.quando("toca", 1, 0.7);
      await c.clicar(botao(f, "Pegar a próxima pizza"), { toque: true });
      await c.quando("sabores", 1, 0.3);
      await c.foco("#tablet", f.locator(".cartao:has(h2:text-is('Pizza atual'))").first(), 1.35);
      await c.foto("atual");
      await c.quando("montou", 1, 0.9);
      await c.foco("#tablet", null, 1);
      await c.clicar(f.locator("button:has-text('Finalizada a montagem')").first(), { toque: true });
      await c.foto("forno");
    },
  },
  c06_acabamento: {
    async prep(c, page) {
      await c.P("esconderCursor");
      c.f = await abrirApp(page, "#ft", "fabio");
      await c.P("rotulo", "#rt", "📱 Tablet do acabamento · <b>Fábio</b>");
    },
    async roda(c) {
      const f = c.f;
      await c.P("capitulo", "04", "Produção · forno e acabamento");
      await c.quando("ocupação", 1, 0.3);
      await c.realcar(f.locator(".cartao:has(h2:has-text('Forno:'))").first());
      await c.quando("sai", 1, 0.6);
      await c.P("realce", null);
      await c.clicar(botao(f, "Saiu do forno"), { toque: true });
      await c.clicar(sub(f, "Acabamento"), { toque: true });
      await c.quando("acabada", 1, 0.5);
      await c.clicar(botao(f, "Acabada e etiqueta"), { toque: true });
      await c.quando("etiqueta", 1, 0.4);
      await c.foco("#tablet", f.locator(".cartao.etiqueta").first(), 1.4);
      await c.foto("etiqueta");
      await c.quando("repare", 1, 1.0);
      await c.foco("#tablet", null, 1);
      await c.realcar(f.locator(".cartao:has(h2:text-is('Pedidos em aberto'))").first());
      await c.P("nota", "Acesso por função", "Pedido, cliente e pizzas. Nenhum valor em reais.", 1180, 640);
      await c.foto("sem_valor");
    },
  },
  c07_massa: {
    async prep(c, page) {
      await c.P("realce", null); await c.P("nota", "", ""); await c.P("esconderCursor");
      c.f = await abrirApp(page, "#ft", "elisa");
      await c.P("rotulo", "#rt", "📱 Tablet da massa · <b>Elisa</b>");
    },
    async roda(c) {
      const f = c.f;
      await c.P("capitulo", "05", "Produção · massa");
      await c.quando("esperando", 1, 0.3);
      await c.foco("#tablet", f.locator(".cartao:has(h2:text-is('Massa aberta'))").first(), 1.35);
      await c.quando("precisa", 1, 0.9);
      await c.foco("#tablet", null, 1);
      await c.digitar(campo(f, "Quantidade", "input"), "20", { toque: true });
      await c.quando("lote", 1, 0.3);
      await c.clicar(botao(f, "Lançar lote de massa"), { toque: true });
      await c.foto("lote");
    },
  },
  c08_acesso: {
    async prep(c, page) {
      await c.P("esconderCursor");
      c.fa = await abrirApp(page, "#fa", "diego");
      c.fb = await abrirApp(page, "#fb", "carla");
      await c.P("rotulo", "#ra", "Pizzaiolo · <b>Diego</b>");
      await c.P("rotulo", "#rb", "Gerente · <b>Carla</b>");
    },
    async roda(c) {
      await c.P("capitulo", "06", "Acesso rígido por função"); await c.P("aparelho", "duo");
      await c.quando("servidor", 1, 0.2);
      await c.P("nota", "Conferido no servidor", "8 perfis · 55 permissões · cada chamada checada", 745, 820);
      await c.quando("pizzaiolo", 1, 0.2);
      await c.realcar(c.fa.locator("nav.menu").first());
      await c.quando("gerente", 1, 0.2);
      await c.realcar(c.fb.locator("nav.menu").first());
      await c.foto("duo");
    },
  },
  c09_caixa: {
    async prep(c, page) {
      await c.P("realce", null); await c.P("nota", "", ""); await c.P("esconderCursor");
      c.ft = await abrirApp(page, "#ft", "fabio");
      await fora(c.ft.locator(".subnav button:text-is('Despacho')").first());
      c.f1 = await abrirApp(page, "#f1", "bruno");
      await fora(menu(c.f1, "Caixa e entregas"));
      await c.P("rotulo", "#rt", "📱 Tablet do despacho · <b>Fábio</b>");
    },
    async roda(c) {
      await c.P("capitulo", "07", "Despacho e caixa"); await c.P("aparelho", "tablet");
      await c.quando("escolhe", 1, 0.3);
      await c.escolher(c.ft.locator("select[aria-label^='Entregador do pedido']").first(), "Tiago Entregas", { toque: true });
      await c.clicar(botao(c.ft, "Despachar"), { toque: true });
      await c.quando("aberto", 1, 0.3);
      await c.P("nota", "Regra", "Sem caixa do dia aberto, não há despacho.", 1180, 640);
      await c.quando("noite", 1, 0.2);
      await c.P("nota", "", ""); await c.P("esconderCursor");
      // Fora do ar, entre as duas telas: o balcão dá a entrega como saída e acerta com o entregador (sem isso a contagem não abre).
      const hoje = await apiDemo("bruno", "GET", "/caixa/hoje");
      for (const e of hoje.entregas_pendentes) {
        await apiDemo("bruno", "POST", `/pedidos/${e.pedido_id}/situacao`, { situacao: "despachado ou retirado" });
        await apiDemo("bruno", "POST", "/caixa/acertos", { entregador_id: e.entregador_id });
      }
      const conta = contagemCaixa();
      const f = c.f1;
      await fora(menu(f, "Caixa e entregas"));
      await c.P("aparelho", "navegador");
      await c.quando("gaveta", 1, 0.2);
      await c.realcar(f.locator(".cartao:has(h2:text-is('Contagem do fim do dia'))").first());
      for (const forma of ["dinheiro", "pix", "credito", "debito"]) await c.digitar(campo(f, forma, "input"), conta[forma], { ms: 450 });
      await c.quando("revela", 1, 0.8);
      await c.P("realce", null);
      await c.clicar(botao(f, "Registrar contagem"));
      await dormir(600);
      await c.quando("tolerância", 1, 0.3);
      await c.realcar(f.locator(".cartao:has(h2:text-is('Resultado da contagem'))").first());
      await c.P("nota", "Contagem cega", "O esperado só aparece depois da contagem. Quem contou não aprova a própria diferença; o subgerente também não.", 200, 560);
      await c.foto("contagem");
    },
  },
  c10_estoque: {
    async prep(c, page) {
      await c.P("realce", null); await c.P("nota", "", ""); await c.P("esconderCursor");
      c.f = await abrirApp(page, "#f1", "carla");
      await fora(area(c.f, "Admin")); await fora(menu(c.f, "Estoque"));
      await dormir(600);
    },
    async roda(c) {
      const f = c.f;
      await c.P("capitulo", "08", "Estoque e vendas fechadas");
      await c.quando("ficha", 1, 0.3);
      await c.realcar(f.locator("tr:has(td:text-is('Calabresa'))").first());
      await c.quando("calabresa", 1, 0.5);
      await c.P("realce", null);
      await c.clicar(sub(f, "Alertas"));
      await c.quando("alerta", 1, 0.1);
      await c.realcar(f.locator("tr:has(td:text-is('Calabresa'))").first());
      await c.quando("toque", 1, 0.4);
      await c.P("realce", null);
      await c.clicar(f.locator("tr:has(td:text-is('Calabresa')) button").first());
      await c.foto("fechada");
      await c.quando("balcão", 1, 0.6);
      await c.clicar(area(f, "Vendas"));
      await dormir(700);
      const s1 = campo(f, "Sabor 1");
      await s1.evaluate((s) => { s.size = 7; s.style.height = "auto"; });  // mostra a lista aberta (só no vídeo)
      await s1.scrollIntoViewIfNeeded(); await dormir(200);
      await c.foco("#navegador", s1, 1.6);
      await c.P("nota", "No balcão", "Sabores com calabresa: VENDA FECHADA, sem opção de escolha.", 1300, 760);
      await c.foto("balcao");
    },
  },
  c11_custos: {
    async prep(c) {
      await c.P("realce", null); await c.P("nota", "", ""); await c.P("esconderCursor");
      await c.P("camera", "#navegador", 1, 0, 0);
      await fora(area(c.f, "Admin")); await fora(menu(c.f, "Custos")); await dormir(800);
    },
    async roda(c) {
      const f = c.f;
      await c.P("capitulo", "09", "Custo e margem por produto");
      await c.quando("custo", 2, 0.2);
      await c.realcar(f.locator("thead").first());
      await c.quando("tamanho", 1, 0.2);
      await c.realcar(f.locator("tr:has(td:text-is('Frango com Catupiry'))").first());
      await c.quando("lucro", 1, 0.3);
      await c.P("nota", "Para decidir", "Margem real de cada sabor, por tamanho, com o custo médio dos insumos.", 1240, 640);
      await c.foto("custos");
    },
  },
  c12_checklists: {
    async prep(c) {
      await c.P("realce", null); await c.P("nota", "", ""); await c.P("esconderCursor");
      await fora(menu(c.f, "Checklists")); await dormir(800);
    },
    async roda(c) {
      const f = c.f;
      await c.P("capitulo", "10", "Checklists da rotina");
      await c.quando("início", 1, 0.2);
      await c.clicar(f.locator(".cartao:has(h2:has-text('Início do dia')) button:text-is('Iniciar')").first());
      await dormir(800);
      await c.foto("aberto");
      const num = f.locator(".chk-item:has(input[inputmode='decimal'])");
      await c.quando("temperatura", 1, 0.6);
      if (await num.count()) {
        await c.digitar(num.nth(0).locator("input").first(), "3", { ms: 400 });
        await c.clicar(num.nth(0).locator("button:text-is('Registrar')").first(), { ms: 400 });
        await dormir(700);
      }
      await c.quando("padrão", 1, 1.5);
      const num2 = f.locator(".chk-item:has(input[inputmode='decimal'])");
      if (await num2.count() > 1) {
        await c.digitar(num2.nth(1).locator("input").first(), "-12", { ms: 400 });
        await c.clicar(num2.nth(1).locator("button:text-is('Registrar')").first(), { ms: 400 });
        await dormir(400);
        const acao = f.locator("input[placeholder^='Valor fora do limite']").first();
        if (await acao.count()) {
          await c.digitar(acao, "Porta ajustada; nova medição", { ms: 400 });
          await c.clicar(f.locator("button:text-is('Salvar')").first());
        }
        await c.foto("fora");
      }
      await c.quando("gerência", 1, 0.6);
      await c.clicar(f.locator("button:text-is('Voltar')").first());
      await c.quando("aderência", 1, 0.2);
      await c.clicar(f.locator("button:text-is('Aderência')").first());
      await c.foto("aderencia");
    },
  },
  c13_bi: {
    async prep(c) {
      await c.P("realce", null); await c.P("nota", "", ""); await c.P("esconderCursor");
      await fora(menu(c.f, "BI")); await dormir(900);
    },
    async roda(c) {
      const f = c.f;
      await c.P("capitulo", "11", "BI · painel do dia");
      await c.quando("vendas", 1, 0.2);
      await c.realcar(f.locator(".cartao:has-text('Vendas de hoje')").first());
      await c.quando("tempo", 1, 0.2);
      await c.realcar(f.locator(".cartao:has-text('Tempo médio')").first());
      await c.quando("custo", 1, 0.2);
      await c.realcar(f.locator(".cartao:has-text('CMV do mês')").first());
      await c.quando("alerta", 1, 0.2);
      await c.realcar(f.locator(".cartao:has(h2:text-is('Alertas'))").first());
      await c.foto("alerta");
      await c.quando("dre", 1, 0.3);
      await c.P("realce", null);
      await c.clicar(sub(f, "DRE"));
      await c.quando("lucratividade", 1, 0.3);
      await c.clicar(sub(f, "Lucratividade"));
      await c.foto("lucratividade");
    },
  },
  c14_numeros: {
    async roda(c) {
      await c.P("esconderCursor"); await c.P("realce", null); await c.P("aparelho", "nenhum"); await c.P("capitulo", "12", "O projeto em números");
      const n = c.dados.numeros;
      await c.P("camada", `<div class="linha medio">contados direto do código</div><div class="numeros">
        <div class="num linha"><b id="n1">0</b><span>versões do banco de dados</span></div><div class="num linha"><b id="n2">0</b><span>tabelas</span></div>
        <div class="num linha"><b id="n3">0</b><span>rotas de API</span></div><div class="num linha"><b id="n4" class="ouro">0</b><span>testes automatizados</span></div></div>
        <div class="linha selo">✔ todos passando · revisão dupla em cada entrega</div>`);
      await c.P("linha", 0);
      await c.quando("vinte", 1, 0.2); await c.P("linha", 1); await c.P("contar", "n1", n.migracoes, 900);
      await c.quando("cento", 1, 0.2); await c.P("linha", 2); await c.P("contar", "n2", n.tabelas, 900);
      await c.quando("duzentas", 1, 0.2); await c.P("linha", 3); await c.P("contar", "n3", n.rotas, 900);
      await c.quando("trezentos", 1, 0.2); await c.P("linha", 4); await c.P("contar", "n4", n.testes, 1100);
      await c.quando("passando", 1, 0.2); await c.P("linha", 5);
      await c.foto("numeros");
    },
  },
  c15_roadmap: {
    async roda(c) {
      await c.P("capitulo", "13", "Próximos passos");
      await c.P("camada", `<div class="linha grande">Próximos passos</div><div class="etapas">
        <div class="etapa linha"><i>1</i>Anota Ai por API, com aceite automático<em>aguardando acesso oficial</em></div>
        <div class="etapa linha"><i>2</i>iFood<em>em seguida</em></div>
        <div class="etapa linha"><i>3</i>Computador na loja para o piloto<em>decisão</em></div>
        <div class="etapa linha"><i>4</i>Nuvem<em>quando fizer sentido</em></div></div>`);
      await c.P("linha", 0);
      await c.quando("anota", 1, 0.2); await c.P("linha", 1);
      await c.quando("ifood", 1, 0.2); await c.P("linha", 2);
      await c.quando("computador", 1, 0.2); await c.P("linha", 3);
      await c.quando("nuvem", 1, 0.2); await c.P("linha", 4);
      await c.foto("roadmap");
    },
  },
  c16_fechamento: {
    async roda(c) {
      await c.P("capitulo", "", "");
      await c.P("camada", `<div class="linha medio">Já funciona. Já foi testado em tablet.</div>
        <div class="linha grande" style="margin-top:24px">Falta uma decisão:</div>
        <div class="linha selo" style="font-size:44px;padding:26px 60px">aprovar o piloto na pizzaria</div>`);
      await c.P("linha", 0);
      await c.quando("falta", 1, 0.2); await c.P("linha", 1);
      await c.quando("aprovar", 1, 0.2); await c.P("linha", 2);
      await c.quando("sistema", 2, 0.3);
      await c.P("camada", `<img class="logo-grande linha" src="logo.svg" alt=""><div class="linha enorme">Sistema Integrado<br><span class="ouro">da Pizzaria</span></div>
        <div class="linha medio" style="margin-top:30px">Cada pizza, cada real, sob controle.</div>`);
      await dormir(150); await c.P("linha", 0); await dormir(250); await c.P("linha", 1);
      await c.quando("cada", 1, 0.2); await c.P("linha", 2);
      await c.foto("fim");
      await c.ate(c.t.duracao - 0.8); await c.P("vinheta", 1);
    },
  },
};

// ---------------------------------------------------------------- dados que as cenas precisam (lidos da API da demonstração)
async function dadosDemo() {
  const login = await fetch(APP + "/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario: "admin", senha: SENHA }) });
  if (!login.ok) throw new Error("Login de admin da demonstração falhou: " + login.status);
  const numeros = ROTEIRO.numeros;  // mesma fonte que o texto da narração da c14; conferir com contagem.py antes de gravar
  const fala = ROTEIRO.cenas.find((c) => c.id === "c14_numeros").texto;
  for (const palavra of ["vinte e quatro", "cento e dez", "duzentas e setenta", "trezentos e setenta e quatro"]) {
    if (!fala.includes(palavra)) throw new Error("A narração da c14 não fala '" + palavra + "': alinhe narracao.json (numeros e texto)");
  }
  const hoje = await apiDemo("carla", "GET", "/caixa/hoje");
  const dataHoje = new Date().toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });
  if (!hoje.caixa || hoje.caixa.situacao !== "aberto" || hoje.caixa.data !== dataHoje) throw new Error("Sem caixa de hoje aberto na demonstração: rode preparar_demo.sh no mesmo dia da gravação");
  return { numeros };
}

const tokens = {};
async function apiDemo(usuario, metodo, caminho, corpo) {
  if (!tokens[usuario]) {
    const r = await fetch(APP + "/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario, senha: SENHA }) });
    if (!r.ok) throw new Error("Login de " + usuario + " falhou: " + r.status);
    tokens[usuario] = (await r.json()).token;
  }
  const r = await fetch(APP + "/api" + caminho, { method: metodo, headers: { Authorization: "Bearer " + tokens[usuario], "Content-Type": "application/json" },
    body: corpo === undefined ? undefined : JSON.stringify(corpo) });
  if (!r.ok) throw new Error(`${metodo} ${caminho}: ${r.status} ${await r.text()}`);
  return r.json();
}

function contagemCaixa() {
  // Valores que a atendente "conta": o esperado de cada forma (calculado pelo próprio serviço do sistema, no banco _demo),
  // com R$ 5,00 a menos no dinheiro, acima da tolerância de R$ 2,00. A tela continua cega: nada disto aparece antes da contagem.
  const py = `import json\nfrom api.config import LOJA_ID\nfrom api.database import get_connection\nfrom api.services import caixa\n` +
    `c = get_connection()\ncx = caixa.ultimo_caixa(c, LOJA_ID)\ne = caixa.esperado(c, LOJA_ID, caixa.faixa(c, LOJA_ID, cx), cx["fundo_troco"])\n` +
    `print(json.dumps({k: str(v) for k, v in e.items()}))`;
  if (!(process.env.DB_NAME || "").endsWith("_demo")) throw new Error("DB_NAME precisa ser o banco _demo");
  if (!process.env.SISTEMA) throw new Error("Defina SISTEMA com a pasta sistema/ do repositório");
  const r = spawnSync("python3", ["-c", py], { env: { ...process.env, PYTHONPATH: process.env.SISTEMA }, encoding: "utf8" });
  if (r.status !== 0) throw new Error("Cálculo do esperado falhou: " + r.stderr);
  const esp = JSON.parse(r.stdout.trim().split("\n").pop());
  const v = (k, menos = 0) => (Number(esp[k] || 0) - menos).toFixed(2).replace(".", ",");
  return { dinheiro: v("dinheiro", 5), pix: v("pix"), credito: v("credito"), debito: v("debito") };
}

// Acha a primeira linha da página na tela: o palco pinta uma linha magenta no topo; um quadro da tela inteira mostra onde ela está.
async function calibrar(page) {
  await dormir(800);
  const r = spawnSync("ffmpeg", ["-loglevel", "error", "-f", "x11grab", "-video_size", "1920x1300", "-i", DISPLAY + ".0", "-frames:v", "1",
    "-vf", "crop=1:1300:960:0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], { maxBuffer: 1 << 20 });
  const px = r.stdout;
  for (let y = 0; y < 1300; y++) if (px[3 * y] > 240 && px[3 * y + 1] < 30 && px[3 * y + 2] > 240) {
    if (y + 1080 > 1300) break;
    return y;
  }
  throw new Error("Calibração da captura falhou: linha de referência não encontrada na tela");
}

async function main() {
  const srv = await servirPalco();
  let xvfb = null;
  if (!TESTE) {
    xvfb = spawn("Xvfb", [DISPLAY, "-screen", "0", "1920x1300x24", "-nolisten", "tcp"], { stdio: "ignore" });
    await dormir(1500);
  }
  const browser = await chromium.launch({
    headless: TESTE, env: { ...process.env, DISPLAY },
    args: ["--window-position=0,0", "--hide-scrollbars", "--disable-infobars", "--force-device-scale-factor=1", "--lang=pt-BR",
      "--disable-features=Translate,TranslateUI", "--no-first-run", "--no-default-browser-check"],
  });
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, timezoneId: "America/Sao_Paulo", locale: "pt-BR" });
  // Só no navegador da gravação: permite exibir o sistema dentro do palco (o servidor proíbe ser emoldurado).
  await ctx.route(APP + "/**", async (route) => {
    const resp = await route.fetch();
    const cab = { ...resp.headers() };
    delete cab["x-frame-options"];
    if (cab["content-security-policy"]) cab["content-security-policy"] = cab["content-security-policy"].replace(/frame-ancestors[^;]*;?/, "");
    await route.fulfill({ response: resp, headers: cab });
  });
  const page = await ctx.newPage();
  page.on("dialog", (d) => d.accept());
  page.on("pageerror", (e) => console.error("[palco]", e.message));
  await page.goto(`http://127.0.0.1:${PORTA_PALCO}/palco.html`);
  if (!TESTE) TOPO = await calibrar(page);
  await page.evaluate(() => window.P.calibrado());
  const base = await dadosDemo();
  const relatorio = [];
  let estado = {};
  for (const id of ROTEIRO.versao_completa) {
    const def = CENAS[id];
    const c = new Cena(page, id);
    c.f = estado.f; c.dados = { ...base };
    if (def.prep) await def.prep(c, page);
    estado.f = c.f || estado.f;
    if (SO && !SO.includes(id)) continue;
    const arquivo = path.join(SAIDA, id + ".mp4");
    const rec = TESTE ? null : iniciarFfmpeg(arquivo);
    // Sincronia: um traço magenta na primeira linha da tela por ~100 ms; montar.py acha o quadro dele no arquivo.
    // A cena começa MARCA_ANTES segundos depois, então o traço nunca aparece no vídeo final.
    let marca = 0;
    if (rec) {
      await dormir(900);
      if (!rec.vivo()) throw new Error("ffmpeg não começou a gravar (Xvfb no ar?)");
      await page.evaluate(() => window.P.marca()); marca = Date.now();
      await dormir(400);
    }
    c.t0 = Date.now();
    let erro = null;
    try { await def.roda(c); } catch (e) { erro = e.message; console.error(`[${id}] ERRO: ${e.message}`); await c.foto("erro"); }
    await c.ate(c.t.duracao);
    const atraso = (Date.now() - c.t0) / 1000 - c.t.duracao;
    if (rec) { await dormir(600); await rec.parar(); }
    relatorio.push({ id, duracao: +c.t.duracao.toFixed(3), marca_antes: rec ? +((c.t0 - marca) / 1000).toFixed(3) : 0,
      atraso: +atraso.toFixed(2), erro });
    console.log(`[ok] ${id}: ${c.t.duracao.toFixed(1)} s` + (atraso > 0.3 ? ` (passou ${atraso.toFixed(1)} s)` : ""));
  }
  // Junta com um cenas.json anterior (gravação de só algumas cenas substitui só essas).
  const arqRel = path.join(SAIDA, "cenas.json");
  const antes = fs.existsSync(arqRel) ? JSON.parse(fs.readFileSync(arqRel, "utf8")).filter((x) => !relatorio.some((r) => r.id === x.id)) : [];
  const todos = [...antes, ...relatorio].sort((a, b) => ROTEIRO.versao_completa.indexOf(a.id) - ROTEIRO.versao_completa.indexOf(b.id));
  fs.writeFileSync(arqRel, JSON.stringify(todos, null, 1));
  const ruins = relatorio.filter((r) => r.erro || r.atraso > 0.3);
  if (ruins.length) console.error("[atenção] cenas com erro ou atraso (montar.py recusa): " + ruins.map((r) => r.id).join(", "));
  await browser.close(); srv.close(); if (xvfb) xvfb.kill();
}

main().catch((e) => { console.error(e); process.exit(1); });
