(function () {
  "use strict";
  try { document.documentElement.lang = "tr"; } catch (e) { }
  // ================================================================ sabitler
  const LIGLER = {
    E0: "İngiltere Premier Lig", E1: "İngiltere Championship", E2: "İngiltere League One", E3: "İngiltere League Two",
    EC: "İngiltere National League", SC0: "İskoçya Premiership", SC1: "İskoçya Championship", SC2: "İskoçya League One",
    SC3: "İskoçya League Two", D1: "Almanya Bundesliga", D2: "Almanya 2. Bundesliga", I1: "İtalya Serie A", I2: "İtalya Serie B",
    SP1: "İspanya La Liga", SP2: "İspanya La Liga 2", F1: "Fransa Ligue 1", F2: "Fransa Ligue 2", N1: "Hollanda Eredivisie",
    B1: "Belçika Pro Lig", P1: "Portekiz Liga", T1: "Türkiye Süper Lig", G1: "Yunanistan Süper Lig",
    USA: "ABD MLS", SWE: "İsveç Allsvenskan", NOR: "Norveç Eliteserien", DNK: "Danimarka Superliga", FIN: "Finlandiya Veikkausliiga",
    CL: "Şampiyonlar Ligi", EL: "Avrupa Ligi", ECL: "Konferans Ligi", NBA: "NBA", HES: "Hesaplayıcı"
  };
  const OK_AD = ["Bet365", "Piyasa ortalaması", "Pinnacle", "En yüksek oran", "Pinnacle (kapanış)", "Piyasa ortalaması (kapanış)", "Bahis şirketleri ortalaması"];
  const mkSpor = (ad, t) => Object.assign({}, t, { ad, TUM: [], FIK: [], SON_GUN: 0, ILK_GUN: 0, GECICI_SAY: 0 });
  const SP = { futbol: mkSpor("futbol", PAZ.futbol), nba: mkSpor("nba", PAZ.nba) };
  const sporOf = m => m.lig === "NBA" ? SP.nba : SP.futbol;
  const g = m => m.ms[0] + m.ms[1];
  const fark = m => m.ms[0] - m.ms[1];
  const sonucu = (pz, m) => { if (m[pz[3]] == null) return null; const r = pz[4](m); return r == null ? null : !!r; };
  let KAT = typeof KAT_YEDEK !== "undefined" ? KAT_YEDEK : null;   // modelin katsayıları (veri.json'daki "model" önceliklidir)

  // ================================================================ tarih
  const GMS = 864e5;
  const gunNo = (y, mo, d) => Math.round(Date.UTC(y, mo - 1, d) / GMS);
  const bugun = (() => { const n = new Date(); return gunNo(n.getFullYear(), n.getMonth() + 1, n.getDate()); })();
  const tOf = gn => new Date(gn * GMS);
  const iso = gn => tOf(gn).toISOString().slice(0, 10);
  const isoGun = s => { if (!s) return null; const [y, m, d] = s.split("-").map(Number); return gunNo(y, m, d); };
  const GUN = ["Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi"];
  const AY = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  const uzunTarih = gn => { const d = tOf(gn); return d.getUTCDate() + " " + AY[d.getUTCMonth()] + " " + GUN[d.getUTCDay()]; };
  const kisaTarih = gn => { const d = tOf(gn); return String(d.getUTCDate()).padStart(2, "0") + "." + String(d.getUTCMonth() + 1).padStart(2, "0") + "." + String(d.getUTCFullYear()).slice(2); };
  const sezonBasi = gn => { const d = tOf(gn); const y = d.getUTCMonth() >= 6 ? d.getUTCFullYear() : d.getUTCFullYear() - 1; return gunNo(y, 7, 1); };

  // ================================================================ yardımcılar
  const $ = id => document.getElementById(id);
  const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
  const virgul = x => x == null ? "–" : Number(x).toFixed(2).replace(".", ",");
  const ondalik = (x, n) => x == null ? "–" : Number(x).toFixed(n == null ? 1 : n).replace(".", ",");
  const cizgi = x => x == null ? "–" : (x > 0 ? "+" : "") + String(x).replace(".", ",");
  const yuzde = x => x == null ? "–" : "%" + Math.round(x * 100);
  const yuzde1 = x => x == null ? "–" : "%" + (x * 100).toFixed(1).replace(".", ",");
  const binlik = x => Number(x).toLocaleString("tr-TR");
  const adil = p => p == null || p <= 0 ? "–" : virgul(Math.max(1.01, 1 / p));
  const sonucIdx = m => m.ms[0] > m.ms[1] ? 0 : m.ms[0] === m.ms[1] ? 1 : 2;
  const saklaAl = (k, v) => { try { const s = localStorage.getItem(k); return s ? JSON.parse(s) : v; } catch (e) { return v; } };
  const saklaYaz = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { } };
  const oranOku = s => { const x = Number(String(s == null ? "" : s).trim().replace(",", ".")); return x > 1 && isFinite(x) ? x : null; };
  const bekle = () => new Promise(r => setTimeout(r, 0));

  // ================================================================ veri
  function mac(lig, gun, saat, ev, dep, o1, ox, o2, ou, oa, ms, iy, korner, kart, gecici, ok) {
    return { lig, gun, saat: saat || "", ev, dep, o1, ox, o2, ou: ou || null, oa: oa || null, ms: ms || null, iy: iy || null,
      korner: korner == null ? null : korner, kart: kart == null ? null : kart, gecici: !!gecici, ok: ok == null ? 0 : ok,
      lh: null, la: null, mc: null, mk: null, oz: null };
  }
  function nbaMac(gun, saat, ev, dep, ml1, ml2, hnd10, hO1, hO2, tot10, tO, tU, skor) {
    const o = x => x ? x / 100 : null, hnd = hnd10 == null ? null : hnd10 / 10, tot = tot10 == null ? null : tot10 / 10;
    return { lig: "NBA", gun, saat: saat || "", ev, dep, o1: o(ml1), o2: o(ml2), ox: null, hnd, hO1: o(hO1), hO2: o(hO2), tot, tO: o(tO), tU: o(tU),
      evT: tot != null && hnd != null ? (tot - hnd) / 2 : null, depT: tot != null && hnd != null ? (tot + hnd) / 2 : null,
      ms: skor || null, iy: null, korner: null, kart: null, gecici: false, ok: 6 };
  }
  const mKey = m => m.lig + "|" + m.gun + "|" + m.ev + "|" + m.dep;
  let OLUSTURMA = null, ODDS_API = null, SURUM = 1;
  function veriAc(V) {
    const T = V.takim, L = V.lig, o = x => x ? x / 100 : null;
    const F = SP.futbol, N = SP.nba;
    SURUM = V.surum || 1;
    if (V.model) KAT = V.model;
    const sonuclu = (r, gec) => {
      const m = mac(L[r[0]], r[1], r[2], T[r[3]], T[r[4]], r[11] / 100, r[12] / 100, r[13] / 100, o(r[14]), o(r[15]),
        [r[5], r[6]], r[7] == null ? null : [r[7], r[8]], r[9], r[10], gec, r[16]);
      if (r.length > 21) { m.lh = r[21]; m.la = r[22]; m.mc = r[23]; m.mk = r[24]; }
      return m;
    };
    F.TUM = V.m.map(r => sonuclu(r, false));
    const var_ = new Set(F.TUM.map(mKey));
    const gec = (V.g || []).map(r => sonuclu(r, true)).filter(m => !var_.has(mKey(m)));
    F.GECICI_SAY = gec.length; gec.forEach(m => { F.TUM.push(m); var_.add(mKey(m)); });
    F.FIK = (V.f || []).map(r => {
      const m = mac(L[r[0]], r[1], r[2], T[r[3]], T[r[4]], r[5] / 100, r[6] / 100, r[7] / 100, o(r[8]), o(r[9]), null, null, null, null, false, r[10]);
      if (r.length > 11) { m.lh = r[11]; m.la = r[12]; m.mc = r[13]; m.mk = r[14]; m.oz = r[15] || null; }
      return m;
    }).filter(m => !var_.has(mKey(m)));
    const nb = V.nba || { m: [], f: [] };
    N.TUM = nb.m.map(r => nbaMac(r[0], r[1], T[r[2]], T[r[3]], r[6], r[7], r[8], r[9], r[10], r[11], r[12], r[13], [r[4], r[5]]));
    N.FIK = nb.f.map(r => nbaMac(r[0], r[1], T[r[2]], T[r[3]], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], null));
    OLUSTURMA = V.olusturma || null; ODDS_API = V.odds_api || null;
    for (const S of [F, N]) {
      S.TUM.sort((a, b) => a.gun - b.gun || a.saat.localeCompare(b.saat));
      S.SON_GUN = S.TUM.reduce((a, m) => Math.max(a, m.gun), 0);
      S.ILK_GUN = S.TUM.reduce((a, m) => Math.min(a, m.gun), Infinity);
    }
  }

  // ================================================================ model hesapları
  // Maçın model değerleri: {lh, la, mc, mk}. ozel: kullanıcının girdiği {o1, ox, o2, ou, oa} (varsa onlardan yeniden hesaplanır)
  function modelDegerleri(m, ozel) {
    if (!KAT) return null;
    if (ozel) {
      const [lh, la] = BOM.oranlardanLambda(ozel.o1, ozel.ox, ozel.o2, ozel.ou, ozel.oa, KAT, m.oz ? m.oz[2] : null);
      return { lh, la, mc: m.oz ? BOM.kkOrtalama(m.oz[0], lh, la, m.lig, KAT.c) : null, mk: m.oz ? BOM.kkOrtalama(m.oz[1], lh, la, m.lig, KAT.k) : null };
    }
    if (m.lh == null) {      // veri dosyasında model değeri yoksa oranlardan hesapla (korner/kart olmadan)
      const [lh, la] = BOM.oranlardanLambda(m.o1, m.ox, m.o2, m.ou, m.oa, KAT, m.oz ? m.oz[2] : null);
      m.lh = lh; m.la = la;
    }
    return { lh: m.lh, la: m.la, mc: m.mc, mk: m.mk };
  }
  // liste için: önbellekli temel pazar ihtimalleri
  function temelOl(m) {
    if (m._t !== undefined) return m._t;
    let r = null;
    if (m.lig === "NBA") r = BOM.nbaPazarlar(m);
    else { const d = modelDegerleri(m, null); if (d) r = BOM.temelPazarlar(d.lh, d.la, KAT, d.mc, d.mk); }
    m._t = r; return r;
  }
  function genisOl(m) {
    if (m._g !== undefined) return m._g;
    let r = null; const d = m.lig === "NBA" ? null : modelDegerleri(m, null);
    if (d) r = BOM.genisPazarlar(d.lh, d.la, KAT);
    m._g = r; return r;
  }
  function ihtimal(m, kod) {
    const t = temelOl(m); if (!t) return null;
    if (kod in t) return t[kod];
    const gn = genisOl(m); return gn && kod in gn ? gn[kod] : null;
  }
  function piyasaIhtimali(m) {       // marjı çıkarılmış piyasa ihtimalleri
    if (m._p) return m._p;
    const p = { };
    if (m.lig === "NBA") { const q = BOM.margGuc([m.o1, m.o2]); p.p1 = q[0]; p.p2 = q[1]; }
    else { const q = BOM.margGuc([m.o1, m.ox, m.o2]); p.p1 = q[0]; p.px = q[1]; p.p2 = q[2]; if (m.ou && m.oa) p.pu = BOM.margGuc([m.ou, m.oa])[0]; }
    m._p = p; return p;
  }

  // ================================================================ durum ve filtreler
  const F = Object.assign({ pazar: {}, sira: "tarih", min: "" }, saklaAl("bob-filtre3", {}));
  if (typeof F.pazar !== "object" || !F.pazar) F.pazar = {};
  let C = SP[saklaAl("bob-spor", "futbol")] || SP.futbol;
  let gorunum = "g";
  const seciliPazar = () => C.PZ[F.pazar[C.ad]] ? F.pazar[C.ad] : "";
  function pazarSecimi() {
    const fp = $("f-pazar"); fp.textContent = ""; fp.append(new Option("Seçilmedi", ""));
    let og = null;
    C.PAZARLAR.forEach(p => { if (!og || og.label !== p[2]) { og = document.createElement("optgroup"); og.label = p[2]; fp.append(og); } og.append(new Option(p[1], p[0])); });
    fp.value = seciliPazar(); $("f-sira").value = F.sira; $("f-min").value = F.min;
  }
  const HIZLI = {
    g: [["tum", "Tümü"], ["bugun", "Bugün"], ["yarin", "Yarın"], ["3", "3 gün"], ["7", "7 gün"], ["ozel", "Özel aralık"]],
    p: [["7", "Son 7 gün"], ["dun", "Dün"], ["30", "Son 30 gün"], ["sezon", "Bu sezon"], ["ozel", "Özel aralık"]]
  };
  function hizliUygula(k) {
    let bas, bit;
    if (gorunum === "g") {
      const son = C.FIK.reduce((a, m) => Math.max(a, m.gun), bugun);
      if (k === "bugun") { bas = bit = bugun; } else if (k === "yarin") { bas = bit = bugun + 1; }
      else if (k === "3") { bas = bugun; bit = bugun + 2; } else if (k === "7") { bas = bugun; bit = bugun + 6; }
      else { bas = bugun; bit = Math.max(son, bugun); }
    } else {
      const son = C.SON_GUN || bugun - 1;
      if (k === "dun") { bas = bit = Math.min(bugun - 1, son); } else if (k === "30") { bas = son - 29; bit = son; }
      else if (k === "sezon") { bas = sezonBasi(son); bit = son; } else { bas = son - 6; bit = son; }
    }
    $("f-bas").value = iso(bas); $("f-bit").value = iso(bit);
  }
  function hizliDoldur() {
    const s = $("f-hizli"); s.textContent = "";
    HIZLI[gorunum === "h" ? "g" : gorunum].forEach(([v, t]) => s.append(new Option(t, v)));
    s.value = HIZLI[gorunum === "h" ? "g" : gorunum][0][0]; hizliUygula(s.value);
  }
  $("f-hizli").addEventListener("change", e => { if (e.target.value !== "ozel") { hizliUygula(e.target.value); listeHazirla(); } });
  ["f-bas", "f-bit"].forEach(id => $(id).addEventListener("change", () => { $("f-hizli").value = "ozel"; listeHazirla(); }));
  ["f-lig", "f-ara"].forEach(id => $(id).addEventListener("input", ciz));
  $("f-pazar").addEventListener("change", e => {
    F.pazar[C.ad] = e.target.value;
    if (!e.target.value) { if (F.sira === "ihtimal") { F.sira = "tarih"; $("f-sira").value = "tarih"; } F.min = ""; $("f-min").value = ""; }
    saklaYaz("bob-filtre3", F); ciz();
  });
  $("f-sira").addEventListener("change", e => { F.sira = e.target.value; saklaYaz("bob-filtre3", F); ciz(); });
  $("f-min").addEventListener("change", e => { F.min = e.target.value; saklaYaz("bob-filtre3", F); ciz(); });
  function sekmeIsaretle() { for (const k of ["g", "p", "h"]) $("tab-" + k).setAttribute("aria-selected", String(gorunum === k)); }
  function sekme(v) {
    gorunum = v; sekmeIsaretle();
    $("liste-alan").hidden = v === "h"; $("hesap-alan").hidden = v !== "h";
    if (v === "h") { hesapCiz(); return; }
    hizliDoldur(); listeHazirla();
  }
  $("tab-g").addEventListener("click", () => sekme("g"));
  $("tab-p").addEventListener("click", () => sekme("p"));
  $("tab-h").addEventListener("click", () => sekme("h"));
  function sporSec(ad, ilk) {
    C = SP[ad]; saklaYaz("bob-spor", ad);
    $("spor-futbol").setAttribute("aria-pressed", String(ad === "futbol")); $("spor-nba").setAttribute("aria-pressed", String(ad === "nba"));
    $("tab-h").hidden = ad === "nba";
    if (ad === "nba" && gorunum === "h") { gorunum = "g"; $("liste-alan").hidden = false; $("hesap-alan").hidden = true; }
    pazarSecimi(); metaCiz(); kalGrupDoldur();
    if (!ilk) { if (gorunum !== "h") gorunum = C.FIK.some(m => m.gun >= bugun) || !C.TUM.length ? "g" : "p"; sekmeIsaretle(); if (gorunum !== "h") { hizliDoldur(); listeHazirla(); } kalBaslat(); }
  }
  $("spor-futbol").addEventListener("click", () => sporSec("futbol"));
  $("spor-nba").addEventListener("click", () => sporSec("nba"));

  // ================================================================ liste
  let VIEW = [];
  function listeHazirla() {
    const bas = isoGun($("f-bas").value), bit = isoGun($("f-bit").value);
    const kaynak = gorunum === "g" ? C.FIK.filter(m => m.gun >= bugun) : C.TUM;
    VIEW = kaynak.filter(m => (bas == null || m.gun >= bas) && (bit == null || m.gun <= bit));
    $("n-g").textContent = C.FIK.filter(m => m.gun >= bugun).length || "";
    const fl = $("f-lig"), s = fl.value; fl.textContent = ""; fl.append(new Option(C.ad === "nba" ? "NBA" : "Tüm ligler", ""));
    if (C.ad !== "nba") [...new Set(VIEW.map(v => v.lig))].sort((a, b) => (LIGLER[a] || a).localeCompare(LIGLER[b] || b, "tr")).forEach(k => fl.append(new Option(LIGLER[k] || k, k)));
    fl.value = [...fl.options].some(o => o.value === s) ? s : "";
    const b = $("banner"), mesaj = [];
    if (!KAT) mesaj.push("Model katsayıları bulunamadı; ihtimaller hesaplanamıyor.");
    if (gorunum === "p") mesaj.push("Geçmiş maçlarda model, maçın oranlarından hesaplanır; kutular gerçek sonuca göre yeşil (tuttu) ya da kırmızı (tutmadı) olur.");
    if (C.ad === "nba" && C.TUM.length < 300) mesaj.push("NBA geçmişi birikiyor: şu an " + binlik(C.TUM.length) + " maç var. NBA modeli geçmiş maça ihtiyaç duymaz; sadece oranlardan hesaplanır, geçmiş yalnızca doğruluk kontrolü içindir.");
    b.hidden = !mesaj.length; b.textContent = mesaj.join(" ");
    ciz();
  }

  function oddBox(lbl, val, on, metin) { const b = el("div", "odd"); b.append(el("small", null, lbl), el("span", on ? "mk on" : null, metin != null ? metin : virgul(val))); return b; }
  function oranKutulari(f) {
    const od = el("div", "odds");
    if (f.lig === "NBA") {
      const fk = f.ms ? fark(f) : null;
      od.append(oddBox("Ev", f.o1, fk != null && fk > 0), oddBox("Dep", f.o2, fk != null && fk < 0),
        oddBox("Handikap", null, f.ms && f.hnd != null && fk + f.hnd > 0, f.hnd == null ? "–" : cizgi(f.hnd)),
        oddBox("Toplam", null, f.ms && f.tot != null && g(f) > f.tot, f.tot == null ? "–" : String(f.tot).replace(".", ",")));
      return od;
    }
    const s = f.ms ? sonucIdx(f) : -1;
    [["1", f.o1], ["X", f.ox], ["2", f.o2]].forEach(([l, o], i) => od.append(oddBox(l, o, i === s)));
    if (f.ou) { const gol = f.ms ? g(f) : null; od.append(oddBox("2,5 Ü", f.ou, gol != null && gol >= 3), oddBox("2,5 A", f.oa, gol != null && gol <= 2)); }
    return od;
  }
  function modelChipleri(f) {
    const ch = el("div", "chips");
    if (f.lig === "NBA") {
      const o = BOM.nbaOrtalamalar(f);
      const c1 = el("span", "chip model", "Fark " + (o.mu >= 0 ? "ev +" : "dep +") + ondalik(Math.abs(o.mu), 1)); c1.title = "Modelin beklediği sayı farkı";
      ch.append(c1);
      if (o.muT != null) { const c2 = el("span", "chip model", "Toplam ~" + ondalik(o.muT, 0)); c2.title = "Modelin beklediği toplam sayı"; ch.append(c2); }
      return ch;
    }
    const d = modelDegerleri(f, null);
    if (!d) { ch.append(el("span", "chip none", "Model yok")); return ch; }
    const c1 = el("span", "chip model", "Gol " + ondalik(d.lh, 2) + " – " + ondalik(d.la, 2)); c1.title = "Modelin beklediği gol (ev – deplasman)"; ch.append(c1);
    if (d.mc != null) { const c = el("span", "chip model", "Korner ~" + ondalik(d.mc, 1)); c.title = "Modelin beklediği toplam korner"; ch.append(c); }
    if (d.mk != null) { const c = el("span", "chip model", "Kart ~" + ondalik(d.mk, 1)); c.title = "Modelin beklediği toplam kart (sarı + kırmızı)"; ch.append(c); }
    return ch;
  }

  // ---------------------------------------------------------------- maç detayı: pazar tablosu
  // ozel: kullanıcının girdiği oranlar (futbol); oranlarim: pazar kodu -> yazılan oran (metin); sonuclu: gerçek sonuç sütunu
  function pazarTablosu(f, ozel, oranlarim) {
    const S = sporOf(f), sonuclu = !!f.ms;
    let P = {};
    if (f.lig === "NBA") P = BOM.nbaPazarlar(f);
    else { const d = modelDegerleri(f, ozel); if (d) P = Object.assign({}, BOM.temelPazarlar(d.lh, d.la, KAT, d.mc, d.mk), BOM.genisPazarlar(d.lh, d.la, KAT)); }
    const t = el("table", "pazar"), h = t.createTHead().insertRow();
    ["Pazar", "Model ihtimali", "Adil oran*", "Senin oranın", "Değer"].concat(sonuclu ? ["Sonuç"] : []).forEach((x, i) => h.append(el("th", i ? "n" : null, x)));
    const b = t.createTBody(); let grup = null;
    S.PAZARLAR.forEach(pz => {
      const p = P[pz[0]]; if (p == null) return;
      if (pz[2] !== grup) { grup = pz[2]; const r = b.insertRow(); r.className = "grp"; const c = r.insertCell(); c.colSpan = sonuclu ? 6 : 5; c.textContent = grup; }
      const r = b.insertRow(); r.dataset.ad = (pz[1] + " " + pz[0]).toLocaleLowerCase("tr");
      r.insertCell().textContent = pz[1];
      const add = (txt, cls) => { const c = r.insertCell(); c.className = "n" + (cls ? " " + cls : ""); c.textContent = txt; return c; };
      add(yuzde1(p)); add(adil(p), "est");
      const ci = r.insertCell(); ci.className = "n inp";
      const inp = el("input"); inp.type = "text"; inp.inputMode = "decimal"; inp.autocomplete = "off"; inp.placeholder = "oran"; inp.setAttribute("aria-label", pz[1] + " için kendi oranın");
      if (oranlarim && oranlarim[pz[0]]) inp.value = oranlarim[pz[0]];
      ci.append(inp);
      const cv = add("", "ev");
      const guncelle = () => {
        const o = oranOku(inp.value);
        if (oranlarim) oranlarim[pz[0]] = inp.value;
        if (o == null) { cv.textContent = ""; cv.className = "n ev"; return; }
        const ev = p * o - 1;
        cv.textContent = (ev >= 0 ? "+" : "−") + "%" + (Math.abs(ev) * 100).toFixed(1).replace(".", ",");
        cv.className = "n ev " + (ev > 0 ? "good" : "bad");
      };
      inp.addEventListener("input", guncelle); guncelle();
      if (sonuclu) { const s = sonucu(pz, f); add(s == null ? (f[pz[3]] == null ? "veri yok" : "iade") : s ? "Tuttu" : "Tutmadı", s == null ? "" : s ? "ok" : "no"); }
    });
    return t;
  }
  function tabloFiltre(t, q) {
    q = q.trim().toLocaleLowerCase("tr");
    let sonGrup = null, say = 0;
    const bitir = () => { if (sonGrup) sonGrup.hidden = say === 0; };
    for (const r of t.tBodies[0].rows) {
      if (r.classList.contains("grp")) { bitir(); sonGrup = r; say = 0; continue; }
      const goster = !q || r.dataset.ad.includes(q); r.hidden = !goster; if (goster) say++;
    }
    bitir();
  }
  function ozetSatiri(f, ozel) {
    const p = piyasaIhtimali(f), kaynak = OK_AD[f.ok] || "Bet365";
    if (f.lig === "NBA") {
      const o = BOM.nbaOrtalamalar(f);
      return "Piyasa ihtimali: Ev " + yuzde(p.p1) + " · Dep " + yuzde(p.p2) + (f.hnd != null ? " · Ev handikabı " + cizgi(f.hnd) : "") +
        (f.tot != null ? " · Toplam çizgisi " + String(f.tot).replace(".", ",") : "") + " · Model: beklenen fark ev " + cizgi(Math.round(o.mu * 10) / 10) +
        (o.muT != null ? ", toplam ~" + ondalik(o.muT, 1) : "") + " · Oranlar: " + kaynak;
    }
    const d = modelDegerleri(f, ozel);
    const q = ozel ? (() => { const x = BOM.margGuc([ozel.o1, ozel.ox, ozel.o2]); const u = ozel.ou && ozel.oa ? BOM.margGuc([ozel.ou, ozel.oa])[0] : null; return { p1: x[0], px: x[1], p2: x[2], pu: u }; })() : p;
    return (ozel ? "Senin oranlarından marjı çıkarılmış ihtimal: " : "Piyasa ihtimali (marjsız): ") + "1 " + yuzde(q.p1) + " · X " + yuzde(q.px) + " · 2 " + yuzde(q.p2) + (q.pu != null ? " · 2,5 Üst " + yuzde(q.pu) : "") +
      (d ? " · Model: beklenen gol " + ondalik(d.lh, 2) + " – " + ondalik(d.la, 2) + (d.mc != null ? " · korner ~" + ondalik(d.mc, 1) : "") + (d.mk != null ? " · kart ~" + ondalik(d.mk, 1) : "") : "") +
      (f.ms && (f.korner != null || f.kart != null) ? " · Gerçekleşen: korner " + (f.korner ?? "–") + " · kart " + (f.kart ?? "–") : "") + (ozel ? "" : " · Oranlar: " + kaynak);
  }
  function detayKur(f) {
    const detay = el("div", "detail"), nba = f.lig === "NBA";
    const durum = { ozel: null, oranlarim: {} };
    const ozet = el("div", "muted", ""); detay.append(ozet);
    if (f.gecici) detay.append(el("div", "muted", "Skor aynı gün football-data.org'dan alındı (geçici). Korner ve kart sayıları, football-data.co.uk sonuçları yayınlayınca eklenecek."));
    let kap = null, ara = null;
    const ciz = () => {
      ozet.textContent = ozetSatiri(f, durum.ozel);
      const yeni = el("div", "scroll"); yeni.append(pazarTablosu(f, durum.ozel, durum.oranlarim));
      if (kap) kap.replaceWith(yeni); else detay.append(yeni);
      kap = yeni; tabloFiltre(kap.firstChild, ara ? ara.value : "");
    };
    if (!nba) {
      const form = el("details", "ozel"), sm = el("summary", null, "Kendi oranlarımı gireyim"); form.append(sm);
      const govde = el("div", "form"); form.append(govde);
      const girdi = [["1", "o1", f.o1], ["X", "ox", f.ox], ["2", "o2", f.o2], ["2,5 Üst", "ou", f.ou], ["2,5 Alt", "oa", f.oa]];
      const alan = {};
      girdi.forEach(([ad, k, v]) => {
        const l = el("label", null, "MS " + ad.replace("MS ", "")); if (k === "ou" || k === "oa") l.firstChild.textContent = ad + " ";
        const i = el("input"); i.type = "text"; i.inputMode = "decimal"; i.autocomplete = "off"; i.placeholder = v ? virgul(v) : "oran"; alan[k] = i; l.append(i); govde.append(l);
      });
      const not = el("p", "muted ozel-not", "Bahis şirketinin 1-X-2 (ve varsa 2,5 Alt/Üst) oranlarını yaz; model tüm pazarları bu oranlara göre yeniden hesaplar. Boş bırakılan oranlar yerine maçın kendi oranları kullanılır.");
      const sifirla = el("button", "btn ikincil", "Sıfırla"); sifirla.type = "button";
      form.append(not, sifirla); detay.append(form);
      const degis = () => {
        const v = k => oranOku(alan[k].value);
        const o = { o1: v("o1") || f.o1, ox: v("ox") || f.ox, o2: v("o2") || f.o2, ou: v("ou") || f.ou, oa: v("oa") || f.oa };
        const degisti = ["o1", "ox", "o2", "ou", "oa"].some(k => v(k));
        durum.ozel = degisti ? o : null; ciz();
      };
      Object.values(alan).forEach(i => i.addEventListener("input", degis));
      sifirla.addEventListener("click", () => { Object.values(alan).forEach(i => { i.value = ""; }); degis(); });
    }
    const arama = el("div", "tablo-ara");
    ara = el("input"); ara.type = "search"; ara.placeholder = "Pazar ara (ör. KG, korner, handikap, 2,5)"; ara.setAttribute("aria-label", "Pazar ara");
    ara.addEventListener("input", () => kap && tabloFiltre(kap.firstChild, ara.value)); arama.append(ara); detay.append(arama);
    ciz();
    const lg = el("div", "legend");
    lg.append(el("span", null, "Oranlar: " + (nba ? "The Odds API (bahis şirketleri ortalaması)" : OK_AD[f.ok] || "Bet365") + ". Bunlar İddaa oranı değildir."));
    const e = el("span"); e.append(el("span", "e", "Adil oran*"), " = modelin ihtimalinin tersi (1 ÷ ihtimal); bahis oranı değildir"); lg.append(e);
    lg.append(el("span", null, "Değer = ihtimal × senin oranın − 1. Artıysa senin oranın modelin adil oranından yüksektir."));
    detay.append(lg);
    return detay;
  }

  function fxSatir(f, tarihli) {
    const S = sporOf(f), box = el("div", "fx");
    const btn = el("button"); btn.type = "button"; btn.setAttribute("aria-expanded", "false");
    const tm = el("span", "time", f.saat || "–"); if (tarihli) tm.append(el("small", null, kisaTarih(f.gun)));
    btn.append(tm, el("span", "lg", f.lig));
    const tt = el("span", "teams", f.ev + " – " + f.dep);
    if (f.ms) tt.append(el("span", "res", f.ms.join("-") + (f.iy ? " (İY " + f.iy.join("-") + ")" : "")));
    if (f.gecici) tt.append(el("span", "gec", "geçici"));
    btn.append(tt, oranKutulari(f));
    const sp = seciliPazar();
    if (sp) {
      const pz = S.PAZARLAR[S.PZ[sp].i], p = ihtimal(f, sp);
      let cls = "pick"; if (f.ms) { const r = sonucu(pz, f); if (r != null) cls += r ? " hit" : " miss"; }
      const pk = el("span", cls);
      pk.append(el("span", null, pz[1]));
      const b = el("b"); b.append(yuzde1(p) + " · ", el("span", "e", "adil " + adil(p) + "*")); pk.append(b);
      btn.append(pk);
    } else btn.append(el("span", "pick-bos"));
    btn.append(modelChipleri(f), el("span", "caret", "›"));
    box.append(btn);
    let detay = null;
    btn.addEventListener("click", () => {
      const acik = box.classList.toggle("open"); btn.setAttribute("aria-expanded", String(acik));
      if (acik && !detay) { detay = detayKur(f); box.append(detay); }
      if (detay) detay.hidden = !acik;
    });
    return box;
  }

  function bosMesaj() {
    if (C.ad === "nba") {
      if (!ODDS_API || !ODDS_API.aktif) return "NBA maçları için The Odds API anahtarı gerekiyor. Anahtar eklenince maçlar ve oranlar her gün alınır.";
      if (gorunum === "g") return "Önümüzdeki 48 saatte oranı alınmış NBA maçı yok. Oranlar günde bir kez alınır.";
      return C.TUM.length ? "Seçili tarih aralığında maç yok." : "Henüz sonucu kaydedilmiş NBA maçı yok. Oynanan maçlar her gün eklenecek.";
    }
    if (gorunum === "g") return C.FIK.some(m => m.gun >= bugun) ? "Seçili tarih aralığında oranı açıklanmış maç yok." :
      "Şu an oranı açıklanmış gelecek maç yok. football-data.co.uk hafta sonu maçlarını Cuma, hafta içi maçlarını Salı öğleden sonra yayınlıyor; kupalar ve ek ligler The Odds API'den günde bir kez gelir.";
    return "Seçili tarih aralığında maç yok.";
  }
  function ciz() {
    const lig = $("f-lig").value, ara = $("f-ara").value.trim().toLocaleLowerCase("tr");
    let liste = VIEW.filter(f => (!lig || f.lig === lig) && (!ara || (f.ev + " " + f.dep).toLocaleLowerCase("tr").includes(ara)));
    const sp = seciliPazar(), ihtimalSira = F.sira === "ihtimal" && sp, min = sp && F.min ? Number(F.min) : 0;
    if (sp && (ihtimalSira || min)) {
      liste = liste.map(f => ({ f, p: ihtimal(f, sp) })).filter(x => x.p != null && x.p >= min);
      if (ihtimalSira) liste.sort((a, b) => b.p - a.p);
      liste = liste.map(x => x.f);
    }
    if (!ihtimalSira) liste = liste.slice().sort((a, b) => b.gun === a.gun ? a.saat.localeCompare(b.saat) || a.lig.localeCompare(b.lig) : (gorunum === "p" ? b.gun - a.gun : a.gun - b.gun));
    const kap = $("fixtures"); kap.textContent = "";
    $("f-count").textContent = binlik(liste.length) + " / " + binlik(VIEW.length) + " maç";
    if (!VIEW.length) { kap.append(el("div", "empty", bosMesaj())); return; }
    if (!liste.length) { kap.append(el("div", "empty", "Bu filtreyle maç yok.")); return; }
    const MAX = 400; const gos = liste.slice(0, MAX);
    if (ihtimalSira) { const l = el("div", "list"); gos.forEach(f => l.append(fxSatir(f, true))); kap.append(l); }
    else {
      let gun = null, lst = null;
      gos.forEach(f => {
        if (f.gun !== gun) { gun = f.gun; const d = el("div", "day"); d.append(el("h3", null, uzunTarih(gun))); lst = el("div", "list"); d.append(lst); kap.append(d); }
        lst.append(fxSatir(f, false));
      });
    }
    if (liste.length > MAX) kap.append(el("div", "empty", "İlk " + MAX + " maç gösteriliyor. Tarih aralığını daraltın ya da lig seçin."));
  }

  // ================================================================ hesaplayıcı
  const hesapDurum = { oranlarim: {} };
  function hesapCiz() {
    const kap = $("hes-sonuc"); kap.textContent = "";
    const v = id => oranOku($(id).value);
    const o1 = v("h-1"), ox = v("h-x"), o2 = v("h-2"), ou = v("h-u"), oa = v("h-a");
    if (!KAT) { kap.append(el("div", "empty", "Model katsayıları yüklenemedi.")); return; }
    if (!(o1 && ox && o2)) { kap.append(el("div", "empty", "MS 1, X ve 2 oranlarını yaz (1'den büyük sayılar). Örnek: 1,85 · 3,60 · 4,20")); return; }
    const iki = ou && oa;
    const f = { lig: "HES", ev: "Ev sahibi", dep: "Deplasman", gun: bugun, saat: "", o1, ox, o2, ou: iki ? ou : null, oa: iki ? oa : null, ms: null, iy: null, korner: null, kart: null, ok: 0, oz: null, lh: null, la: null, mc: null, mk: null };
    const ozel = { o1, ox, o2, ou: f.ou, oa: f.oa };
    const ozet = el("div", "muted", ozetSatiri(f, ozel)); ozet.textContent = ozet.textContent.replace(" · Model:", " · Model:") ;
    kap.append(ozet);
    if (!iki) kap.append(el("div", "muted", "2,5 Alt/Üst oranları yazılmadığı için toplam gol seviyesi tahmin edildi; yazarsan sonuçlar daha doğru olur."));
    const ara = el("div", "tablo-ara"), ai = el("input"); ai.type = "search"; ai.placeholder = "Pazar ara (ör. KG, handikap, 2,5)"; ai.setAttribute("aria-label", "Pazar ara"); ara.append(ai); kap.append(ara);
    const sc = el("div", "scroll"); sc.append(pazarTablosu(f, ozel, hesapDurum.oranlarim)); kap.append(sc);
    ai.addEventListener("input", () => tabloFiltre(sc.firstChild, ai.value));
    kap.append(el("div", "muted", "Hesaplayıcıda korner ve kart yoktur (takım bilgisi gerekir). Bu pazarlar için maç listesinden maçı aç."));
  }
  ["h-1", "h-x", "h-2", "h-u", "h-a"].forEach(id => $(id).addEventListener("input", () => { hesapDurum.oranlarim = {}; hesapCiz(); }));

  // ================================================================ geçmişte nasıl çalıştı
  // Araştırma sonuçları (python: arastirma/degerlendir3.py). Log kayıp: küçük = iyi.
  const ARASTIRMA = {
    gruplar: [["Maç sonucu", 6, 0.6252, 0.5989, 0.5846], ["Toplam gol", 8, 0.5604, 0.5601, 0.5491], ["Karşılıklı gol", 2, 0.6904, 0.6945, 0.6862],
      ["Takım golü", 10, 0.5828, 0.5640, 0.5524], ["İlk yarı", 8, 0.6089, 0.6073, 0.5976], ["İkinci yarı", 2, 0.6029, 0.6068, 0.5975],
      ["Korner", 8, 0.6515, 0.6564, 0.6465], ["Kart", 7, 0.6156, 0.6177, 0.6066]],
    toplam: [51, 0.6087, 0.6029, 0.5920]
  };
  function arastirmaCiz() {
    const k = $("arastirma"); k.textContent = "";
    k.append(el("p", "lead", "Geriye dönük test: Temmuz 2024 – Eylül 2026 arasında oynanan 15.406 maç (22 Avrupa ligi). Model her test döneminde yalnızca o tarihten ÖNCEKİ veriyle (Temmuz 2023'ten itibaren) eğitildi; her maç yalnızca kendi oranlarıyla tahmin edildi. " +
      "Aşağıdaki sayılar ortalama log kayıptır (küçük = tahminler gerçeğe daha yakın). Karşılaştırma: lig ortalamasını her maça aynen veren basit tahmin ve sayfanın eski \"benzer oranlı maç\" yöntemi."));
    const sc = el("div", "bt-wrap scroll"), t = el("table"); sc.append(t); k.append(sc);
    const h = t.createTHead().insertRow(); ["Pazar grubu", "Pazar", "Lig ortalaması", "Eski yöntem", "Yeni model"].forEach((x, i) => h.append(el("th", i ? "n" : null, x)));
    const b = t.createTBody();
    ARASTIRMA.gruplar.concat([["Hepsi"].concat(ARASTIRMA.toplam)]).forEach(r => {
      const tr = b.insertRow(); if (r[0] === "Hepsi") tr.className = "toplam";
      tr.insertCell().textContent = r[0];
      const en = Math.min(r[2], r[3], r[4]);
      [String(r[1]), ...[r[2], r[3], r[4]].map(x => x.toFixed(4).replace(".", ","))].forEach((x, i) => { const c = tr.insertCell(); c.className = "n" + (i && Number(String(x).replace(",", ".")) === en ? " good" : ""); c.textContent = x; });
    });
    const ul = el("ul", "bulgu");
    [
      "Yeni model 51 pazarın 51'inde hem eski yöntemden hem de lig ortalamasından daha doğru çıktı. Eski yöntem 51 pazarın yalnızca 20'sinde lig ortalamasını geçebildi.",
      "Eski yöntemin \"sinyal\" verdiği 25.586 maç-pazar çiftinin %78,2'si tuttu; eski yöntem %80,5 bekliyordu. Yeni modelin aynı çiftler için ortalama ihtimali %77,5: yani sinyaller, oranların zaten söylediğinin üstüne yalnızca 0,7 puanlık bir şey ekliyor; eski yöntemin vaat ettiği kadar değil.",
      "Para tarafı: MS ve 2,5 Alt/Üst pazarlarındaki sinyalli bahislere (Bet365 oranıyla, 581 bahis) 1 birim oynansaydı toplam getiri −%5,2 (±6,2) olurdu. Test döneminde tüm maçlara düz oynanan MS 1 −%7,8, MS X −%5,3, MS 2 −%11,4, 2,5 Üst −%4,1, 2,5 Alt −%7,2 getirdi (en yüksek oran seçilse bile −%1 ile −%7).",
      "Birleşik ve ek pazarlarda (62 pazar: handikap, İY/MS, MS + Alt/Üst, KG + Alt/Üst, toplam gol aralığı) modelin ihtimali ile gerçekleşen oran arasındaki ortalama fark 0,5 puan, en büyük fark 1,5 puan (handikap pazarları) çıktı. Tek/çift için model bilgi eklemediğinden %50 gösterilir."
    ].forEach(x => ul.append(el("li", null, x)));
    k.append(ul);
  }

  // ---------------------------------------------------------------- canlı kontrol (sayfadaki geçmiş maçlarla)
  const KAL_TEMEL = () => C.ad === "futbol" ? C.PAZARLAR.slice(0, PAZ.TEMEL_SAYI) : C.PAZARLAR;
  const kalGrupAdi = a => a === "Ev sahibi golü" || a === "Deplasman golü" ? "Takım golü" : a;
  function kalGrupDoldur() {
    const s = $("k-grup"), onceki = s.value; s.textContent = "";
    s.append(new Option("Hepsi", "tum"));
    [...new Set(KAL_TEMEL().map(p => kalGrupAdi(p[2])))].forEach(a => s.append(new Option(a, a)));
    s.value = [...s.options].some(o => o.value === onceki) ? onceki : "tum";
  }
  let kalNo = 0;
  function kalBaslat() {
    const no = ++kalNo, S = C, tab = $("kal-table"); tab.textContent = "";
    $("kal-lead").textContent = "Hesaplanıyor…";
    setTimeout(async () => {
      if (no !== kalNo) return;
      const grup = $("k-grup").value, donem = $("k-donem").value;
      const bas = donem === "12ay" ? bugun - 365 : -Infinity;
      const secili = KAL_TEMEL().filter(p => grup === "tum" || kalGrupAdi(p[2]) === grup);
      const maclar = S.TUM.filter(m => m.gun >= bas && m.ms && (S.ad === "nba" || m.lh != null) && KAT);
      if (!maclar.length) { $("kal-lead").textContent = "Bu dönemde kontrol edilecek geçmiş maç yok."; return; }
      const kutu = Array.from({ length: 10 }, () => ({ n: 0, p: 0, y: 0 }));
      for (let j = 0; j < maclar.length; j++) {
        if (j % 300 === 0) { await bekle(); if (no !== kalNo) return; $("kal-lead").textContent = "Hesaplanıyor… %" + Math.round(j / maclar.length * 100); }
        const m = maclar[j];
        const P = S.ad === "nba" ? BOM.nbaPazarlar(m) : BOM.temelPazarlar(m.lh, m.la, KAT, m.mc, m.mk);
        for (const pz of secili) {
          const r = sonucu(pz, m), p = P[pz[0]]; if (r == null || p == null) continue;
          const k = kutu[Math.min(9, Math.floor(p * 10))]; k.n++; k.p += p; if (r) k.y++;
        }
      }
      if (no !== kalNo) return;
      kalCiz(kutu, maclar.length, donem);
    }, 40);
  }
  function kalCiz(kutu, nMac, donem) {
    const tab = $("kal-table"); tab.textContent = "";
    const top = kutu.reduce((a, k) => (a.n += k.n, a.p += k.p, a.y += k.y, a), { n: 0, p: 0, y: 0 });
    if (!top.n) { $("kal-lead").textContent = "Bu seçim için sonuçlanmış pazar yok."; return; }
    let sapma = 0; kutu.forEach(k => { if (k.n) sapma += Math.abs(k.y / k.n - k.p / k.n) * k.n; });
    $("kal-lead").textContent = (donem === "12ay" ? "Son 12 ayda" : "Sayfadaki tüm geçmişte (" + kisaTarih(C.ILK_GUN) + " sonrası)") + " oynanan " + binlik(nMac) + " maçta, modelin her pazar için maçtan önce verdiği ihtimaller gruplandı. Model ortalaması %" +
      ondalik(top.p / top.n * 100, 1) + ", gerçekleşen %" + ondalik(top.y / top.n * 100, 1) + "; ağırlıklı ortalama sapma " + ondalik(sapma / top.n * 100, 1) + " puan. İdeal durumda her satırda iki yüzde birbirine eşittir." +
      (C.ad === "futbol" ? " (Korner ve kart modelinin katsayıları da bu verilerle eğitildiği için o gruplarda sonuç biraz iyimser olabilir.)" : "");
    const h = tab.createTHead().insertRow(); ["Modelin ihtimali", "Pazar sayısı", "Model ortalaması", "Gerçekleşen", "Fark"].forEach((x, i) => h.append(el("th", i ? "n" : null, x)));
    const b = tab.createTBody();
    kutu.forEach((k, i) => {
      if (!k.n) return;
      const tr = b.insertRow(); tr.insertCell().textContent = "%" + i * 10 + " – %" + (i + 1) * 10;
      const fk = (k.y - k.p) / k.n * 100, se = Math.sqrt(Math.max(k.p / k.n * (1 - k.p / k.n), 1e-9) / k.n) * 100;
      [binlik(k.n), yuzde1(k.p / k.n), yuzde1(k.y / k.n), (fk >= 0 ? "+" : "−") + ondalik(Math.abs(fk), 1) + " puan"].forEach((x, j) => {
        const c = tr.insertCell(); c.className = "n" + (j === 3 ? (Math.abs(fk) > 2.5 * se && Math.abs(fk) > 1 ? " bad" : "") : ""); c.textContent = x;
      });
    });
  }
  $("k-grup").addEventListener("change", kalBaslat);
  $("k-donem").addEventListener("change", kalBaslat);

  // ================================================================ üst bilgi + güncelleme
  function metaCiz() {
    const meta = $("meta"); meta.textContent = "";
    const fs = C.FIK.filter(m => m.gun >= bugun).length;
    const kaynak = C.ad === "nba" ? "The Odds API" : "football-data.co.uk" + (ODDS_API && ODDS_API.aktif ? " + The Odds API" : "");
    const satir = [["Kaynak", kaynak], ["Geçmiş", binlik(C.TUM.length) + " maç"], ["Aralık", C.TUM.length ? kisaTarih(C.ILK_GUN) + " – " + kisaTarih(C.SON_GUN) : "–"], ["Gelecek", fs + " maç"],
      ["Model", C.ad === "nba" ? "normal dağılım (oranlardan)" : "Poisson / Dixon-Coles (oranlardan)"]];
    if (C.GECICI_SAY) satir.push(["Geçici sonuç", C.GECICI_SAY + " maç"]);
    if (ODDS_API && ODDS_API.aktif && ODDS_API.kalan != null) satir.push(["The Odds API kalan kredi", String(ODDS_API.kalan)]);
    if (ODDS_API && ODDS_API.hata) satir.push(["The Odds API", "hata: " + ODDS_API.hata]);
    satir.forEach(([k, v]) => { const s = el("span"); s.append(k + ": ", el("b", null, v)); meta.append(s); });
    $("upd-durum").textContent = OLUSTURMA ? "Veri: " + new Date(OLUSTURMA).toLocaleString("tr-TR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "";
  }
  const gomulu = document.getElementById("gomulu-veri");
  async function guncelle(ilk) {
    const btn = $("guncelle"); btn.disabled = true; $("upd-durum").textContent = "Güncelleniyor…";
    try {
      let V;
      if (ilk && gomulu) V = JSON.parse(gomulu.textContent);
      else {
        const r = await fetch("veri.json?t=" + Date.now(), { cache: "no-store" });
        if (!r.ok) throw new Error("HTTP " + r.status);
        V = await r.json();
      }
      veriAc(V);
      if (ilk) { sporSec(C.ad, true); gorunum = C.FIK.some(m => m.gun >= bugun) || !C.TUM.length ? "g" : "p"; sekmeIsaretle(); hizliDoldur(); }
      else { metaCiz(); if ($("f-hizli").value !== "ozel") hizliUygula($("f-hizli").value); }
      if (gorunum === "h") hesapCiz(); else listeHazirla();
      kalBaslat();
      if (!ilk) $("upd-durum").textContent += " · güncellendi";
    } catch (e) {
      metaCiz();
      $("upd-durum").textContent = gomulu
        ? "Bu önizlemede güncelleme yok; GitHub sayfanızda Güncelle tuşu son veriyi getirir."
        : "Güncellenemedi (" + (e && e.message || e) + "). İnternet bağlantınızı kontrol edin.";
      if (!C.TUM.length) ciz();
    } finally { btn.disabled = false; }
  }
  $("guncelle").addEventListener("click", () => guncelle(false));

  [
    "Adil oran*: Modelin hesapladığı ihtimalin tersidir (1 ÷ ihtimal). Hiçbir bahis şirketinin oranı değildir. Bahis şirketlerinin oranları marj içerir; kendi oranını yazdığın pazarda \"değer\" artıysa o oran, modelin adil oranından yüksektir. Değer sütunu modelin doğruluğuna bağlıdır; model de en iyi ihtimalle piyasanın kendi bilgisi kadar doğrudur.",
    "Model: marjı çıkarılmış 1X2 ve 2,5 Alt/Üst ihtimallerine uyan beklenen ev ve deplasman golü bulunur; skorlar Poisson dağılımı, düşük skorlar için Dixon-Coles düzeltmesi ve 2+ farklı skorlar için hafif bir ağırlıkla modellenir. İlk yarı için gollerin yaklaşık %44,5'inin ilk yarıda atıldığı varsayılır. Korner ve kart: negatif binom dağılımı; takımların son 20 maçtaki attığı/yediği korner ve kart sayıları, ligin son 400 maçtaki seviyesi ve beklenen gol kullanılır. Katsayılar 1 Temmuz 2023'ten sonraki verilerle eğitilmiştir.",
    "Gerçek oranlar: ana Avrupa liglerinde Bet365 (football-data.co.uk); MLS ve İskandinav liglerinin geçmişinde kapanış oranları; kupalarda, NBA'de ve ek liglerin gelecek maçlarında bahis şirketlerinin ortalaması (The Odds API). Saatler Türkiye saatidir. Kart: sarı + kırmızı kart sayısı; İddaa'nın kart kuralları farklı olabilir. Korner, kart ve ilk yarı verisi her ligde yok (MLS, İskandinav ligleri ve kupalarda korner/kart modeli yok).",
    "NBA: maç sonucu ihtimali oranlardan, toplam sayı çizgiden hesaplanır; fark ve takım sayıları normal dağılımla modellenir (fark için standart sapma 13, toplam için 18 sayı). Çizgiye tam eşit sonuç iade sayılır ve \"iade hariç\" ihtimal gösterilir.",
    "Bu sayfa istatistiksel bir araçtır, bahis tavsiyesi değildir. Eski sürüm: v1.html"
  ].forEach(t => $("foot").append(el("p", null, t)));

  $("tab-h").hidden = C.ad === "nba";
  pazarSecimi(); hizliDoldur(); arastirmaCiz(); kalGrupDoldur();
  guncelle(true);
})();
