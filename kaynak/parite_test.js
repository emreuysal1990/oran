// node parite_test.js  -> JS modelinin Python referansıyla farkı (parite.json'u arastirma/parite_uret.py üretir)
const B = require("./model.js"), kat = require("../katsayilar.json"), T = require("./parite.json");
let enBuyuk = {}, say = {};
function karsilastir(ad, a, b, tol) {
  const f = Math.abs(a - b);
  enBuyuk[ad] = Math.max(enBuyuk[ad] || 0, f); say[ad] = (say[ad] || 0) + 1;
  if (!(f <= tol)) { console.log("FARK", ad, a, b, f); process.exitCode = 1; }
}
for (const c of T.pazar) {
  const t = B.temelPazarlar(c.lh, c.la, kat, c.mc, c.mk), g = B.genisPazarlar(c.lh, c.la, kat);
  for (const k of Object.keys(c.temel)) { if (!(k in t)) { console.log("EKSİK temel", k); process.exitCode = 1; continue; } karsilastir("temel", t[k], c.temel[k], 1e-9); }
  for (const k of Object.keys(c.genis)) { if (!(k in g)) { console.log("EKSİK genis", k); process.exitCode = 1; continue; } karsilastir("genis", g[k], c.genis[k], 1e-9); }
}
for (const c of T.fit) {
  const [l1, l2] = B.oranlardanLambda(c.o[0], c.o[1], c.o[2], c.o[3], c.o[4], kat, c.lig_u);
  karsilastir("lambda", l1, c.lh, 2e-6); karsilastir("lambda", l2, c.la, 2e-6);
}
for (const c of T.kk) {
  const mu = B.kkOrtalama(c.oz, c.lh, c.la, c.lig, kat[c.t]);
  karsilastir("kk_mu", mu, c.mu, 1e-9);
}
for (const c of T.nba) {
  const p = B.nbaPazarlar(c.m);
  for (const k of Object.keys(c.p)) karsilastir("nba", p[k], c.p[k], 2e-6);
}
console.log("en büyük fark:", JSON.stringify(enBuyuk), " karşılaştırılan:", JSON.stringify(say));
