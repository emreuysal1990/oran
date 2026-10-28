# Araştırma: yeni model eski yöntemden daha mı doğru?

Bu klasör, sayfadaki iki yöntemi geriye dönük karşılaştıran betikleri ve sonuç tablosunu içerir.

- **Eski yöntem (v1):** aynı ligde 1-X-2 ve 2,5 Alt/Üst ihtimalleri benzer olan geçmiş maçlara bakar; ± %2,5 içindeki en yakın 10 maç, ± %5 içindeki tüm maçlar, ligin genel oranına 8 maçlık önselle karıştırılır. 4 yakın maçın hepsi tuttuysa "sinyal" verir (`v1.py`).
- **Yeni model (v2):** oranlardan marj çıkarılır, Poisson/Dixon-Coles gol modeli uydurulur; tüm pazarlar bundan hesaplanır. Korner ve kart için ayrı negatif binom modeli (`../modelkit.py`, `model.py`, `genis.py`, `egit.py`).
- **Lig ortalaması:** her maça, o güne kadarki lig oranını aynen veren basit tahmin (`taban.py`).

## Veri

[xgabora/Club-Football-Match-Data-2000-2025](https://github.com/xgabora/Club-Football-Match-Data-2000-2025) deposundaki `Matches.csv` (football-data.co.uk kaynaklı, 3 Eylül 2026'ya kadar). Yalnızca 1 Temmuz 2023 sonrası 22 Avrupa ligi kullanılır; dosyanın yolu `MATCHES_CSV` ortam değişkeniyle verilir.

## Yöntem

- Genişleyen pencere: **Fold A** eğitim 2023-07 → 2024-06, test 2024-07 → 2025-06; **Fold B** eğitim 2023-07 → 2025-06, test 2025-07 → 2026-09. Model her maçı yalnızca kendisinden önceki veriyle eğitilmiş katsayılarla tahmin eder.
- Karşılaştırılan 51 pazar: MS, çifte şans, toplam gol, KG, takım golü, ilk yarı, ikinci yarı, korner, kart. 62 ek pazar (handikap, İY/MS, birleşik, toplam gol aralığı, yarı sonuçları) ayrıca doğruluk (kalibrasyon) açısından kontrol edilir.
- Ölçüt: ortalama log kayıp ve Brier skoru; eşleştirilmiş t-testi; ROI (Bet365 ve en yüksek oran).
- Test: 15.406 maç (22 lig).

## Çalıştırma sırası

```
export MATCHES_CSV=/yol/Matches.csv
python3 hazir.py          # veri, marj temizleme, λ uydurma  -> cache.pkl
python3 run_v1.py         # v1 yöntemi                      -> v1_sonuc.pkl
python3 taban.py          # lig ortalaması                  -> taban.pkl
python3 degerlendir3.py   # iki fold, yeni model + tablo    -> degerlendirme_tablosu.csv
python3 t_sinyal.py       # v1 "sinyal"lerinin isabeti
python3 t_roi.py          # düz bahis ve sinyal ROI'si
python3 t_genis.py        # 62 ek pazarın doğruluğu
python3 t_esik.py         # eski sinyaller ve yeni modelin ihtimal eşikleri (isabet)
python3 t_guclu.py        # eski sinyalleri tahmini ihtimal / model ihtimaliyle süzme
python3 egit.py son ../katsayilar.json   # üretim katsayıları (tüm veriyle)
python3 parite_uret.py    # ../kaynak/parite.json (JS model testi için)
```

(`pandas`, `numpy`, `scipy`, `scikit-learn` gerekir.)

## Sonuçlar

`degerlendirme_tablosu.csv` her pazar için: test maçı sayısı, gerçekleşme oranı, lig ortalaması / v1 / yeni modelin log kaybı, kazançlar, t değeri ve Brier skorları. Özet için ana [README](../README.md).

## Sınırlar

- Yeni model oranlardan türetildiği için "bahis şirketini yener mi?" sorusunu **cevaplamaz**; yalnızca oranlardaki bilgiyi ne kadar iyi dağıttığını ölçer. Tüm maçlara düz oynanan bahisler test döneminde −%4 ile −%11 arasında kaybettirdi.
- Oranlar Bet365'in (maça yakın) oranlarıdır; İddaa'nın oranları ve marjları farklıdır.
- Korner/kart katsayıları tüm veriyle eğitildiği için sayfadaki "Canlı kontrol" tablosunda bu gruplar biraz iyimser görünebilir; bu klasördeki değerlendirme ise yukarıdaki genişleyen pencereyle yapılır.
- İlk yarı payı (%44,5) ve tek/çift (%50) sabit varsayımlardır.
