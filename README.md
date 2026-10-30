# Oran Bülteni

Bahis şirketlerinin oranlarından (1-X-2 ve 2,5 Alt/Üst) marjı çıkarıp bir gol modeli kuran; buradan KG, takım golü, ilk yarı, İY/MS, handikap, birleşik pazarlar, korner ve kart dahil **113 futbol pazarının** ihtimalini ve **adil oranını** hesaplayan sayfa. Bir pazarın yanına kendi oranını (ör. İddaa'daki) yazarsan sayfa modelin adil oranıyla karşılaştırıp **değer** gösterir. NBA için de aynı mantık (maç sonucu, handikap, toplam sayı) çalışır.

> **Adil oran**, modelin ihtimalinin tersidir (1 ÷ ihtimal); hiçbir bahis şirketinin oranı değildir. Model yeni bilgi üretmez, oranlardaki bilgiyi diğer pazarlara dağıtır. Bu sayfa istatistiksel bir araçtır, bahis tavsiyesi değildir.

## Sürümler

| Adres | Ne |
|---|---|
| `/` | **Ana sayfa: yeni tasarım (v3, `v3.html`).** Öneriler, Maçlar, Geçmiş, Performans. Öneri formülü aşağıda; adil oranı 1,20'nin altındaki hiçbir sonuç önerilmez. Maça dokununca tüm pazarlar, oranları en çok benzeyen 10 maç ve İddaa oranını yazıp değer hesaplama. |
| `/v1.html` | Eski sinyal sayfası: "benzer oranlı geçmiş maç" sinyalleri (10 maçta 10), sinyal için en az tahmini ihtimal ayarı, "3 benzer maç" yöntem sekmesi |
| `/v2.html` | Model sayfası (`index.html` dosyası): 113 pazar, hesaplayıcı, canlı doğruluk kontrolü |

### Ana sayfayı değiştirmek

1. `.github/workflows/guncelle.yml` dosyasındaki `ANA_SAYFA: v3.html` satırı ana adreste hangi sürümün açılacağını belirler (`v1.html`, `index.html` ya da `v3.html`). Değiştirip kaydedin (Commit changes); birkaç dakika içinde değişir. Üç sürüm de her zaman kendi adresinde durur.
2. Eski sürümün **tüm deposu** (kod ve iş akışıyla) ayrıca `v1-yedek` dalında saklıdır.

## Öneri formülü (`oneri.py`)

1. **İhtimal:** maçın oranlarından marj çıkarılır, gol modeli kurulur (Poisson / Dixon-Coles); 51 pazarın ihtimali bundan hesaplanır. Korner ve kart için negatif binom.
2. **Destek:** oranları en çok benzeyen 10 geçmiş maçın (aynı lig, marjsız 1-X-2 ve 2,5 Üst ±2,5 puan) en az 9'unda o pazar tuttuysa öneri "destekli" sayılır, beklenen tutmaya 1 puan eklenir.
3. **Öneri:** gösterilen ihtimal sayfada seçilen sınırın üstünde ve oran en az 1,20. Oran sınırı varsayılan olarak **tahmini İddaa oranına** uygulanır (Ayarlar'dan adil orana çevrilebilir).
4. **Tahmini İddaa oranı** = adil oran ÷ 1,19. İddaa'nın marjı, örnek maçlarda MS, 2,5 Alt/Üst ve KG pazarlarının hepsinde %18-19 çıktı. Gerçek İddaa oranı değildir; gerçek oranı maç ayrıntısına yazınca değer hesaplanır.

**Günün tahminleri** (sabit 5 yerine, sistemin güvendiği kadar): her maçta tahmini İddaa oranı seçilen eşiğin (1,20 / 1,30 / 1,40 / 1,50) üstünde kalan pazarlar arasından beklenen tutması en yüksek olan alınır; beklenen tutması o oranın izin verdiği en yüksek ihtimale yakınsa (güven payı içinde) listeye girer. O gün kaç maç bu şartı sağlıyorsa o kadar tahmin çıkar; hiçbiri sağlamıyorsa o gün tahmin yoktur. Sayfada son 14 gün sonuçlarıyla, gelecek günler maç öncesi görünür.

Güven seviyeleri: **Yüksek** (en yüksek ihtimale 0,5 puan kadar yakın), **Orta** (2 puan), **Geniş** (4 puan; ihtimal hiçbir zaman %55'in altına inmez). Aynı kural 2024-25'ten beri her gün uygulandığında (734 gün, her maç yalnızca kendinden önceki bilgiyle):

| İddaa eşiği | Güven | Günde tahmin | Tuttu (beklenen) | Boş gün | Model eğitiminden sonra |
|---|---|---|---|---|---|
| 1,20 | Yüksek | 10,3 | %70,8 (%69,7) | %12 | günde 10,1 · %67,0 |
| 1,30 | Yüksek | 8,5 | %64,6 (%64,3) | %16 | günde 9,0 · %64,6 |
| 1,30 | Orta | 21,0 | %63,8 (%63,8) | %4 | günde 23,3 · %64,2 |
| 1,30 | Geniş | 26,6 | %63,6 (%63,4) | %1 | günde 29,6 · %64,0 |
| 1,40 | Yüksek | 7,5 | %60,0 (%59,8) | %17 | günde 8,8 · %59,7 |
| 1,50 | Yüksek | 7,4 | %56,1 (%55,8) | %19 | günde 9,1 · %56,6 |

Bir tahmine duyulan güven, oranının izin verdiğinden fazla olamaz (tahmini İddaa 1,30 ≈ en çok %65). Bu yüzden tahmin sayısı gün gün değişir ama her tahmin yaklaşık beklenen oranda tutar. Tahminleri tek tek değerlendirmek kupondan çok daha az risklidir: 1,30'luk tahminlerden 5'inin birden tutma ihtimali yaklaşık %11'dir. İddaa'nın %19 marjı yüzünden tahmini oranlarla oynanan her bahis ve kupon uzun vadede kaybettirir (`arastirma/f_guven.py`).

**Oranlardan bağımsız formüller de denendi** (`arastirma/f_bagimsiz_*.py`, `arastirma/f_g5_varyant.py`; iki sezon ayrı ayrı):
- Yalnız istatistik (kendi Elo, clubelo, son 8 maç ve iç saha/deplasman formu: gol, isabetli şut, şut, korner, kart, puan; dinlenme günü; lig seviyesi) ile makine öğrenmesi (gradient boosting): 51 pazarın 51'inde oranlardan daha kötü (log kayıp %1,4 kötü).
- İstatistik + oran birlikte: yine 51 pazarın 51'inde yalnız orandan kötü (%0,65).
- İstatistik modelinin oranlardan yüksek dediği tahminler oranın söylediğinden yaklaşık 1 puan daha sık tuttu (iki sezonda da); küçük ama tutarlı. Bet365 oranlarına karşı hiçbir model kazandırmadı (−%4 ile −%11).
- Günlük seçim için yaklaşık 20 varyant (destek payı, yalnız destekli, istatistik onayı, pazar türü sınırlaması, makine öğrenmesiyle sıralama) denendi; en iyisi mevcut kural: iki sezonda tahminlerin %66,7'si tuttu (ihtimal %64,2), günde 5'te 3,3.

Varsayılan ayarla (ihtimal en az %60, tahmini İddaa oranı en az 1,20; yani ihtimal %60-70): 2024-25'ten beri 127.056 öneri, %65,3 tuttu (model %65,2); eğitimden sonraki maçlarda %65,2. Bu aralıkta destekli öneriler modelden 2 puan daha sık tuttu.

Öneriler ve geçmiş performans her güncellemede `guncelle.py` içinde hesaplanır ve `veri.json`'daki `oneri` bölümüne yazılır.

**Geriye dönük sonuç** (2024-25'ten beri, her maç yalnızca kendinden önceki bilgiyle; ihtimal en az %70, adil oran en az 1,20): 175.765 öneri, %76,0 tuttu (model %75,8 demişti); destekliler %77,5. Model katsayıları belirlendikten sonra oynanan maçlarda (formülün hiç görmediği maçlar): 14.106 öneri, %76,3 (model %76,2). İhtimal %80+ seçilince %81,8.

**Denenip elenenler** (`arastirma/f_*.py`, 22 Avrupa ligi, iki sezon ayrı ayrı):
- Takım formu (son 8 maçta gol, isabetli şut, şut, korner, kart, puan) eklemek tahminleri %0,2 kötüleştirdi; tek bir "isabetli şut farkı" göstergesi de etkisiz kaldı (+%0,01). Bu bilgiler oranlarda zaten var.
- "En yakın 3 maçta ortak sonuç", benzer maç sayısını 2-10 arasında değiştirmek ve lig sırası benzerliği ihtimalin üstüne bir şey katmadı.
- Hiçbir pazar türü yüksek ihtimal aralığında düzenli olarak daha sık tutmadı (hepsi ±1 puan içinde).
- Hiçbir formül oranların kendisinden daha iyi tahmin etmedi: tutma şansını sonucun ihtimali belirler; kazanç ancak İddaa oranı adil orandan yüksek olduğunda mümkündür.

## Veri (yalnızca yasal kaynaklar)

- [football-data.co.uk](https://www.football-data.co.uk) (ücretsiz): 22 Avrupa ligi (Bet365 oranları, korner, kart, ilk yarı), ayrıca MLS, Brezilya Série A ve İsveç, Norveç, Danimarka, Finlandiya ligleri (bu ek liglerde yalnızca skor ve maç sonucu oranı var).
- İsteğe bağlı [The Odds API](https://the-odds-api.com) anahtarı (`THE_ODDS_API_KEY` secret): Şampiyonlar Ligi, Avrupa Ligi, Konferans Ligi, NBA ve ek liglerin güncel oranları. Kupaların ve NBA'in geçmişi, oynanan maçlarla `veri` dalında birikir.
- İsteğe bağlı football-data.org anahtarı (`FOOTBALL_DATA_ORG_TOKEN` secret): Premier Lig, Championship, Bundesliga, Serie A, La Liga, Ligue 1, Eredivisie, Portekiz ve Brezilya Série A'da **aynı gün skor** (football-data.co.uk sonuçları 1-4 gün sonra ekler). Ücretsiz: [football-data.org](https://www.football-data.org/client/register) adresinden kayıt olunca e-postayla gelen anahtar `FOOTBALL_DATA_ORG_TOKEN` adıyla eklenir. Sayfanın üstündeki "Aynı gün skor" satırı anahtarın çalışıp çalışmadığını gösterir.
- Anahtarları yalnızca GitHub'da **Settings → Secrets and variables → Actions** altına siz eklersiniz; kimseyle paylaşmayın.
- GitHub Actions veriyi **15 dakikada bir** kontrol eder (GitHub zamanlanmış çalışmaları yoğun saatlerde geciktirebilir ya da atlayabilir). Kaynakta değişmeyen dosyalar yeniden indirilmez. Sayfadaki **Güncelle** tuşu en son veriyi getirir.
- Oynanmış ama sonucu kaynağa henüz eklenmemiş maçlar (son 7 gün) "Geçmiş maçlar"da **"sonuç bekleniyor"** etiketiyle, maç öncesi analizleriyle görünür; sonuç gelince kendiliğinden tamamlanır.
- Sayfa son 4 sezonu kullanır (şu an 1 Temmuz 2023'ten itibaren, yani 2023/24 sezonundan); daha eski veri kullanılmaz. Model katsayıları da 1 Temmuz 2023 sonrası veriyle eğitilmiştir.

## Model

1. Her maçın 1-X-2 ve 2,5 Alt/Üst oranlarından marj çıkarılır (güç yöntemi).
2. Bu ihtimallere uyan beklenen ev ve deplasman golü bulunur; skorlar Poisson dağılımı + Dixon-Coles düzeltmesiyle (ρ = −0,04) modellenir. 2 ve üzeri fark skorlarına hafif bir ağırlık (κ = 0,90) verilir.
3. Tüm gol temelli pazarlar (KG, takım golü, handikap, birleşik pazarlar, toplam gol aralığı, İY/MS, ilk yarı) bu skor dağılımından hesaplanır. İlk yarı için gollerin yaklaşık %44,5'inin ilk yarıda atıldığı varsayılır.
4. Korner ve kart: negatif binom dağılımı; takımların son 20 maçtaki attığı/yediği sayılar, ligin son 400 maçtaki seviyesi ve beklenen gol kullanılır. MLS, İskandinav ligleri ve kupalar için korner/kart modeli yoktur.
5. NBA: oranlardan maç sonucu, çizgiden toplam sayı; fark ve takım sayıları normal dağılımla (fark için σ = 13, toplam için σ = 18) modellenir.

Katsayılar `katsayilar.json` dosyasındadır; `arastirma/egit.py son ../katsayilar.json` ile yeniden üretilir.

## Geriye dönük test (özet)

Temmuz 2024 – Eylül 2026 arasında oynanan **15.406 maç** (22 Avrupa ligi). Model her test döneminde yalnızca o tarihten önceki veriyle eğitildi (genişleyen pencere); her maç yalnızca kendi oranlarıyla tahmin edildi. Ortalama log kayıp (küçük = daha iyi):

| Pazar grubu | Pazar | Lig ortalaması | Eski yöntem (v1) | Yeni model |
|---|---:|---:|---:|---:|
| Maç sonucu | 6 | 0,6252 | 0,5989 | **0,5846** |
| Toplam gol | 8 | 0,5604 | 0,5601 | **0,5491** |
| Karşılıklı gol | 2 | 0,6904 | 0,6945 | **0,6862** |
| Takım golü | 10 | 0,5828 | 0,5640 | **0,5524** |
| İlk yarı | 8 | 0,6089 | 0,6073 | **0,5976** |
| İkinci yarı | 2 | 0,6029 | 0,6068 | **0,5975** |
| Korner | 8 | 0,6515 | 0,6564 | **0,6465** |
| Kart | 7 | 0,6156 | 0,6177 | **0,6066** |
| **Hepsi** | **51** | 0,6087 | 0,6029 | **0,5920** |

- Yeni model 51 pazarın 51'inde hem eski yöntemden hem lig ortalamasından daha doğru. Eski yöntem 51 pazarın yalnızca 20'sinde lig ortalamasını geçebildi.
- Eski yöntemin "sinyal" verdiği 25.586 maç-pazar çiftinin %78,2'si tuttu (eski yöntem %80,5 bekliyordu); yeni modelin aynı çiftler için ortalama ihtimali %77,5. Yani sinyaller, oranların zaten söylediğinin üstüne yalnızca 0,7 puan ekliyor.
- **Sinyalleri süzmek:** en yakın maçların hepsi tutsa bile "Tahmini ihtimal" düşükse sinyal zayıf. Tahmini ihtimali %60'ın altındaki sinyallerin %50'si, %80 ve üzerindekilerin %84'ü, %85 ve üzerindekilerin %86'sı, %90 ve üzerindekilerin %89'u tuttu (maç başına sırasıyla 0,96 / 0,62 / 0,28 sinyal). Bu yüzden eski sayfada sinyal için varsayılan sınır %80'dir (`arastirma/t_guclu.py`).
- **"3 benzer maç" (ortak sonuç) yöntemi:** en yakın 3 maçın hepsinde aynı olan sonuçlar, adil oranı 1,50 ve üzeri olanlarda %50,9 tuttu; gol modeli bunlara ortalama %50,5 ihtimal vermişti (her adil oran aralığında fark 1-2 puan içinde). Benzer maç sayısını 2-10 arasında değiştirmek ya da lig sırasını benzerliğe katmak bunu değiştirmedi. Yani tahminin tutma şansı sonucun ihtimalidir; sekmede bu yüzden her tahminin model ihtimali ve adil oranı gösterilir (`arastirma/uc_deney.py`, `arastirma/uc_model.py`).
- MS ve 2,5 Alt/Üst pazarlarındaki sinyalli 581 bahsin Bet365 oranıyla getirisi −%5,2 (±6,2). Tüm maçlara düz oynanan MS 1 −%7,8, MS X −%5,3, MS 2 −%11,4, 2,5 Üst −%4,1, 2,5 Alt −%7,2 getirdi (en yüksek oran seçilse bile −%1 ile −%7).
- 62 birleşik/ek pazarda (handikap, İY/MS, MS + Alt/Üst, KG + Alt/Üst, toplam gol aralığı, yarı sonuçları) modelin ihtimali ile gerçekleşen oran arasındaki ortalama fark 0,5 puan, en büyük fark 1,5 puan (handikap pazarları).

Ayrıntılar ve yeniden üretme adımları: [`arastirma/README.md`](arastirma/README.md).

## Dosyalar

| Dosya | Ne |
|---|---|
| `v3.html`, `v1.html`, `index.html` | Sayfalar (tek dosya; `veri.json`'u okurlar). `v3.html` yeni tasarım, `index.html` v2 (kaynağı `kaynak/`) |
| `oneri.py` | Öneri formülü: 51 pazarın ihtimali, benzer maç desteği, öneriler ve geçmiş performans |
| `guncelle.py` | Veriyi indirir, birleştirir, model değerlerini hesaplayıp `veri.json` üretir |
| `modelkit.py`, `katsayilar.json` | Model çekirdeği (yalnızca numpy) ve eğitilmiş katsayılar |
| `kaynak/` | `index.html`'in kaynakları (`model.js`, `pazarlar.js`, `betik.js`, `stil.css`, `govde.html`); `python3 kaynak/derle.py --repo .` ile derlenir; `node kaynak/parite_test.js` JS modelini Python ile karşılaştırır |
| `arastirma/` | Geriye dönük test betikleri ve sonuç tablosu |
| `.github/workflows/guncelle.yml` | Saatlik güncelleme ve Pages yayını |

## Kurulum (bir kerelik)

1. GitHub'da **New repository** → **Public** → **Create repository**.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions** seçin.
3. Bu depodaki dosyaları ekleyin (özellikle `v3.html`, `v1.html`, `index.html`, `guncelle.py`, `modelkit.py`, `oneri.py`, `katsayilar.json` ve `.github/workflows/guncelle.yml`).
4. **Actions** sekmesinde **Verileri güncelle** iş akışı çalışır (çalışmazsa **Run workflow**). 1–2 dakika sonra sayfa açılır: `https://KULLANICI-ADINIZ.github.io/DEPO-ADI/`
5. iPhone'da Safari ile açıp **Paylaş → Ana Ekrana Ekle** diyebilirsiniz.

## Bilinmesi gerekenler

- Depo herkese açık olduğu için sayfa da bağlantıyı bilen herkese açıktır.
- GitHub, 60 gün hiç işlem görmeyen depolarda zamanlanmış iş akışlarını durdurur ve e-posta atar; e-postadaki bağlantıyla tek tıkla yeniden açılır.
- football-data.co.uk gelecek maçların oranlarını hafta sonu için Cuma, hafta içi için Salı öğleden sonra (Türkiye saatiyle genelde 16:00-20:00) yayınlar; o saate kadar "Gelecek maçlar" boş görünebilir. Ek liglerin (MLS, Brezilya, İskandinav) fikstürü daha sık yayınlanır.
- Zamanlanmış çalışmalar yine de seyrek kalırsa, ücretsiz [cron-job.org](https://cron-job.org) ile iş akışı dışarıdan tetiklenebilir (GitHub'da yalnızca bu depoya "Actions: Read and write" izni olan bir fine-grained token gerekir; tokenı kimseyle paylaşmayın).
- Korner ve kart sayıları, football-data.co.uk sonuçları yayınlayana kadar (aynı gün skor football-data.org'dan gelse bile) eksik olabilir.
