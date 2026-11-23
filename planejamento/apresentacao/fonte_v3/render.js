// Converte os HTML gerados por gen_v3.py em PDF (1920x1080). Uso: node render.js
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  for (const [src, out] of [['sistema.html', '../Apresentacao_do_Sistema_v3.pdf'], ['comercial.html', '../Apresentacao_Comercial_v3.pdf'], ['fluxos.html', '../Fluxogramas_v3.pdf']]) {
    const pg = await b.newPage({ viewport: { width: 1920, height: 1080 } });
    await pg.goto('file://' + path.join(__dirname, src), { waitUntil: 'networkidle' });
    await pg.evaluate(() => document.fonts.ready);
    await pg.pdf({ path: path.join(__dirname, out), width: '1920px', height: '1080px', printBackground: true });
    console.log(out);
  }
  await b.close();
})();
