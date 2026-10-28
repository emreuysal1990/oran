#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sayfanın okuduğu veri.json dosyasını üretir. GitHub Actions bunu her saat çalıştırır.

Kaynaklar
  - football-data.co.uk: 22 Avrupa ligi (sonuç, İY, korner, kart, Bet365 oranı) ve
    MLS, İsveç, Norveç, Danimarka, Finlandiya (sonuç ve kapanış MS oranı).
  - The Odds API (isteğe bağlı, THE_ODDS_API_KEY): Şampiyonlar Ligi, Avrupa Ligi, Konferans Ligi,
    NBA ve ek liglerin güncel oranları; kupalar ve NBA için skorlar. Ücretsiz plan ayda 500 kredi;
    bu betik kredi harcamasını sınırlar.
  - football-data.org (isteğe bağlı, FOOTBALL_DATA_ORG_TOKEN): 8 büyük ligde aynı gün skorlar.

Kupalar ve NBA için geçmiş, oranlar ve skorlar biriktirilerek oluşur; birikim/ klasörü
iş akışı tarafından depodaki "veri" dalına kaydedilir.

  python3 guncelle.py --onbellek onbellek --birikim birikim --cikti _site/veri.json
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from datetime import time as dtime
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

KAYNAK = "https://www.football-data.co.uk"
FDORG = "https://api.football-data.org/v4/matches"
ODDS = "https://api.the-odds-api.com/v4/sports"
LON, IST = ZoneInfo("Europe/London"), ZoneInfo("Europe/Istanbul")

ANA_LIGLER = ["E0", "E1", "E2", "E3", "EC", "SC0", "SC1", "SC2", "SC3", "D1", "D2", "I1", "I2",
              "SP1", "SP2", "F1", "F2", "N1", "B1", "P1", "T1", "G1"]
EK_LIGLER = ["USA", "SWE", "NOR", "DNK", "FIN"]          # football-data "new/<kod>.csv"
KUPALAR = ["CL", "EL", "ECL"]
LIGLER = ANA_LIGLER + EK_LIGLER + KUPALAR
ODDS_SPOR = {"CL": "soccer_uefa_champs_league", "EL": "soccer_uefa_europa_league",
             "ECL": "soccer_uefa_europa_conference_league", "USA": "soccer_usa_mls",
             "SWE": "soccer_sweden_allsvenskan", "NOR": "soccer_norway_eliteserien",
             "DNK": "soccer_denmark_superliga", "FIN": "soccer_finland_veikkausliiga",
             "NBA": "basketball_nba"}
SKORLU = {"CL", "EL", "ECL", "NBA"}   # sonucu başka kaynaktan gelmeyenler: skorlar The Odds API'den
FDORG_LIG = {"PL": "E0", "ELC": "E1", "BL1": "D1", "SA": "I1", "PD": "SP1", "FL1": "F1", "DED": "N1", "PPL": "P1"}

# Oran kaynağı kodları (sayfada etiket olarak gösterilir)
OK_B365, OK_ORT, OK_PIN, OK_MAX, OK_PINK, OK_ORTK, OK_API = 0, 1, 2, 3, 4, 5, 6
MS_KAYNAKLARI = [("B365H", "B365D", "B365A", OK_B365), ("AvgH", "AvgD", "AvgA", OK_ORT), ("PSH", "PSD", "PSA", OK_PIN),
                 ("MaxH", "MaxD", "MaxA", OK_MAX), ("BbAvH", "BbAvD", "BbAvA", OK_ORT)]
MS_EK_KAYNAKLARI = [("PSCH", "PSCD", "PSCA", OK_PINK), ("AvgCH", "AvgCD", "AvgCA", OK_ORTK), ("B365CH", "B365CD", "B365CA", OK_B365),
                    ("MaxCH", "MaxCD", "MaxCA", OK_MAX), ("PSH", "PSD", "PSA", OK_PIN), ("AvgH", "AvgD", "AvgA", OK_ORT)]
AU_KAYNAKLARI = [("B365>2.5", "B365<2.5"), ("Avg>2.5", "Avg<2.5"), ("P>2.5", "P<2.5"), ("Max>2.5", "Max<2.5"),
                 ("BbAv>2.5", "BbAv<2.5"), ("PC>2.5", "PC<2.5"), ("AvgC>2.5", "AvgC<2.5"), ("B365C>2.5", "B365C<2.5")]
EPOCH = date(1970, 1, 1)
UA = {"User-Agent": "Mozilla/5.0 (benzer-oran-bulteni; github actions)"}


def simdi():
    return datetime.now(timezone.utc)


def gun_no(d):
    return (d - EPOCH).days


# ----------------------------------------------------------------------------- indirme
def sezon_kodlari(n_gecmis, bugun):
    y = bugun.year if bugun.month >= 7 else bugun.year - 1
    return [f"{(y - k) % 100:02d}{(y - k + 1) % 100:02d}" for k in range(n_gecmis, -1, -1)]


def indir(url, hedef, zorla, zorunlu=True):
    if os.path.exists(hedef) and not zorla:
        return True
    for deneme in range(3 if zorunlu else 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as yanit:
                veri = yanit.read()
            with open(hedef + ".tmp", "wb") as f:
                f.write(veri)
            os.replace(hedef + ".tmp", hedef)
            print(f"  indirildi: {url} ({len(veri) // 1024} KB)")
            return True
        except (urllib.error.URLError, OSError) as e:
            print(f"  {'deneme ' + str(deneme + 1) + ' ' if zorunlu else ''}başarısız: {url} ({e})")
            if zorunlu:
                time.sleep(5 * (deneme + 1))
    return os.path.exists(hedef)


# ----------------------------------------------------------------------------- okuma
def csv_satirlari(ham):
    metin = ""
    for kod in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            metin = ham.decode(kod)
            break
        except UnicodeDecodeError:
            continue
    satirlar = list(csv.reader(io.StringIO(metin)))
    if not satirlar:
        return []
    baslik = [b.strip().lstrip("﻿") for b in satirlar[0]]
    return [{baslik[i]: s[i].strip() for i in range(min(len(baslik), len(s))) if baslik[i]}
            for s in satirlar[1:] if s and any(h.strip() for h in s)]


def sayi(x):
    x = (x or "").strip().replace(",", ".")
    if not x:
        return None
    try:
        return float(x)
    except ValueError:
        return None


def tarih_coz(s):
    s = (s or "").strip()
    for bicim in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, bicim).date()
        except ValueError:
            continue
    return None


def tr_saat(d, hhmm):
    """football-data saatleri İngiltere saatidir; Türkiye saatine çevir. (gün_no, 'SS:DD')"""
    m = re.match(r"^(\d{1,2}):(\d{2})", hhmm or "")
    if not m:
        return gun_no(d), ""
    dt = datetime.combine(d, dtime(int(m.group(1)), int(m.group(2))), LON).astimezone(IST)
    return gun_no(dt.date()), dt.strftime("%H:%M")


def oran100(x):
    return int(round(x * 100)) if x and x > 1 else None


def oranlar(r, ms_kaynaklari):
    ms, ok = None, None
    for h, d, a, kod in ms_kaynaklari:
        v = [oran100(sayi(r.get(k))) for k in (h, d, a)]
        if all(v):
            ms, ok = v, kod
            break
    au = [None, None]
    for u, a in AU_KAYNAKLARI:
        v = [oran100(sayi(r.get(k))) for k in (u, a)]
        if all(v):
            au = v
            break
    return ms, au, ok


def oku(r, varsayilan_lig, sonuclu):
    """football-data ana lig satırı."""
    lig = (r.get("Div") or varsayilan_lig or "").strip()
    if lig not in ANA_LIGLER:
        return None
    t = tarih_coz(r.get("Date"))
    ev = (r.get("HomeTeam") or r.get("Home") or "").strip()
    dep = (r.get("AwayTeam") or r.get("Away") or "").strip()
    if not t or not ev or not dep:
        return None
    ms, au, ok = oranlar(r, MS_KAYNAKLARI)
    if not ms:
        return None
    g, saat = tr_saat(t, r.get("Time"))
    m = {"lig": lig, "gun": g, "saat": saat, "ev": ev, "dep": dep, "oran": ms + au, "ok": ok}
    if sonuclu:
        fh, fa = sayi(r.get("FTHG") or r.get("HG")), sayi(r.get("FTAG") or r.get("AG"))
        if fh is None or fa is None:
            return None
        hh, ha = sayi(r.get("HTHG")), sayi(r.get("HTAG"))
        hc, ac = sayi(r.get("HC")), sayi(r.get("AC"))
        kart = [sayi(r.get(k)) for k in ("HY", "AY", "HR", "AR")]
        m["sonuc"] = [int(fh), int(fa),
                      None if hh is None or ha is None else int(hh), None if hh is None or ha is None else int(ha),
                      None if hc is None or ac is None else int(hc + ac),
                      None if any(k is None for k in kart) else int(sum(kart))]
    return m


def oku_ek(r, lig, ilk_gun):
    """football-data ek lig satırı (new/USA.csv gibi): sadece skor ve kapanış MS oranı."""
    t = tarih_coz(r.get("Date"))
    ev, dep = (r.get("Home") or r.get("HomeTeam") or "").strip(), (r.get("Away") or r.get("AwayTeam") or "").strip()
    fh, fa = sayi(r.get("HG") or r.get("FTHG")), sayi(r.get("AG") or r.get("FTAG"))
    if not t or not ev or not dep or fh is None or fa is None or gun_no(t) < ilk_gun:
        return None
    ms, au, ok = oranlar(r, MS_EK_KAYNAKLARI)
    if not ms:
        return None
    g, saat = tr_saat(t, r.get("Time"))
    return {"lig": lig, "gun": g, "saat": saat, "ev": ev, "dep": dep, "oran": ms + au, "ok": ok,
            "sonuc": [int(fh), int(fa), None, None, None, None]}


def anahtar(m):
    return (m["lig"], m["gun"], m["ev"], m["dep"])


# ----------------------------------------------------------------------------- takım adı eşleştirme
TAKMA = {
    "man united": "manchester united", "man city": "manchester city", "nottm forest": "nottingham forest",
    "sheffield weds": "sheffield wednesday", "west brom": "west bromwich albion", "qpr": "queens park rangers",
    "wolves": "wolverhampton wanderers", "spurs": "tottenham hotspur", "brighton": "brighton hove albion",
    "ath madrid": "atletico madrid", "ath bilbao": "athletic club bilbao", "sociedad": "real sociedad",
    "betis": "real betis", "vallecano": "rayo vallecano", "espanol": "espanyol", "celta": "celta vigo",
    "alaves": "deportivo alaves", "la coruna": "deportivo la coruna",
    "ein frankfurt": "eintracht frankfurt", "mgladbach": "borussia monchengladbach", "fc koln": "koln",
    "leverkusen": "bayer leverkusen", "dortmund": "borussia dortmund", "bayern munich": "bayern munchen",
    "hertha": "hertha berlin", "hamburg": "hamburger",
    "paris sg": "paris saint germain", "st etienne": "saint etienne",
    "inter": "internazionale milano", "verona": "hellas verona",
    "sp lisbon": "sporting clube portugal lisbon", "sp braga": "sporting braga", "guimaraes": "vitoria guimaraes",
    "for sittard": "fortuna sittard", "nijmegen": "nec nijmegen", "zwolle": "pec zwolle",
    "waalwijk": "rkc waalwijk", "psv eindhoven": "psv", "az alkmaar": "az",
}
DOLGU = {"fc", "afc", "cf", "sc", "ac", "as", "us", "ssc", "rc", "cd", "ud", "sd", "club", "de", "la", "le", "the",
         "fk", "sv", "tsg", "vfb", "vfl", "bv", "calcio", "and", "1", "05", "04", "1899", "1846", "1907", "1909",
         "1910", "1913", "1919", "sad", "futbol", "football", "clube"}


def tokenler(ad, takma=False):
    s = unicodedata.normalize("NFKD", ad or "").encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ").replace("'", "").replace(".", " ")
    s = " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())
    if takma and s in TAKMA:
        s = TAKMA[s]
    return [t for t in s.split() if t not in DOLGU]


def benzerlik(a, b):
    if not a or not b:
        return 0.0
    kisa, uzun = (a, b) if len(a) <= len(b) else (b, a)
    eslesen = sum(1 for t in kisa if any(t == u or (len(t) >= 3 and len(u) >= 3 and (t.startswith(u) or u.startswith(t)))
                                         for u in uzun))
    return max(0.95 * eslesen / len(kisa), SequenceMatcher(None, " ".join(a), " ".join(b)).ratio())


def ad_benzerligi(couk_ad, org_adlar):
    a = tokenler(couk_ad, takma=True)
    return max((benzerlik(a, tokenler(x)) for x in org_adlar if x), default=0.0)


def eslestir(gecici, fiksturler, esik=0.55):
    adaylar = []
    for gi, g in enumerate(gecici):
        for fi, f in enumerate(fiksturler):
            if f["lig"] != g["lig"] or abs(f["gun"] - g["gun"]) > 1:
                continue
            se, sd = ad_benzerligi(f["ev"], g["ev"]), ad_benzerligi(f["dep"], g["dep"])
            if min(se, sd) < 0.35 or (se + sd) / 2 < esik:
                continue
            adaylar.append((se + sd - 0.05 * abs(f["gun"] - g["gun"]), gi, fi))
    adaylar.sort(reverse=True)
    kg, kf, ciftler = set(), set(), []
    for _, gi, fi in adaylar:
        if gi in kg or fi in kf:
            continue
        kg.add(gi)
        kf.add(fi)
        ciftler.append((gecici[gi], fiksturler[fi]))
    return ciftler


# ----------------------------------------------------------------------------- football-data.org
def gecici_sonuclar(token, gun_bas, gun_bit):
    url = (f"{FDORG}?competitions={','.join(FDORG_LIG)}&status=FINISHED"
           f"&dateFrom={(EPOCH + timedelta(days=gun_bas)).isoformat()}&dateTo={(EPOCH + timedelta(days=gun_bit)).isoformat()}")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={**UA, "X-Auth-Token": token}), timeout=60) as y:
            veri = json.load(y)
    except Exception as e:  # noqa
        print(f"  ! football-data.org okunamadı: {e}")
        return []
    sonuc = []
    for m in veri.get("matches", []):
        lig = FDORG_LIG.get((m.get("competition") or {}).get("code"))
        skor = m.get("score") or {}
        ft, ht = skor.get("fullTime") or {}, skor.get("halfTime") or {}
        if not lig or m.get("status") != "FINISHED" or ft.get("home") is None or ft.get("away") is None:
            continue
        if skor.get("duration") not in (None, "REGULAR"):
            continue
        u = datetime.strptime(m["utcDate"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(IST)
        ev, dep = m.get("homeTeam") or {}, m.get("awayTeam") or {}
        sonuc.append({"lig": lig, "gun": gun_no(u.date()),
                      "ev": [ev.get("name"), ev.get("shortName"), ev.get("tla")],
                      "dep": [dep.get("name"), dep.get("shortName"), dep.get("tla")],
                      "ms": [ft["home"], ft["away"]],
                      "iy": [ht.get("home"), ht.get("away")] if ht.get("home") is not None else [None, None]})
    print(f"  football-data.org: {len(sonuc)} biten maç")
    return sonuc


# ----------------------------------------------------------------------------- The Odds API
class OddsAPI:
    """Ücretsiz planda ayda 500 kredi. /events ücretsiz; /odds = pazar sayısı × bölge; /scores (daysFrom ile) = 2."""

    def __init__(self, anahtar, durum, test_klasoru=None):
        self.anahtar, self.durum, self.test = anahtar, durum, test_klasoru
        self.durum.setdefault("son_oran", {})
        self.durum.setdefault("son_skor", {})

    def aktif(self):
        return bool(self.anahtar or self.test)

    def _get(self, yol, params, test_adi):
        if self.test:
            p = os.path.join(self.test, test_adi)
            return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []
        q = urllib.parse.urlencode({**params, "apiKey": self.anahtar})
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{ODDS}/{yol}?{q}", headers=UA), timeout=60) as y:
                kalan = y.headers.get("x-requests-remaining")
                if kalan is not None:
                    self.durum["kalan"] = int(float(kalan))
                return json.load(y)
        except urllib.error.HTTPError as e:
            print(f"  ! The Odds API {yol}: HTTP {e.code}")
            if e.code in (401, 429):
                self.durum["hata"] = f"HTTP {e.code}"
        except Exception as e:  # noqa
            print(f"  ! The Odds API {yol}: {e}")
        return None

    def kredi_var(self, gereken):
        kalan = self.durum.get("kalan")
        return kalan is None or kalan - gereken >= 15

    def eski(self, tur, spor, saat):
        son = self.durum[tur].get(spor)
        if self.test:
            return True
        return not son or simdi() - datetime.fromisoformat(son) > timedelta(hours=saat)

    def etkinlikler(self, spor):
        return self._get(f"{spor}/events", {}, f"{spor}_events.json") or []

    def oranlar(self, spor, piyasalar):
        if not self.kredi_var(len(piyasalar)):
            print(f"  ! kredi az, {spor} oranları atlandı")
            return None
        bas = simdi().replace(microsecond=0)
        veri = self._get(f"{spor}/odds", {"regions": "eu", "markets": ",".join(piyasalar), "oddsFormat": "decimal",
                                          "commenceTimeFrom": bas.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                          "commenceTimeTo": (bas + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")},
                         f"{spor}_odds.json")
        if veri is not None:
            self.durum["son_oran"][spor] = simdi().isoformat()
        return veri

    def skorlar(self, spor):
        if not self.kredi_var(2):
            print(f"  ! kredi az, {spor} skorları atlandı")
            return None
        veri = self._get(f"{spor}/scores", {"daysFrom": 3}, f"{spor}_scores.json")
        if veri is not None:
            self.durum["son_skor"][spor] = simdi().isoformat()
        return veri


def utc(s):
    return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def ort(degerler):
    d = [x for x in degerler if x and x > 1]
    return sum(d) / len(d) if d else None


def oran_ozeti(ev_kaydi, spor_turu):
    """Bahis şirketlerinin oranlarının ortalaması. Futbol: 1X2 + 2,5 A/Ü. NBA: ML + handikap + toplam."""
    ev_ad, dep_ad = ev_kaydi["home_team"], ev_kaydi["away_team"]
    h2h = {"ev": [], "dep": [], "x": []}
    toplam, handikap = {}, {}
    for b in ev_kaydi.get("bookmakers", []):
        for pz in b.get("markets", []):
            oc = pz.get("outcomes", [])
            if pz.get("key") == "h2h":
                for o in oc:
                    k = "ev" if o.get("name") == ev_ad else "dep" if o.get("name") == dep_ad else "x"
                    h2h[k].append(o.get("price"))
            elif pz.get("key") == "totals":
                for o in oc:
                    nokta = o.get("point")
                    if nokta is None:
                        continue
                    toplam.setdefault(nokta, {"Over": [], "Under": []}).setdefault(o.get("name"), []).append(o.get("price"))
            elif pz.get("key") == "spreads":
                ev_o = next((o for o in oc if o.get("name") == ev_ad), None)
                dep_o = next((o for o in oc if o.get("name") == dep_ad), None)
                if ev_o and dep_o and ev_o.get("point") is not None:
                    h = handikap.setdefault(ev_o["point"], {"ev": [], "dep": []})
                    h["ev"].append(ev_o.get("price"))
                    h["dep"].append(dep_o.get("price"))
    o1, o2, ox = ort(h2h["ev"]), ort(h2h["dep"]), ort(h2h["x"])
    if spor_turu == "futbol":
        if not (o1 and o2 and ox):
            return None
        t = toplam.get(2.5, {})
        ou, oa = ort(t.get("Over", [])), ort(t.get("Under", []))
        return [oran100(o1), oran100(ox), oran100(o2), oran100(ou) if ou and oa else None, oran100(oa) if ou and oa else None]
    if not (o1 and o2):
        return None
    sonuc = [oran100(o1), oran100(o2), None, None, None, None, None, None]
    if handikap:
        nokta = Counter({p: len(v["ev"]) for p, v in handikap.items()}).most_common(1)[0][0]
        sonuc[2:5] = [int(round(nokta * 10)), oran100(ort(handikap[nokta]["ev"])), oran100(ort(handikap[nokta]["dep"]))]
    if toplam:
        nokta = Counter({p: len(v.get("Over", [])) for p, v in toplam.items()}).most_common(1)[0][0]
        sonuc[5:8] = [int(round(nokta * 10)), oran100(ort(toplam[nokta].get("Over", []))), oran100(ort(toplam[nokta].get("Under", [])))]
    return sonuc


def odds_api_guncelle(api, birikim):
    """bekleyen: oranı alınmış, sonucu bekleyen etkinlikler (id ile). sonuclu: oran + skoru olan kalıcı kayıtlar."""
    bekleyen, sonuclu = birikim["bekleyen"], birikim["sonuclu"]
    su_an = simdi()
    for lig, spor in ODDS_SPOR.items():
        tur = "nba" if lig == "NBA" else "futbol"
        piyasalar = ["h2h", "spreads", "totals"] if tur == "nba" else ["h2h", "totals"]
        # 1) Oranlar: günde en fazla bir kez ve sadece 48 saat içinde maç varsa (etkinlik listesi ücretsiz)
        if api.eski("son_oran", spor, 20):
            etk = api.etkinlikler(spor)
            yakin = [e for e in etk if su_an - timedelta(hours=1) < utc(e["commence_time"]) < su_an + timedelta(hours=48)]
            if yakin:
                veri = api.oranlar(spor, piyasalar)
                for e in veri or []:
                    o = oran_ozeti(e, tur)
                    if not o:
                        continue
                    t = utc(e["commence_time"]).astimezone(IST)
                    bekleyen[e["id"]] = {"tur": tur, "lig": lig, "ts": e["commence_time"], "gun": gun_no(t.date()),
                                         "saat": t.strftime("%H:%M"), "ev": e["home_team"], "dep": e["away_team"], "oran": o}
                print(f"  {spor}: {len(veri or [])} etkinliğin oranı alındı")
        # 2) Skorlar: kupalar ve NBA için, oynanmış ama sonucu gelmemiş maç varsa (6 saatte bir)
        if lig in SKORLU and api.eski("son_skor", spor, 6):
            bekleyenler = [k for k, b in bekleyen.items() if b["lig"] == lig and su_an - timedelta(days=3) < utc(b["ts"]) < su_an - timedelta(hours=2)]
            if bekleyenler:
                for e in api.skorlar(spor) or []:
                    b = bekleyen.get(e.get("id"))
                    if not b or not e.get("completed") or not e.get("scores"):
                        continue
                    sk = {s.get("name"): s.get("score") for s in e["scores"]}
                    try:
                        ev_s, dep_s = int(sk[b["ev"]]), int(sk[b["dep"]])
                    except (KeyError, TypeError, ValueError):
                        continue
                    sonuclu[e["id"]] = dict(b, skor=[ev_s, dep_s])
                    del bekleyen[e["id"]]
                print(f"  {spor}: skorlar kontrol edildi")
    # 3) Eski bekleyenleri temizle (4 gün sonra hâlâ sonucu yoksa)
    for k in [k for k, b in bekleyen.items() if utc(b["ts"]) < su_an - timedelta(days=4)]:
        del bekleyen[k]


# ----------------------------------------------------------------------------- yardımcılar
def json_oku(yol, varsayilan):
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return varsayilan


def json_yaz(yol, veri):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


# ----------------------------------------------------------------------------- ana akış
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onbellek", default="onbellek")
    ap.add_argument("--birikim", default="birikim")
    ap.add_argument("--cikti", default="_site/veri.json")
    ap.add_argument("--sezon", type=int, default=3)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--fdorg-dosya", help="Test: football-data.org yanıtı yerine bu JSON")
    ap.add_argument("--odds-test", help="Test: The Odds API yanıtlarının bulunduğu klasör")
    a = ap.parse_args()
    for d in (a.onbellek, a.birikim, os.path.dirname(os.path.abspath(a.cikti))):
        os.makedirs(d, exist_ok=True)

    bugun = simdi().astimezone(IST).date()
    bugun_no = gun_no(bugun)
    kodlar = sezon_kodlari(a.sezon, bugun)
    ilk_gun = gun_no(date(2000 + int(kodlar[0][:2]), 7, 1))
    if not a.offline:
        for i, k in enumerate(kodlar):
            indir(f"{KAYNAK}/mmz4281/{k}/data.zip", os.path.join(a.onbellek, f"{k}.zip"), zorla=(i == len(kodlar) - 1))
        indir(f"{KAYNAK}/fixtures.csv", os.path.join(a.onbellek, "fixtures.csv"), zorla=True)
        for lig in EK_LIGLER:
            yol = os.path.join(a.onbellek, f"ek_{lig}.csv")
            eski = not os.path.exists(yol) or time.time() - os.path.getmtime(yol) > 6 * 3600
            indir(f"{KAYNAK}/new/{lig}.csv", yol, zorla=eski)
        indir(f"{KAYNAK}/new_league_fixtures.csv", os.path.join(a.onbellek, "ek_fixtures.csv"), zorla=True, zorunlu=False)

    # 1) Kesin sonuçlar: ana ligler
    maclar = {}
    for k in kodlar:
        yol = os.path.join(a.onbellek, f"{k}.zip")
        if not os.path.exists(yol):
            print(f"  ! {k} sezonu yok")
            continue
        with zipfile.ZipFile(yol) as z:
            for ad in z.namelist():
                kod = os.path.splitext(os.path.basename(ad))[0]
                if kod not in ANA_LIGLER:
                    continue
                for r in csv_satirlari(z.read(ad)):
                    m = oku(r, kod, sonuclu=True)
                    if m:
                        maclar[anahtar(m)] = m
    if not maclar:
        print("Hiç maç okunamadı.")
        sys.exit(1)
    # Ek ligler (MLS, İskandinav ligleri)
    ek_say = Counter()
    for lig in EK_LIGLER:
        yol = os.path.join(a.onbellek, f"ek_{lig}.csv")
        if not os.path.exists(yol):
            print(f"  ! {lig} verisi yok")
            continue
        with open(yol, "rb") as f:
            for r in csv_satirlari(f.read()):
                m = oku_ek(r, lig, ilk_gun)
                if m:
                    maclar[anahtar(m)] = m
                    ek_say[lig] += 1
    print(f"  ek ligler: {dict(ek_say)}")

    # 2) Fikstür arşivi (football-data fikstürleri her yayında değişir; oranları 30 gün sakla)
    arsiv_yol = os.path.join(a.onbellek, "fikstur_arsiv_v2.json")
    arsiv = {anahtar(m): m for m in json_oku(arsiv_yol, [])}
    for dosya in ("fixtures.csv", "ek_fixtures.csv"):
        fyol = os.path.join(a.onbellek, dosya)
        if os.path.exists(fyol):
            with open(fyol, "rb") as f:
                for r in csv_satirlari(f.read()):
                    m = oku(r, None, sonuclu=False)
                    if not m and (r.get("Div") or r.get("Country")):
                        lig = {"USA": "USA", "Sweden": "SWE", "Norway": "NOR", "Denmark": "DNK", "Finland": "FIN"}.get(
                            (r.get("Div") or r.get("Country") or "").strip())
                        if lig:
                            t = tarih_coz(r.get("Date"))
                            ms, au, ok = oranlar(r, MS_EK_KAYNAKLARI + MS_KAYNAKLARI)
                            if t and ms:
                                g, saat = tr_saat(t, r.get("Time"))
                                m = {"lig": lig, "gun": g, "saat": saat, "ev": (r.get("Home") or r.get("HomeTeam") or "").strip(),
                                     "dep": (r.get("Away") or r.get("AwayTeam") or "").strip(), "oran": ms + au, "ok": ok}
                    if m and m["ev"] and m["dep"]:
                        arsiv[anahtar(m)] = m
    arsiv = {k: m for k, m in arsiv.items() if m["gun"] >= bugun_no - 30}
    json_yaz(arsiv_yol, list(arsiv.values()))

    # 3) The Odds API: kupalar, NBA, ek ligler (kalıcı birikim "veri" dalında)
    birikim = {"bekleyen": json_oku(os.path.join(a.birikim, "bekleyen.json"), {}),
               "sonuclu": json_oku(os.path.join(a.birikim, "sonuclu.json"), {})}
    durum = json_oku(os.path.join(a.birikim, "durum.json"), {})
    durum.pop("hata", None)
    api = OddsAPI(os.environ.get("THE_ODDS_API_KEY", "").strip(), durum, a.odds_test)
    if api.aktif():
        odds_api_guncelle(api, birikim)
    else:
        print("  THE_ODDS_API_KEY yok; kupalar, NBA ve ek liglerin güncel oranları atlandı")

    # 4) Aynı gün sonuçlar (football-data.org)
    sonucsuz = [m for k, m in arsiv.items() if k not in maclar and m["gun"] <= bugun_no and m["lig"] in FDORG_LIG.values()]
    gecici = {}
    token = os.environ.get("FOOTBALL_DATA_ORG_TOKEN", "").strip()
    if sonucsuz and (token or a.fdorg_dosya):
        bas = max(min(m["gun"] for m in sonucsuz), bugun_no - 9) - 1
        org = json_oku(a.fdorg_dosya, []) if a.fdorg_dosya else gecici_sonuclar(token, bas, bugun_no)
        for g, f in eslestir(org, sonucsuz):
            gecici[anahtar(f)] = dict(f, sonuc=[g["ms"][0], g["ms"][1], g["iy"][0], g["iy"][1], None, None])
        print(f"  {len(gecici)} geçici sonuç eşleşti")

    # 5) Çıktı
    takim = {}

    def t(ad):
        if ad not in takim:
            takim[ad] = len(takim)
        return takim[ad]

    def bas_alanlar(m):
        return [LIGLER.index(m["lig"]), m["gun"], m["saat"], t(m["ev"]), t(m["dep"])]

    sirala = lambda l: sorted(l, key=lambda m: (m["gun"], m["saat"], m["lig"]))  # noqa
    # Kupa maçları (biriken): futbol sonuçlarına katılır
    kupa_m = []
    for b in birikim["sonuclu"].values():
        if b["tur"] == "futbol" and b["lig"] in KUPALAR:
            kupa_m.append({**b, "oran": b["oran"], "ok": OK_API, "sonuc": [b["skor"][0], b["skor"][1], None, None, None, None]})
    m_liste = [bas_alanlar(m) + m["sonuc"] + m["oran"] + [m["ok"]] for m in sirala(list(maclar.values()) + kupa_m)]
    g_liste = [bas_alanlar(m) + m["sonuc"] + m["oran"] + [m["ok"]] for m in sirala(gecici.values())]
    simdi_ts = simdi()
    api_fik = [{**b, "ok": OK_API} for b in birikim["bekleyen"].values()
               if b["tur"] == "futbol" and utc(b["ts"]) > simdi_ts - timedelta(hours=2)]
    f_kaynak = [m for k, m in arsiv.items() if k not in maclar and k not in gecici and m["gun"] >= bugun_no]
    f_liste = [bas_alanlar(m) + m["oran"] + [m["ok"]] for m in sirala(f_kaynak + api_fik)]
    nba_m = [[b["gun"], b["saat"], t(b["ev"]), t(b["dep"])] + b["skor"] + b["oran"]
             for b in sirala([b for b in birikim["sonuclu"].values() if b["tur"] == "nba"])]
    nba_f = [[b["gun"], b["saat"], t(b["ev"]), t(b["dep"])] + b["oran"]
             for b in sirala([b for b in birikim["bekleyen"].values() if b["tur"] == "nba" and utc(b["ts"]) > simdi_ts - timedelta(hours=2)])]
    veri = {
        "olusturma": simdi_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kaynak": "football-data.co.uk",
        "lig": LIGLER,
        "takim": [ad for ad, _ in sorted(takim.items(), key=lambda x: x[1])],
        "m": m_liste, "g": g_liste, "f": f_liste,
        "nba": {"m": nba_m, "f": nba_f},
        "odds_api": {"aktif": api.aktif(), "kalan": durum.get("kalan"), "hata": durum.get("hata")},
        "gecici_kaynak": "football-data.org" if g_liste else None,
    }
    with open(a.cikti, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, separators=(",", ":"))

    # Birikimi ve durum özetini kaydet (iş akışı bunları "veri" dalına gönderir)
    json_yaz(os.path.join(a.birikim, "bekleyen.json"), birikim["bekleyen"])
    json_yaz(os.path.join(a.birikim, "sonuclu.json"), birikim["sonuclu"])
    lig_say = Counter(LIGLER[r[0]] for r in m_liste)
    durum["ozet"] = {"mac": len(m_liste), "gecici": len(g_liste), "fikstur": len(f_liste), "nba_mac": len(nba_m),
                     "nba_fikstur": len(nba_f), "son_mac_gunu": max(r[1] for r in m_liste),
                     "lig": dict(sorted(lig_say.items())), "odds_api_aktif": api.aktif()}
    json_yaz(os.path.join(a.birikim, "durum.json"), durum)
    print(f"{len(m_liste)} maç, {len(g_liste)} geçici, {len(f_liste)} gelecek futbol maçı, "
          f"{len(nba_m)} NBA maçı, {len(nba_f)} gelecek NBA maçı → {a.cikti}")


if __name__ == "__main__":
    main()
