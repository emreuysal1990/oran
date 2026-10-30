#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
football-data.co.uk verilerini indirip sayfanın okuduğu veri.json dosyasını üretir.
GitHub Actions bunu her 4 saatte bir çalıştırır; elle çalıştırmak gerekmez.

  python3 guncelle.py --onbellek onbellek --cikti _site/veri.json
"""
import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timezone

KAYNAK = "https://www.football-data.co.uk"
LIGLER = ["E0", "E1", "E2", "E3", "EC", "SC0", "SC1", "SC2", "SC3", "D1", "D2", "I1", "I2",
          "SP1", "SP2", "F1", "F2", "N1", "B1", "P1", "T1", "G1"]
MS_KAYNAKLARI = [("B365H", "B365D", "B365A"), ("AvgH", "AvgD", "AvgA"), ("PSH", "PSD", "PSA"),
                 ("MaxH", "MaxD", "MaxA"), ("BbAvH", "BbAvD", "BbAvA")]
AU_KAYNAKLARI = [("B365>2.5", "B365<2.5"), ("Avg>2.5", "Avg<2.5"), ("P>2.5", "P<2.5"),
                 ("Max>2.5", "Max<2.5"), ("BbAv>2.5", "BbAv<2.5")]
EPOCH = date(1970, 1, 1)


def sezon_kodlari(n_gecmis, bugun):
    y = bugun.year if bugun.month >= 7 else bugun.year - 1
    return [f"{(y - k) % 100:02d}{(y - k + 1) % 100:02d}" for k in range(n_gecmis, -1, -1)]


def indir(url, hedef, zorla):
    if os.path.exists(hedef) and not zorla:
        return True
    for deneme in range(3):
        try:
            istek = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (benzer-oran-bulteni; github actions)"})
            with urllib.request.urlopen(istek, timeout=90) as yanit:
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


def kayit(r, varsayilan_lig, takim, sonuclu):
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
    for ad in (ev, dep):
        if ad not in takim:
            takim[ad] = len(takim)
    temel = [LIGLER.index(lig), (t - EPOCH).days, (r.get("Time") or "").strip()[:5], takim[ev], takim[dep]]
    if not sonuclu:
        return temel + ms + au
    fh, fa = sayi(r.get("FTHG") or r.get("HG")), sayi(r.get("FTAG") or r.get("AG"))
    if fh is None or fa is None:
        return None
    hh, ha = sayi(r.get("HTHG")), sayi(r.get("HTAG"))
    hc, ac = sayi(r.get("HC")), sayi(r.get("AC"))
    kart = [sayi(r.get(k)) for k in ("HY", "AY", "HR", "AR")]
    return temel + [int(fh), int(fa),
                    None if hh is None or ha is None else int(hh), None if hh is None or ha is None else int(ha),
                    None if hc is None or ac is None else int(hc + ac),
                    None if any(k is None for k in kart) else int(sum(kart))] + ms + au


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onbellek", default="onbellek")
    ap.add_argument("--cikti", default="_site/veri.json")
    ap.add_argument("--sezon", type=int, default=3)
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.onbellek, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.cikti)), exist_ok=True)

    kodlar = sezon_kodlari(a.sezon, date.today())
    if not a.offline:
        for i, k in enumerate(kodlar):
            indir(f"{KAYNAK}/mmz4281/{k}/data.zip", os.path.join(a.onbellek, f"{k}.zip"), zorla=(i == len(kodlar) - 1))
        indir(f"{KAYNAK}/fixtures.csv", os.path.join(a.onbellek, "fixtures.csv"), zorla=True)

    takim, maclar = {}, {}
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
                    m = kayit(r, kod, takim, sonuclu=True)
                    if m:
                        maclar[(m[0], m[1], m[3], m[4])] = m
    fikstur = []
    fyol = os.path.join(a.onbellek, "fixtures.csv")
    if os.path.exists(fyol):
        with open(fyol, "rb") as f:
            for r in csv_satirlari(f.read()):
                m = kayit(r, None, takim, sonuclu=False)
                if m and (m[0], m[1], m[3], m[4]) not in maclar:
                    fikstur.append(m)
    if not maclar:
        print("Hiç maç okunamadı.")
        sys.exit(1)

    m_liste = sorted(maclar.values(), key=lambda m: (m[1], m[2], m[0]))
    veri = {
        "olusturma": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kaynak": "football-data.co.uk",
        "lig": LIGLER,
        "takim": [ad for ad, _ in sorted(takim.items(), key=lambda x: x[1])],
        "m": m_liste,
        "f": sorted(fikstur, key=lambda m: (m[1], m[2], m[0])),
    }
    with open(a.cikti, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(m_liste)} maç, {len(fikstur)} fikstür yazıldı → {a.cikti}")


if __name__ == "__main__":
    main()
