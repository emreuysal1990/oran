#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sayfanın okuduğu veri.json dosyasını üretir. GitHub Actions bunu her saat çalıştırır.

Kaynaklar
  - football-data.co.uk: sonuçlar, İY skoru, korner, kart ve oranlar (haftada birkaç kez güncellenir)
  - football-data.org (isteğe bağlı): 8 büyük ligde aynı gün biten maçların skoru.
    GitHub'da FOOTBALL_DATA_ORG_TOKEN adlı secret tanımlıysa kullanılır; yoksa atlanır.

  python3 guncelle.py --onbellek onbellek --cikti _site/veri.json
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
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher

KAYNAK = "https://www.football-data.co.uk"
FDORG = "https://api.football-data.org/v4/matches"
LIGLER = ["E0", "E1", "E2", "E3", "EC", "SC0", "SC1", "SC2", "SC3", "D1", "D2", "I1", "I2",
          "SP1", "SP2", "F1", "F2", "N1", "B1", "P1", "T1", "G1"]
FDORG_LIG = {"PL": "E0", "ELC": "E1", "BL1": "D1", "SA": "I1", "PD": "SP1", "FL1": "F1", "DED": "N1", "PPL": "P1"}
MS_KAYNAKLARI = [("B365H", "B365D", "B365A"), ("AvgH", "AvgD", "AvgA"), ("PSH", "PSD", "PSA"),
                 ("MaxH", "MaxD", "MaxA"), ("BbAvH", "BbAvD", "BbAvA")]
AU_KAYNAKLARI = [("B365>2.5", "B365<2.5"), ("Avg>2.5", "Avg<2.5"), ("P>2.5", "P<2.5"),
                 ("Max>2.5", "Max<2.5"), ("BbAv>2.5", "BbAv<2.5")]
EPOCH = date(1970, 1, 1)
UA = {"User-Agent": "Mozilla/5.0 (benzer-oran-bulteni; github actions)"}


# ----------------------------------------------------------------------------- indirme
def sezon_kodlari(n_gecmis, bugun):
    y = bugun.year if bugun.month >= 7 else bugun.year - 1
    return [f"{(y - k) % 100:02d}{(y - k + 1) % 100:02d}" for k in range(n_gecmis, -1, -1)]


def indir(url, hedef, zorla):
    if os.path.exists(hedef) and not zorla:
        return True
    for deneme in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as yanit:
                veri = yanit.read()
            with open(hedef + ".tmp", "wb") as f:
                f.write(veri)
            os.replace(hedef + ".tmp", hedef)
            print(f"  indirildi: {url} ({len(veri) // 1024} KB)")
            return True
        except (urllib.error.URLError, OSError) as e:
            print(f"  deneme {deneme + 1} başarısız: {url} ({e})")
            time.sleep(5 * (deneme + 1))
    return os.path.exists(hedef)


# ----------------------------------------------------------------------------- okuma
def csv_satirlari(ham):
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


def oran100(x):
    return int(round(x * 100)) if x and x > 1 else None


def oku(r, varsayilan_lig, sonuclu):
    """Bir CSV satırını sözlüğe çevirir; takım adları düz metin."""
    lig = (r.get("Div") or varsayilan_lig or "").strip()
    if lig not in LIGLER:
        return None
    t = tarih_coz(r.get("Date"))
    ev = (r.get("HomeTeam") or r.get("Home") or "").strip()
    dep = (r.get("AwayTeam") or r.get("Away") or "").strip()
    if not t or not ev or not dep:
        return None
    ms = None
    for h, d, a in MS_KAYNAKLARI:
        v = [oran100(sayi(r.get(k))) for k in (h, d, a)]
        if all(v):
            ms = v
            break
    if not ms:
        return None
    au = [None, None]
    for u, a in AU_KAYNAKLARI:
        v = [oran100(sayi(r.get(k))) for k in (u, a)]
        if all(v):
            au = v
            break
    m = {"lig": lig, "gun": (t - EPOCH).days, "saat": (r.get("Time") or "").strip()[:5], "ev": ev, "dep": dep,
         "oran": ms + au}
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


def anahtar(m):
    return (m["lig"], m["gun"], m["ev"], m["dep"])


# ----------------------------------------------------------------------------- takım adı eşleştirme
# football-data.co.uk kısaltmaları -> açık adlar (football-data.org adlarıyla karşılaştırmak için)
TAKMA = {
    "man united": "manchester united", "man city": "manchester city", "nottm forest": "nottingham forest",
    "sheffield weds": "sheffield wednesday", "west brom": "west bromwich albion", "qpr": "queens park rangers",
    "wolves": "wolverhampton wanderers", "spurs": "tottenham hotspur", "brighton": "brighton hove albion",
    "ath madrid": "atletico madrid", "ath bilbao": "athletic club bilbao", "sociedad": "real sociedad",
    "betis": "real betis", "vallecano": "rayo vallecano", "espanol": "espanyol", "celta": "celta vigo",
    "alaves": "deportivo alaves", "la coruna": "deportivo la coruna",
    "ein frankfurt": "eintracht frankfurt", "mgladbach": "borussia monchengladbach", "fc koln": "koln",
    "leverkusen": "bayer leverkusen", "dortmund": "borussia dortmund", "bayern munich": "bayern munchen",
    "hertha": "hertha berlin", "union berlin": "union berlin", "st pauli": "st pauli", "hamburg": "hamburger",
    "paris sg": "paris saint germain", "st etienne": "saint etienne",
    "inter": "internazionale milano", "milan": "milan", "verona": "hellas verona",
    "sp lisbon": "sporting clube portugal lisbon", "sp braga": "sporting braga", "guimaraes": "vitoria guimaraes",
    "for sittard": "fortuna sittard", "nijmegen": "nec nijmegen", "zwolle": "pec zwolle",
    "waalwijk": "rkc waalwijk", "psv eindhoven": "psv", "az alkmaar": "az", "go ahead eagles": "go ahead eagles",
}
DOLGU = {"fc", "afc", "cf", "sc", "ac", "as", "us", "ssc", "rc", "cd", "ud", "sd", "club", "de", "la", "le", "the",
         "fk", "sv", "tsg", "vfb", "vfl", "bv", "calcio", "and", "1", "05", "04", "1899", "1846", "1907", "1909",
         "1910", "1913", "1919", "sad", "futbol", "football", "clube"}


def tokenler(ad, takma=False):
    s = unicodedata.normalize("NFKD", ad).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ").replace("'", "").replace(".", " ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = " ".join(s.split())
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


# ----------------------------------------------------------------------------- football-data.org
def gecici_sonuclar(token, gun_bas, gun_bit):
    url = (f"{FDORG}?competitions={','.join(FDORG_LIG)}&status=FINISHED"
           f"&dateFrom={(EPOCH + timedelta(days=gun_bas)).isoformat()}&dateTo={(EPOCH + timedelta(days=gun_bit)).isoformat()}")
    try:
        istek = urllib.request.Request(url, headers={**UA, "X-Auth-Token": token})
        with urllib.request.urlopen(istek, timeout=60) as yanit:
            veri = json.load(yanit)
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
            continue  # uzatma/penaltı olan kupa maçları
        t = datetime.strptime(m["utcDate"][:10], "%Y-%m-%d").date()
        ev, dep = m.get("homeTeam") or {}, m.get("awayTeam") or {}
        sonuc.append({"lig": lig, "gun": (t - EPOCH).days,
                      "ev": [ev.get("name"), ev.get("shortName"), ev.get("tla")],
                      "dep": [dep.get("name"), dep.get("shortName"), dep.get("tla")],
                      "ms": [ft["home"], ft["away"]],
                      "iy": [ht.get("home"), ht.get("away")] if ht.get("home") is not None else [None, None]})
    print(f"  football-data.org: {len(sonuc)} biten maç")
    return sonuc


def eslestir(gecici, fiksturler, esik=0.55):
    """Geçici sonuçları oranlı fikstürlere bağlar. Aynı lig, ±1 gün; en iyi çiftler önce."""
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
    kullanilan_g, kullanilan_f, ciftler = set(), set(), []
    for skor, gi, fi in adaylar:
        if gi in kullanilan_g or fi in kullanilan_f:
            continue
        kullanilan_g.add(gi)
        kullanilan_f.add(fi)
        ciftler.append((gecici[gi], fiksturler[fi]))
    return ciftler


# ----------------------------------------------------------------------------- ana akış
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onbellek", default="onbellek")
    ap.add_argument("--cikti", default="_site/veri.json")
    ap.add_argument("--sezon", type=int, default=3)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--fdorg-dosya", help="Test için: football-data.org yanıtı yerine bu JSON listesini kullan")
    a = ap.parse_args()
    os.makedirs(a.onbellek, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.cikti)), exist_ok=True)

    bugun = datetime.now(timezone.utc).date()
    bugun_no = (bugun - EPOCH).days
    kodlar = sezon_kodlari(a.sezon, bugun)
    if not a.offline:
        for i, k in enumerate(kodlar):
            indir(f"{KAYNAK}/mmz4281/{k}/data.zip", os.path.join(a.onbellek, f"{k}.zip"), zorla=(i == len(kodlar) - 1))
        indir(f"{KAYNAK}/fixtures.csv", os.path.join(a.onbellek, "fixtures.csv"), zorla=True)

    # 1) Kesin sonuçlar (football-data.co.uk)
    maclar = {}
    for k in kodlar:
        yol = os.path.join(a.onbellek, f"{k}.zip")
        if not os.path.exists(yol):
            print(f"  ! {k} sezonu yok")
            continue
        with zipfile.ZipFile(yol) as z:
            for ad in z.namelist():
                kod = os.path.splitext(os.path.basename(ad))[0]
                if kod not in LIGLER:
                    continue
                for r in csv_satirlari(z.read(ad)):
                    m = oku(r, kod, sonuclu=True)
                    if m:
                        maclar[anahtar(m)] = m
    if not maclar:
        print("Hiç maç okunamadı.")
        sys.exit(1)

    # 2) Fikstür arşivi: fixtures.csv her yayında değiştiği için gördüğümüz oranları 30 gün saklarız
    arsiv_yol = os.path.join(a.onbellek, "fikstur_arsiv.json")
    arsiv = {}
    if os.path.exists(arsiv_yol):
        try:
            for m in json.load(open(arsiv_yol, encoding="utf-8")):
                arsiv[anahtar(m)] = m
        except Exception as e:  # noqa
            print(f"  ! arşiv okunamadı: {e}")
    fyol = os.path.join(a.onbellek, "fixtures.csv")
    if os.path.exists(fyol):
        with open(fyol, "rb") as f:
            for r in csv_satirlari(f.read()):
                m = oku(r, None, sonuclu=False)
                if m:
                    arsiv[anahtar(m)] = m
    arsiv = {k: m for k, m in arsiv.items() if m["gun"] >= bugun_no - 30}
    with open(arsiv_yol, "w", encoding="utf-8") as f:
        json.dump(list(arsiv.values()), f, ensure_ascii=False)

    # 3) Aynı gün sonuçlar (football-data.org, isteğe bağlı)
    sonucsuz = [m for k, m in arsiv.items() if k not in maclar and m["gun"] <= bugun_no]
    gecici = {}
    token = os.environ.get("FOOTBALL_DATA_ORG_TOKEN", "").strip()
    if sonucsuz and (token or a.fdorg_dosya):
        bas = min(m["gun"] for m in sonucsuz)
        bas = max(bas, bugun_no - 9) - 1  # football-data.org en fazla 10 günlük aralık kabul ediyor
        org = json.load(open(a.fdorg_dosya, encoding="utf-8")) if a.fdorg_dosya else gecici_sonuclar(token, bas, bugun_no)
        for g, f in eslestir(org, sonucsuz):
            gecici[anahtar(f)] = dict(f, sonuc=[g["ms"][0], g["ms"][1], g["iy"][0], g["iy"][1], None, None])
        print(f"  {len(gecici)} geçici sonuç eşleşti")
    elif sonucsuz:
        print("  FOOTBALL_DATA_ORG_TOKEN yok; aynı gün sonuçlar atlandı")

    # 4) Çıktı
    takim = {}

    def t(ad):
        if ad not in takim:
            takim[ad] = len(takim)
        return takim[ad]

    def satir_sonuclu(m):
        return [LIGLER.index(m["lig"]), m["gun"], m["saat"], t(m["ev"]), t(m["dep"])] + m["sonuc"] + m["oran"]

    def satir_fikstur(m):
        return [LIGLER.index(m["lig"]), m["gun"], m["saat"], t(m["ev"]), t(m["dep"])] + m["oran"]

    sirala = lambda l: sorted(l, key=lambda m: (m["gun"], m["saat"], m["lig"]))  # noqa
    m_liste = [satir_sonuclu(m) for m in sirala(maclar.values())]
    g_liste = [satir_sonuclu(m) for m in sirala(gecici.values())]
    f_liste = [satir_fikstur(m) for m in sirala(m for k, m in arsiv.items()
                                                  if k not in maclar and k not in gecici and m["gun"] >= bugun_no)]
    veri = {
        "olusturma": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kaynak": "football-data.co.uk",
        "lig": LIGLER,
        "takim": [ad for ad, _ in sorted(takim.items(), key=lambda x: x[1])],
        "m": m_liste,
        "g": g_liste,
        "f": f_liste,
        "gecici_kaynak": "football-data.org" if g_liste else None,
    }
    with open(a.cikti, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(m_liste)} maç, {len(g_liste)} geçici sonuç, {len(f_liste)} gelecek maç yazıldı → {a.cikti}")


if __name__ == "__main__":
    main()
