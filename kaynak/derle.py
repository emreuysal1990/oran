# Oran Bülteni v2 derleyici.
#   python3 derle.py --sayfa              -> sayfa.html (ara çıktı)
#   python3 derle.py --repo ..            -> ../index.html (GitHub Pages sayfası, veri.json'u çeker; katsayılar ../katsayilar.json'dan gömülür)
#   python3 derle.py --veri veri.json --onizleme cikti.html -> veri gömülü, tek dosya önizleme
import argparse, json, os
k = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--repo"); ap.add_argument("--veri"); ap.add_argument("--onizleme"); ap.add_argument("--sayfa", action="store_true")
ust = os.path.join(k, os.pardir, "katsayilar.json")
ap.add_argument("--kat", default=ust if os.path.exists(ust) else os.path.join(k, "katsayilar.json"))
a = ap.parse_args()

def oku(ad):
    return open(os.path.join(k, ad), encoding="utf-8-sig").read()

kat = json.dumps(json.load(open(a.kat, encoding="utf-8")), ensure_ascii=False, separators=(",", ":"))
js = "const KAT_YEDEK = " + kat + ";\n" + oku("model.js") + "\n" + oku("pazarlar.js") + "\n" + oku("betik.js")
if "</script" in js.lower():
    raise SystemExit("betikte </script geçmemeli")
bas = ('<title>Oran Bülteni</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
       '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
       '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Public+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">\n')
sayfa = bas + oku("stil.css") + "\n\n" + oku("govde.html") + "<script>\n" + js + "</script>\n"
if a.sayfa:
    open(os.path.join(k, "sayfa.html"), "w", encoding="utf-8").write(sayfa)

i = sayfa.index('<div class="wrap">')
tam = ('<!doctype html>\n<html lang="tr">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       + sayfa[:i] + '</head>\n<body>\n' + sayfa[i:].replace("<!--GOMULU-->\n", "") + '</body>\n</html>\n')
if a.repo:
    open(os.path.join(a.repo, "index.html"), "w", encoding="utf-8").write(tam)
    print("index.html yazıldı:", a.repo, len(tam), "bayt")
if a.onizleme:
    veri = open(a.veri, encoding="utf-8").read().replace("</", "<\\/")
    on = sayfa.replace("<!--GOMULU-->", '<script id="gomulu-veri" type="application/json">' + veri + "</script>")
    open(a.onizleme, "w", encoding="utf-8").write(on)
    print("önizleme yazıldı:", a.onizleme, len(on), "bayt")
