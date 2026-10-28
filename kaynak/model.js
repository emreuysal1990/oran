// ============================================================================ model.js
// Oran modeli (Python'daki modelkit.py + araştırma/genis.py'nin birebir JS karşılığı; parite testi ile doğrulanır).
//  1) Oranlardan marj temizlenir, Poisson / Dixon-Coles skor matrisi uydurulur (beklenen ev ve deplasman golü).
//  2) Skor matrisinden tüm gol pazarları, yarılar ve birleşik pazarlar hesaplanır.
//  3) Korner ve kart: negatif binom (takım özellikleri + lig seviyesi + beklenen gol).
//  4) NBA: normal dağılım modeli (galibiyet ihtimali ve toplam çizgisinden).
const BOM = (function () {
  "use strict";
  const G = 13;                                  // 0..12 gol
  const LF = new Float64Array(G);
  for (let k = 1; k < G; k++) LF[k] = LF[k - 1] + Math.log(k);
  const RHO_VARSAYILAN = -0.04, KAPPA_VARSAYILAN = 0.90;

  // ------------------------------------------------------------------ marj temizleme (güç yöntemi)
  function margGuc(oranlar) {
    const inv = oranlar.map(o => 1 / o);
    let lo = 1, hi = 3;
    for (let i = 0; i < 40; i++) {
      const mid = (lo + hi) / 2; let s = 0;
      for (const v of inv) s += Math.pow(v, mid);
      if (s > 1) lo = mid; else hi = mid;
    }
    const k = (lo + hi) / 2, p = inv.map(v => Math.pow(v, k)), t = p.reduce((a, b) => a + b, 0);
    return p.map(v => v / t);
  }

  // ------------------------------------------------------------------ Poisson / Dixon-Coles
  function pmfSatir(lam) {
    lam = Math.min(Math.max(lam, 1e-4), 9.0);
    const l = Math.log(lam), o = new Float64Array(G);
    for (let k = 0; k < G; k++) o[k] = Math.exp(-lam + k * l - LF[k]);
    return o;
  }
  // M[h*G + a]: bağımsız Poisson × Dixon-Coles düşük skor düzeltmesi × (fark >= 2 ağırlığı), toplamı 1
  function matris(lh, la, rho, kappa, normalle) {
    if (rho === undefined) rho = RHO_VARSAYILAN;
    if (kappa === undefined) kappa = KAPPA_VARSAYILAN;
    if (normalle === undefined) normalle = true;
    const ph = pmfSatir(lh), pa = pmfSatir(la), M = new Float64Array(G * G);
    for (let h = 0; h < G; h++) for (let a = 0; a < G; a++) M[h * G + a] = ph[h] * pa[a];
    if (rho !== 0) { M[0] *= 1 - lh * la * rho; M[1] *= 1 + lh * rho; M[G] *= 1 + la * rho; M[G + 1] *= 1 - rho; }
    let t = 0;
    for (let h = 0; h < G; h++) for (let a = 0; a < G; a++) { if (kappa !== 1 && Math.abs(h - a) >= 2) M[h * G + a] *= kappa; t += M[h * G + a]; }
    if (normalle) for (let i = 0; i < G * G; i++) M[i] /= t;
    return M;
  }
  // 1X2, ev golü dağılımı, deplasman golü dağılımı, toplam gol dağılımı
  function ozet(M) {
    let p1 = 0, px = 0, p2 = 0;
    const ev = new Float64Array(G), dp = new Float64Array(G), top = new Float64Array(2 * G - 1);
    for (let h = 0; h < G; h++) for (let a = 0; a < G; a++) {
      const v = M[h * G + a];
      if (h > a) p1 += v; else if (h === a) px += v; else p2 += v;
      ev[h] += v; dp[a] += v; top[h + a] += v;
    }
    return { p1, px, p2, ev, dp, top, m00: M[0] };
  }
  const topla = (d, a, b) => { let s = 0; for (let i = a; i <= b && i < d.length; i++) s += d[i]; return s; };

  // ------------------------------------------------------------------ oranlardan beklenen gol (damped Gauss-Newton)
  function uyumVektor(lh, la, rho, kappa) {
    const o = ozet(matris(lh, la, rho, kappa));
    return [o.p1, o.px, o.p2, 1 - topla(o.top, 0, 2)];
  }
  // p1,px,p2: marjsız ihtimaller; pu: 2,5 Üst ihtimali (null/NaN ise puOnsel, wOnsel ağırlığıyla kullanılır)
  function lambdaUydur(p1, px, p2, pu, opt) {
    opt = opt || {};
    const rho = opt.rho === undefined ? RHO_VARSAYILAN : opt.rho, kappa = opt.kappa === undefined ? KAPPA_VARSAYILAN : opt.kappa;
    const wOnsel = opt.wOnsel === undefined ? 0.3 : opt.wOnsel;
    const hedef = [p1, px, p2, 0], w = [1, 1, 1, 1];
    if (pu == null || Number.isNaN(pu)) { hedef[3] = opt.puOnsel == null ? 0.5 : opt.puOnsel; w[3] = wOnsel; } else hedef[3] = pu;
    let t1 = Math.log(1.45), t2 = Math.log(1.1);
    const lo = Math.log(0.05), hi = Math.log(6.0), e = 1e-4;
    for (let it = 0; it < 30; it++) {
      const f0 = uyumVektor(Math.exp(t1), Math.exp(t2), rho, kappa);
      const fa = uyumVektor(Math.exp(t1 + e), Math.exp(t2), rho, kappa);
      const fb = uyumVektor(Math.exp(t1), Math.exp(t2 + e), rho, kappa);
      let a11 = 1e-6, a12 = 0, a22 = 1e-6, g1 = 0, g2 = 0;
      for (let i = 0; i < 4; i++) {
        const r = (f0[i] - hedef[i]) * w[i], j1 = (fa[i] - f0[i]) / e * w[i], j2 = (fb[i] - f0[i]) / e * w[i];
        a11 += j1 * j1; a12 += j1 * j2; a22 += j2 * j2; g1 += j1 * r; g2 += j2 * r;
      }
      const det = a11 * a22 - a12 * a12;
      const d1 = Math.min(Math.max(-(a22 * g1 - a12 * g2) / det, -0.4), 0.4);
      const d2 = Math.min(Math.max(-(-a12 * g1 + a11 * g2) / det, -0.4), 0.4);
      t1 = Math.min(Math.max(t1 + d1, lo), hi); t2 = Math.min(Math.max(t2 + d2, lo), hi);
      if (Math.max(Math.abs(d1), Math.abs(d2)) < 1e-7) break;
    }
    return [Math.exp(t1), Math.exp(t2)];
  }
  const sig = x => 1 / (1 + Math.exp(-x));
  const logit = p => { p = Math.min(Math.max(p, 1e-4), 1 - 1e-4); return Math.log(p / (1 - p)); };
  // 2,5 Alt/Üst oranı olmayan maçlar için 2,5 Üst ihtimali tahmini (lig seviyesi + 1X2). w: 6 katsayı
  function puOnsel(p1, px, p2, ligOrani, w) {
    const f = [1, logit(ligOrani == null ? 0.5 : ligOrani), px, (p1 - p2) * (p1 - p2), Math.abs(p1 - p2), Math.max(p1, p2)];
    let z = 0; for (let i = 0; i < 6; i++) z += f[i] * w[i];
    return sig(z);
  }
  // ham oranlardan (1,X,2 ve varsa Üst, Alt) beklenen gol
  function oranlardanLambda(o1, ox, o2, ou, oa, kat, ligUstOrani) {
    const [p1, px, p2] = margGuc([o1, ox, o2]);
    const pu = ou && oa ? margGuc([ou, oa])[0] : null;
    const on = pu == null ? puOnsel(p1, px, p2, ligUstOrani, kat.pu_onsel_w) : null;
    return lambdaUydur(p1, px, p2, pu, { rho: kat.rho, kappa: kat.kappa, puOnsel: on });
  }

  // ------------------------------------------------------------------ korner / kart (negatif binom)
  // oz: [h_atan, h_yiyen, d_atan, d_yiyen, lig_toplam] (null olabilir); t: kat.c ya da kat.k; lig: lig kodu
  function kkOrtalama(oz, lh, la, lig, t) {
    if (!oz || !t) return null;
    const c = t.lig[lig]; if (c === undefined) return null;
    const x = [lh + la, Math.abs(lh - la), lh, la, oz[0], oz[1], oz[2], oz[3], oz[4]];
    let z = t.b + c;
    for (let i = 0; i < 9; i++) { if (x[i] == null || Number.isNaN(x[i])) continue; z += t.w[i] * (x[i] - t.ort[i]) / t.sd[i]; }
    return Math.exp(Math.min(Math.max(z, -5), 5));
  }
  // P(Y = k), k = 0..kmax; Var = mu + alfa mu^2
  function nbTablo(mu, alfa, kmax) {
    kmax = kmax || 40;
    const r = 1 / alfa, p = r / (r + mu), o = new Float64Array(kmax + 1);
    o[0] = Math.pow(p, r);
    for (let k = 0; k < kmax; k++) o[k + 1] = o[k] * (k + r) / (k + 1) * (1 - p);
    return o;
  }
  const kumulatif = d => { const c = new Float64Array(d.length); let s = 0; for (let i = 0; i < d.length; i++) { s += d[i]; c[i] = s; } return c; };
  const KORNER = [["K75U", 8, 1], ["K85U", 9, 1], ["K85A", 9, 0], ["K95U", 10, 1], ["K95A", 10, 0], ["K105U", 11, 1], ["K105A", 11, 0], ["K115A", 12, 0]];
  const KART = [["C25U", 3, 1], ["C35U", 4, 1], ["C35A", 4, 0], ["C45U", 5, 1], ["C45A", 5, 0], ["C55U", 6, 1], ["C55A", 6, 0]];
  function kkPazarlar(mu, alfa, liste, out) {
    const c = kumulatif(nbTablo(mu, alfa));
    for (const [kod, esik, ust] of liste) { const p = 1 - c[esik - 1]; out[kod] = ust ? p : 1 - p; }
  }

  // ------------------------------------------------------------------ gol pazarları (51 pazarın gol / yarı bölümü)
  function temelPazarlar(lh, la, kat, mc, mk) {
    const rho = kat.rho, kappa = kat.kappa, fh = kat.fh, fa = kat.fa;
    const o = ozet(matris(lh, la, rho, kappa)), out = {};
    const T = o.top, evc = kumulatif(o.ev), dpc = kumulatif(o.dp), c = kumulatif(T);
    out.MS1 = o.p1; out.MSX = o.px; out.MS2 = o.p2; out.CS1X = o.p1 + o.px; out.CSX2 = o.px + o.p2; out.CS12 = o.p1 + o.p2;
    for (const [k, i] of [[15, 1], [25, 2], [35, 3], [45, 4]]) { out["A" + k] = c[i]; out["U" + k] = 1 - c[i]; }
    const kgv = 1 - o.ev[0] - o.dp[0] + o.m00; out.KGV = kgv; out.KGY = 1 - kgv;
    out.EV05A = evc[0]; out.EV05U = 1 - evc[0]; out.EV15A = evc[1]; out.EV15U = 1 - evc[1]; out.EV25U = 1 - evc[2];
    out.DEP05A = dpc[0]; out.DEP05U = 1 - dpc[0]; out.DEP15A = dpc[1]; out.DEP15U = 1 - dpc[1]; out.DEP25U = 1 - dpc[2];
    // ilk yarı: bağımsız Poisson (düzeltmesiz, normalleştirilmemiş), ikinci yarı toplamı ~ Poisson
    const Mh = matris(lh * fh, la * fa, 0, 1, false);   // yalnızca bağımsız çarpım (Python ile aynı: düzeltmesiz, normalleştirilmemiş)
    const h = ozet(Mh), ch = kumulatif(h.top);
    out.IY1 = h.p1; out.IYX = h.px; out.IY2 = h.p2;
    out.IY05A = ch[0]; out.IY05U = 1 - ch[0]; out.IY15A = ch[1]; out.IY15U = 1 - ch[1];
    out.IYKGV = (1 - h.ev[0]) * (1 - h.dp[0]);
    const l2 = lh * (1 - fh) + la * (1 - fa), e0 = Math.exp(-l2);
    out.IY2Y05U = 1 - e0; out.IY2Y15U = 1 - e0 * (1 + l2);
    if (mc != null && kat.c) kkPazarlar(mc, kat.c.alfa, KORNER, out);
    if (mk != null && kat.k) kkPazarlar(mk, kat.k.alfa, KART, out);
    return out;
  }

  // ------------------------------------------------------------------ birleşik / ek pazarlar
  function skellam(l1, l2) {                       // iki bağımsız Poisson farkı; indeks d + 12 (d = -12..12)
    const p1 = pmfSatir(l1), p2 = pmfSatir(l2), o = new Float64Array(25);
    for (let h = 0; h < G; h++) for (let a = 0; a < G; a++) o[h - a + 12] += p1[h] * p2[a];
    return o;
  }
  function genisPazarlar(lh, la, kat) {
    const rho = kat.rho, kappa = kat.kappa, fh = kat.fh, fa = kat.fa;
    const M = matris(lh, la, rho, kappa), out = {};
    const topM = (f) => { let s = 0; for (let h = 0; h < G; h++) for (let a = 0; a < G; a++) if (f(h, a)) s += M[h * G + a]; return s; };
    const sonuc = { "1": (h, a) => h > a, "X": (h, a) => h === a, "2": (h, a) => h < a };
    const u25 = (h, a) => h + a >= 3, a25 = (h, a) => h + a <= 2, kgv = (h, a) => h > 0 && a > 0, kgy = (h, a) => h === 0 || a === 0;
    for (const s of ["1", "X", "2"]) {
      const f = sonuc[s];
      out["MS" + s + "_U25"] = topM((h, a) => f(h, a) && u25(h, a)); out["MS" + s + "_A25"] = topM((h, a) => f(h, a) && a25(h, a));
      out["MS" + s + "_KGV"] = topM((h, a) => f(h, a) && kgv(h, a)); out["MS" + s + "_KGY"] = topM((h, a) => f(h, a) && kgy(h, a));
    }
    for (const [ad, f] of [["1X", (h, a) => h >= a], ["X2", (h, a) => h <= a], ["12", (h, a) => h !== a]]) {
      out[ad + "_U25"] = topM((h, a) => f(h, a) && u25(h, a)); out[ad + "_A25"] = topM((h, a) => f(h, a) && a25(h, a));
    }
    out.KGV_U25 = topM((h, a) => kgv(h, a) && u25(h, a)); out.KGV_A25 = topM((h, a) => kgv(h, a) && a25(h, a));
    out.KGY_U25 = topM((h, a) => kgy(h, a) && u25(h, a)); out.KGY_A25 = topM((h, a) => kgy(h, a) && a25(h, a));
    out.TG01 = topM((h, a) => h + a <= 1); out.TG23 = topM((h, a) => h + a >= 2 && h + a <= 3);
    out.TG46 = topM((h, a) => h + a >= 4 && h + a <= 6); out.TG7P = topM((h, a) => h + a >= 7);
    out.TEK = 0.5; out.CIFT = 0.5;                 // model tek/çift için bilgi eklemiyor (gerçek oran ≈ %50)
    out.A05 = topM((h, a) => h + a === 0); out.U05 = 1 - out.A05;
    out.U55 = topM((h, a) => h + a >= 6); out.A55 = 1 - out.U55;
    for (const hn of [-2, -1, 1, 2]) {
      const ad = "HND" + (hn < 0 ? "m" : "p") + Math.abs(hn);
      out[ad + "_1"] = topM((h, a) => h + hn - a > 0); out[ad + "_X"] = topM((h, a) => h + hn - a === 0); out[ad + "_2"] = topM((h, a) => h + hn - a < 0);
    }
    // yarılar (bağımsız Poisson) ve İY/MS
    const l1h = lh * fh, l1a = la * fa, l2h = lh * (1 - fh), l2a = la * (1 - fa), dm = 12;
    const D1 = skellam(l1h, l1a), D2 = skellam(l2h, l2a);
    const sum = (d, a, b) => { let s = 0; for (let i = a; i <= b; i++) s += d[i]; return s; };
    const P1 = { "1": sum(D1, dm + 1, 2 * dm), "X": D1[dm], "2": sum(D1, 0, dm - 1) };
    out.Y2_1 = sum(D2, dm + 1, 2 * dm); out.Y2_X = D2[dm]; out.Y2_2 = sum(D2, 0, dm - 1);
    const c2 = kumulatif(D2);
    const le = x => { x = Math.max(Math.min(x, dm), -dm - 1); return x < -dm ? 0 : c2[x + dm]; };
    const ftd = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
    const gruplar = [[0, d => d > 0], [1, d => d === 0], [2, d => d < 0]];
    for (const [i1, f] of gruplar) for (let d1 = -dm; d1 <= dm; d1++) {
      if (!f(d1)) continue;
      const p = D1[d1 + dm];
      ftd[i1][0] += p * (1 - le(-d1)); ftd[i1][1] += p * (le(-d1) - le(-d1 - 1)); ftd[i1][2] += p * le(-d1 - 1);
    }
    const msDc = [out.MS1_U25 + out.MS1_A25, out.MSX_U25 + out.MSX_A25, out.MS2_U25 + out.MS2_A25];
    const msH = [0, 1, 2].map(j => ftd[0][j] + ftd[1][j] + ftd[2][j]);
    let tot = 0;
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) { ftd[i][j] *= msDc[j] / msH[j]; tot += ftd[i][j]; }
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) out["IYMS_" + "1X2"[i] + "1X2"[j]] = ftd[i][j] / tot;
    out.IY1X = P1["1"] + P1["X"]; out.IYX2 = P1["X"] + P1["2"]; out.IY12 = P1["1"] + P1["2"];
    // en çok gol hangi yarıda
    const t1 = pmfSatir(l1h + l1a), t2 = pmfSatir(l2h + l2a), cc2 = kumulatif(t2);
    let y1 = 0, ye = 0;
    for (let k = 0; k < G; k++) { y1 += t1[k] * (k > 0 ? cc2[k - 1] : 0); ye += t1[k] * t2[k]; }
    out.YARI_1 = y1; out.YARI_E = ye; out.YARI_2 = 1 - y1 - ye;
    return out;
  }

  // ------------------------------------------------------------------ NBA (normal dağılım modeli)
  const NBA = { sM: 13.0, sT: 18.0, sH: 12.1 };
  function Phi(x) {                                // Abramowitz-Stegun 7.1.26 (hata < 1e-7)
    const z = Math.abs(x) / Math.SQRT2, t = 1 / (1 + 0.3275911 * z);
    const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-z * z);
    return x >= 0 ? 0.5 * (1 + y) : 0.5 * (1 - y);
  }
  function PhiInv(p) {                             // Acklam algoritması (göreli hata ~1e-9)
    p = Math.min(Math.max(p, 1e-9), 1 - 1e-9);
    const a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
    const b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01];
    const c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
    const d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
    let x;
    if (p < 0.02425) { const q = Math.sqrt(-2 * Math.log(p)); x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
    else if (p > 1 - 0.02425) { const q = Math.sqrt(-2 * Math.log(1 - p)); x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
    else { const q = p - 0.5, r = q * q; x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1); }
    return x;
  }
  // tamsayı değerli değişken X ~ N(mu, sd): P(X > L) ve P(X < L)  (L: çizgi; yarım sayı, tam sayı ya da çeyrek olabilir)
  const ustOlasilik = (L, mu, sd) => 1 - Phi((Math.floor(L) + 0.5 - mu) / sd);
  const altOlasilik = (L, mu, sd) => Phi((Math.ceil(L) - 0.5 - mu) / sd);
  // m: {o1,o2 (ML), hnd (ev handikabı), hO1,hO2, tot, tO,tU}; dönüş: pazar kodu -> ihtimal (iade hariç koşullu ihtimal)
  function nbaPazarlar(m) {
    const { sM, sT, sH } = NBA, out = {};
    const pml = margGuc([m.o1, m.o2])[0], mu = sM * PhiInv(pml);
    out.N_MS1 = pml; out.N_MS2 = 1 - pml;
    let muT = null;
    if (m.tot != null) {
      const pu = m.tO && m.tU ? margGuc([m.tO, m.tU])[0] : 0.5;
      muT = Math.floor(m.tot) + 0.5 + sT * PhiInv(pu);
      const pUst = ustOlasilik(m.tot, muT, sT), pAlt = altOlasilik(m.tot, muT, sT), push = 1 - pUst - pAlt;
      out.N_UST = pUst / (1 - push); out.N_ALT = pAlt / (1 - push);
    }
    if (m.hnd != null) {
      const L = -m.hnd;                            // ev kapatır: M > -hnd
      const pc = ustOlasilik(L, mu, sM), pd = altOlasilik(L, mu, sM), push = 1 - pc - pd;
      out.N_HEV = pc / (1 - push); out.N_HDEP = pd / (1 - push);
    }
    if (muT != null && m.hnd != null) {
      const muH = (muT + mu) / 2, muA = (muT - mu) / 2, evT = (m.tot - m.hnd) / 2, depT = (m.tot + m.hnd) / 2;
      const eu = ustOlasilik(evT, muH, sH), ea = altOlasilik(evT, muH, sH), du = ustOlasilik(depT, muA, sH), da = altOlasilik(depT, muA, sH);
      out.N_EVU = eu / (eu + ea); out.N_EVA = ea / (eu + ea); out.N_DEPU = du / (du + da); out.N_DEPA = da / (du + da);
    }
    const F = (a, b) => Phi((b - mu) / sM) - Phi((a - mu) / sM);       // ev lehine fark aralığı (a, b]
    out.N_E1 = F(0, 5.5); out.N_E6 = F(5.5, 10.5); out.N_E11 = F(10.5, 15.5); out.N_E16 = 1 - Phi((15.5 - mu) / sM);
    const Fd = (a, b) => Phi((b + mu) / sM) - Phi((a + mu) / sM);      // deplasman lehine
    out.N_D1 = Fd(0, 5.5); out.N_D6 = Fd(5.5, 10.5); out.N_D11 = Fd(10.5, 15.5); out.N_D16 = 1 - Phi((15.5 + mu) / sM);
    out.N_TEK = 0.5; out.N_CIFT = 0.5;
    return out;
  }

  // NBA beklenen fark (ev - dep) ve beklenen toplam sayı
  function nbaOrtalamalar(m) {
    const pml = margGuc([m.o1, m.o2])[0], mu = NBA.sM * PhiInv(pml);
    let muT = null;
    if (m.tot != null) { const pu = m.tO && m.tU ? margGuc([m.tO, m.tU])[0] : 0.5; muT = Math.floor(m.tot) + 0.5 + NBA.sT * PhiInv(pu); }
    return { mu, muT };
  }

  return { G, margGuc, matris, ozet, lambdaUydur, puOnsel, oranlardanLambda, kkOrtalama, nbTablo, kkPazarlar, temelPazarlar, genisPazarlar,
    nbaPazarlar, nbaOrtalamalar, Phi, PhiInv, NBA, KORNER, KART, RHO_VARSAYILAN, KAPPA_VARSAYILAN };
})();
if (typeof module !== "undefined" && module.exports) module.exports = BOM;
