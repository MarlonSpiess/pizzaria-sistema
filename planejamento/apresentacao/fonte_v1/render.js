const { chromium } = require('/opt/node-tools/node_modules/playwright');
(async()=>{
 const b=await chromium.launch();
 for (const [src,out] of [['deck.html','Apresentacao_Comercial_Sistema_Pizzaria.pdf'],['flow.html','Fluxogramas_Sistema_Pizzaria.pdf']]){
  const pg=await b.newPage({viewport:{width:1920,height:1080}});
  await pg.goto('file://'+process.cwd()+'/'+src,{waitUntil:'networkidle'});
  await pg.evaluate(()=>document.fonts.ready);
  console.log(src, await pg.evaluate(()=>[...document.fonts].filter(f=>f.status=='loaded').map(f=>f.family).join(',')));
  await pg.pdf({path:out,width:'1920px',height:'1080px',printBackground:true});
 }
 await b.close();
})();
