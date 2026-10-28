// ============================================================================ pazarlar.js
// Pazar tanımları: [kod, etiket, grup, gereken alan, sonuç testi]. Sonuç testi geçmiş maçın tuttu / tutmadı bilgisini verir.
// Gereken alan: "ms" (maç skoru), "iy" (ilk yarı skoru), "korner", "kart", "hnd", "tot", "evT", "depT" (NBA).
const PAZ = (function () {
  "use strict";
  const g = m => m.ms[0] + m.ms[1];
  const iyT = m => m.iy[0] + m.iy[1];
  const s1 = m => m.ms[0] > m.ms[1], sX = m => m.ms[0] === m.ms[1], s2 = m => m.ms[0] < m.ms[1];
  const S = { "1": s1, "X": sX, "2": s2 };
  const U25 = m => g(m) >= 3, A25 = m => g(m) <= 2, KGV = m => m.ms[0] > 0 && m.ms[1] > 0, KGY = m => m.ms[0] === 0 || m.ms[1] === 0;
  const TEMEL = [
    ["MS1", "MS 1", "Maç sonucu", "ms", s1], ["MSX", "MS X", "Maç sonucu", "ms", sX], ["MS2", "MS 2", "Maç sonucu", "ms", s2],
    ["CS1X", "Çifte şans 1X", "Maç sonucu", "ms", m => m.ms[0] >= m.ms[1]], ["CSX2", "Çifte şans X2", "Maç sonucu", "ms", m => m.ms[0] <= m.ms[1]],
    ["CS12", "Çifte şans 12", "Maç sonucu", "ms", m => m.ms[0] !== m.ms[1]],
    ["U15", "1,5 Üst", "Toplam gol", "ms", m => g(m) >= 2], ["A15", "1,5 Alt", "Toplam gol", "ms", m => g(m) <= 1],
    ["U25", "2,5 Üst", "Toplam gol", "ms", U25], ["A25", "2,5 Alt", "Toplam gol", "ms", A25],
    ["U35", "3,5 Üst", "Toplam gol", "ms", m => g(m) >= 4], ["A35", "3,5 Alt", "Toplam gol", "ms", m => g(m) <= 3],
    ["U45", "4,5 Üst", "Toplam gol", "ms", m => g(m) >= 5], ["A45", "4,5 Alt", "Toplam gol", "ms", m => g(m) <= 4],
    ["KGV", "KG Var", "Karşılıklı gol", "ms", KGV], ["KGY", "KG Yok", "Karşılıklı gol", "ms", KGY],
    ["EV05U", "Ev 0,5 Üst", "Ev sahibi golü", "ms", m => m.ms[0] >= 1], ["EV05A", "Ev 0,5 Alt", "Ev sahibi golü", "ms", m => m.ms[0] === 0],
    ["EV15U", "Ev 1,5 Üst", "Ev sahibi golü", "ms", m => m.ms[0] >= 2], ["EV15A", "Ev 1,5 Alt", "Ev sahibi golü", "ms", m => m.ms[0] <= 1],
    ["EV25U", "Ev 2,5 Üst", "Ev sahibi golü", "ms", m => m.ms[0] >= 3],
    ["DEP05U", "Dep 0,5 Üst", "Deplasman golü", "ms", m => m.ms[1] >= 1], ["DEP05A", "Dep 0,5 Alt", "Deplasman golü", "ms", m => m.ms[1] === 0],
    ["DEP15U", "Dep 1,5 Üst", "Deplasman golü", "ms", m => m.ms[1] >= 2], ["DEP15A", "Dep 1,5 Alt", "Deplasman golü", "ms", m => m.ms[1] <= 1],
    ["DEP25U", "Dep 2,5 Üst", "Deplasman golü", "ms", m => m.ms[1] >= 3],
    ["IY1", "İY 1", "İlk yarı", "iy", m => m.iy[0] > m.iy[1]], ["IYX", "İY X", "İlk yarı", "iy", m => m.iy[0] === m.iy[1]],
    ["IY2", "İY 2", "İlk yarı", "iy", m => m.iy[0] < m.iy[1]],
    ["IY05U", "İY 0,5 Üst", "İlk yarı", "iy", m => iyT(m) >= 1], ["IY05A", "İY 0,5 Alt", "İlk yarı", "iy", m => iyT(m) === 0],
    ["IY15U", "İY 1,5 Üst", "İlk yarı", "iy", m => iyT(m) >= 2], ["IY15A", "İY 1,5 Alt", "İlk yarı", "iy", m => iyT(m) <= 1],
    ["IYKGV", "İY KG Var", "İlk yarı", "iy", m => m.iy[0] > 0 && m.iy[1] > 0],
    ["IY2Y05U", "2. yarı 0,5 Üst", "İkinci yarı", "iy", m => g(m) - iyT(m) >= 1], ["IY2Y15U", "2. yarı 1,5 Üst", "İkinci yarı", "iy", m => g(m) - iyT(m) >= 2],
    ["K75U", "Korner 7,5 Üst", "Korner", "korner", m => m.korner >= 8], ["K85U", "Korner 8,5 Üst", "Korner", "korner", m => m.korner >= 9],
    ["K85A", "Korner 8,5 Alt", "Korner", "korner", m => m.korner <= 8], ["K95U", "Korner 9,5 Üst", "Korner", "korner", m => m.korner >= 10],
    ["K95A", "Korner 9,5 Alt", "Korner", "korner", m => m.korner <= 9], ["K105U", "Korner 10,5 Üst", "Korner", "korner", m => m.korner >= 11],
    ["K105A", "Korner 10,5 Alt", "Korner", "korner", m => m.korner <= 10], ["K115A", "Korner 11,5 Alt", "Korner", "korner", m => m.korner <= 11],
    ["C25U", "Kart 2,5 Üst", "Kart", "kart", m => m.kart >= 3], ["C35U", "Kart 3,5 Üst", "Kart", "kart", m => m.kart >= 4],
    ["C35A", "Kart 3,5 Alt", "Kart", "kart", m => m.kart <= 3], ["C45U", "Kart 4,5 Üst", "Kart", "kart", m => m.kart >= 5],
    ["C45A", "Kart 4,5 Alt", "Kart", "kart", m => m.kart <= 4], ["C55U", "Kart 5,5 Üst", "Kart", "kart", m => m.kart >= 6],
    ["C55A", "Kart 5,5 Alt", "Kart", "kart", m => m.kart <= 5]
  ];
  // ---- genişletilmiş (birleşik) pazarlar
  const GENIS = [];
  const ekle = (kod, etiket, grup, alan, test) => GENIS.push([kod, etiket, grup, alan, test]);
  for (const s of ["1", "X", "2"]) { const e = "MS " + s;
    ekle("MS" + s + "_U25", e + " & 2,5 Üst", "Maç sonucu + 2,5 Alt/Üst", "ms", m => S[s](m) && U25(m)); ekle("MS" + s + "_A25", e + " & 2,5 Alt", "Maç sonucu + 2,5 Alt/Üst", "ms", m => S[s](m) && A25(m)); }
  for (const s of ["1", "X", "2"]) { const e = "MS " + s;
    ekle("MS" + s + "_KGV", e + " & KG Var", "Maç sonucu + KG", "ms", m => S[s](m) && KGV(m)); ekle("MS" + s + "_KGY", e + " & KG Yok", "Maç sonucu + KG", "ms", m => S[s](m) && KGY(m)); }
  const CS = { "1X": m => m.ms[0] >= m.ms[1], "X2": m => m.ms[0] <= m.ms[1], "12": m => m.ms[0] !== m.ms[1] };
  for (const c of ["1X", "X2", "12"]) {
    ekle(c + "_U25", c + " & 2,5 Üst", "Çifte şans + 2,5 Alt/Üst", "ms", m => CS[c](m) && U25(m)); ekle(c + "_A25", c + " & 2,5 Alt", "Çifte şans + 2,5 Alt/Üst", "ms", m => CS[c](m) && A25(m)); }
  ekle("KGV_U25", "KG Var & 2,5 Üst", "KG + 2,5 Alt/Üst", "ms", m => KGV(m) && U25(m)); ekle("KGV_A25", "KG Var & 2,5 Alt", "KG + 2,5 Alt/Üst", "ms", m => KGV(m) && A25(m));
  ekle("KGY_U25", "KG Yok & 2,5 Üst", "KG + 2,5 Alt/Üst", "ms", m => KGY(m) && U25(m)); ekle("KGY_A25", "KG Yok & 2,5 Alt", "KG + 2,5 Alt/Üst", "ms", m => KGY(m) && A25(m));
  ekle("TG01", "0-1 gol", "Toplam gol aralığı", "ms", m => g(m) <= 1); ekle("TG23", "2-3 gol", "Toplam gol aralığı", "ms", m => g(m) >= 2 && g(m) <= 3);
  ekle("TG46", "4-6 gol", "Toplam gol aralığı", "ms", m => g(m) >= 4 && g(m) <= 6); ekle("TG7P", "7+ gol", "Toplam gol aralığı", "ms", m => g(m) >= 7);
  ekle("A05", "0,5 Alt", "Ek toplam gol çizgileri", "ms", m => g(m) === 0); ekle("U05", "0,5 Üst", "Ek toplam gol çizgileri", "ms", m => g(m) >= 1);
  ekle("A55", "5,5 Alt", "Ek toplam gol çizgileri", "ms", m => g(m) <= 5); ekle("U55", "5,5 Üst", "Ek toplam gol çizgileri", "ms", m => g(m) >= 6);
  ekle("TEK", "Toplam tek", "Tek / çift", "ms", m => g(m) % 2 === 1); ekle("CIFT", "Toplam çift", "Tek / çift", "ms", m => g(m) % 2 === 0);
  for (const hn of [-2, -1, 1, 2]) {
    const kod = "HND" + (hn < 0 ? "m" : "p") + Math.abs(hn), et = "(" + (hn > 0 ? "+" : "") + hn + ") ", fk = m => m.ms[0] + hn - m.ms[1];
    ekle(kod + "_1", et + "1", "Handikaplı maç sonucu (ev sahibine eklenen gol)", "ms", m => fk(m) > 0);
    ekle(kod + "_X", et + "X", "Handikaplı maç sonucu (ev sahibine eklenen gol)", "ms", m => fk(m) === 0);
    ekle(kod + "_2", et + "2", "Handikaplı maç sonucu (ev sahibine eklenen gol)", "ms", m => fk(m) < 0);
  }
  const ik = m => m.iy[0] - m.iy[1], h2 = m => (m.ms[0] - m.iy[0]) - (m.ms[1] - m.iy[1]), sg = x => x > 0 ? "1" : x < 0 ? "2" : "X";
  ekle("Y2_1", "2. yarı 1", "İkinci yarı sonucu", "iy", m => h2(m) > 0); ekle("Y2_X", "2. yarı X", "İkinci yarı sonucu", "iy", m => h2(m) === 0);
  ekle("Y2_2", "2. yarı 2", "İkinci yarı sonucu", "iy", m => h2(m) < 0);
  ekle("IY1X", "İY 1X", "İlk yarı çifte şans", "iy", m => ik(m) >= 0); ekle("IYX2", "İY X2", "İlk yarı çifte şans", "iy", m => ik(m) <= 0);
  ekle("IY12", "İY 12", "İlk yarı çifte şans", "iy", m => ik(m) !== 0);
  for (const a of ["1", "X", "2"]) for (const b of ["1", "X", "2"])
    ekle("IYMS_" + a + b, "İY " + a + " / MS " + b, "İlk yarı / maç sonucu", "iy", m => sg(ik(m)) === a && sg(m.ms[0] - m.ms[1]) === b);
  const ty = m => [iyT(m), g(m) - iyT(m)];
  ekle("YARI_1", "1. yarıda daha çok gol", "Hangi yarıda daha çok gol", "iy", m => { const t = ty(m); return t[0] > t[1]; });
  ekle("YARI_E", "İki yarıda eşit gol", "Hangi yarıda daha çok gol", "iy", m => { const t = ty(m); return t[0] === t[1]; });
  ekle("YARI_2", "2. yarıda daha çok gol", "Hangi yarıda daha çok gol", "iy", m => { const t = ty(m); return t[0] < t[1]; });

  // ---- NBA
  const fark = m => m.ms[0] - m.ms[1];
  const iade = (v, kosul) => v === 0 ? null : kosul;
  const bant = (a, b) => m => { const f = fark(m); return f >= a && f <= b; };
  const NBA = [
    ["N_MS1", "Ev sahibi kazanır", "Maç sonucu (uzatmalar dahil)", "ms", m => fark(m) > 0, "o1"],
    ["N_MS2", "Deplasman kazanır", "Maç sonucu (uzatmalar dahil)", "ms", m => fark(m) < 0, "o2"],
    ["N_HEV", "Ev handikabı kapatır", "Handikap (maçın kendi çizgisi)", "hnd", m => iade(fark(m) + m.hnd, fark(m) + m.hnd > 0), "hO1"],
    ["N_HDEP", "Deplasman handikabı kapatır", "Handikap (maçın kendi çizgisi)", "hnd", m => iade(fark(m) + m.hnd, fark(m) + m.hnd < 0), "hO2"],
    ["N_UST", "Toplam Üst", "Toplam sayı (maçın kendi çizgisi)", "tot", m => iade(g(m) - m.tot, g(m) > m.tot), "tO"],
    ["N_ALT", "Toplam Alt", "Toplam sayı (maçın kendi çizgisi)", "tot", m => iade(g(m) - m.tot, g(m) < m.tot), "tU"],
    ["N_EVU", "Ev takım toplamı Üst", "Takım sayıları (çizgiden hesaplanan)", "evT", m => iade(m.ms[0] - m.evT, m.ms[0] > m.evT)],
    ["N_EVA", "Ev takım toplamı Alt", "Takım sayıları (çizgiden hesaplanan)", "evT", m => iade(m.ms[0] - m.evT, m.ms[0] < m.evT)],
    ["N_DEPU", "Deplasman takım toplamı Üst", "Takım sayıları (çizgiden hesaplanan)", "depT", m => iade(m.ms[1] - m.depT, m.ms[1] > m.depT)],
    ["N_DEPA", "Deplasman takım toplamı Alt", "Takım sayıları (çizgiden hesaplanan)", "depT", m => iade(m.ms[1] - m.depT, m.ms[1] < m.depT)],
    ["N_E1", "Ev 1-5 farkla", "Kazanma farkı", "ms", bant(1, 5)], ["N_E6", "Ev 6-10 farkla", "Kazanma farkı", "ms", bant(6, 10)],
    ["N_E11", "Ev 11-15 farkla", "Kazanma farkı", "ms", bant(11, 15)], ["N_E16", "Ev 16+ farkla", "Kazanma farkı", "ms", bant(16, 999)],
    ["N_D1", "Deplasman 1-5 farkla", "Kazanma farkı", "ms", bant(-5, -1)], ["N_D6", "Deplasman 6-10 farkla", "Kazanma farkı", "ms", bant(-10, -6)],
    ["N_D11", "Deplasman 11-15 farkla", "Kazanma farkı", "ms", bant(-15, -11)], ["N_D16", "Deplasman 16+ farkla", "Kazanma farkı", "ms", bant(-999, -16)],
    ["N_TEK", "Toplam tek", "Tek / çift", "ms", m => g(m) % 2 === 1], ["N_CIFT", "Toplam çift", "Tek / çift", "ms", m => g(m) % 2 === 0]
  ];
  function kur(ad, liste) {
    const PZ = {}; liste.forEach((p, i) => PZ[p[0]] = { label: p[1], grup: p[2], i });
    return { ad, PAZARLAR: liste, PZ, P: liste.length };
  }
  return { futbol: kur("futbol", TEMEL.concat(GENIS)), nba: kur("nba", NBA), TEMEL_SAYI: TEMEL.length };
})();
if (typeof module !== "undefined" && module.exports) module.exports = PAZ;
