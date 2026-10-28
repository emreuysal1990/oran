# Oran Bülteni

Bahis şirketlerinin oranlarından (1-X-2 ve 2,5 Alt/Üst) marjı çıkarıp bir gol modeli kuran; buradan KG, takım golü, ilk yarı, İY/MS, handikap, birleşik pazarlar, korner ve kart dahil **113 futbol pazarının** ihtimalini ve **adil oranını** hesaplayan sayfa. Bir pazarın yanına kendi oranını (ör. İddaa'daki) yazarsan sayfa modelin adil oranıyla karşılaştırıp **değer** gösterir. NBA için de aynı mantık (maç sonucu, handikap, toplam sayı) çalışır.

> **Adil oran**, modelin ihtimalinin tersidir (1 ÷ ihtimal); hiçbir bahis şirketinin oranı değildir. Model yeni bilgi üretmez, oranlardaki bilgiyi diğer pazarlara dağıtır. Bu sayfa istatistiksel bir araçtır, bahis tavsiyesi değildir.

## Sürümler

| Adres | Ne |
|---|---|
| `/` | **Ana sayfa: eski sürüm (v1)**, "benzer oranlı geçmiş maç" yöntemi ve sinyaller (`v1.html` dosyası) |
| `/v1.html` | Eski sürümün sabit adresi |
| `/v2.html` | **Yeni model sürümü (v2):** oranlardan model, 113 pazar, kendi oranını gir, hesaplayıcı, canlı doğruluk kontrolü (`index.html` dosyası) |

### Ana sayfayı değiştirmek

1. `.github/workflows/guncelle.yml` dosyasındaki `ANA_SAYFA: v1.html` satırı ana adreste hangi sürümün açılacağını belirler. Yeni sürümü ana sayfa yapmak için `ANA_SAYFA: index.html` yazıp kaydedin (Commit changes); birkaç dakika içinde değişir. İki sürüm de her zaman `/v1.html` ve `/v2.html` adreslerinde durur.
2. Eski sürümün **tüm deposu** (kod ve iş akışıyla) ayrıca `v1-yedek` dalında saklıdır.

## Veri (yalnızca yasal kaynaklar)

- [football-data.co.uk](https://www.football-data.co.uk) (ücretsiz): 22 Avrupa ligi (Bet365 oranları, korner, kart, ilk yarı), ayrıca MLS ve İsveç, Norveç, Danimarka, Finlandiya ligleri.
- İsteğe bağlı [The Odds API](https://the-odds-api.com) anahtarı (`THE_ODDS_API_KEY` secret): Şampiyonlar Ligi, Avrupa Ligi, Konferans Ligi, NBA ve ek liglerin güncel oranları. Kupaların ve NBA'in geçmişi, oynanan maçlarla `veri` dalında birikir.
- İsteğe bağlı football-data.org anahtarı (`FOOTBALL_DATA_ORG_TOKEN` secret): 8 büyük ligde aynı gün skorlar.
- Anahtarları yalnızca GitHub'da **Settings → Secrets and variables → Actions** altına siz eklersiniz; kimseyle paylaşmayın.
- GitHub Actions veriyi **her saat** indirmeye çalışır (GitHub bunu geciktirebilir). Sayfadaki **Güncelle** tuşu en son veriyi getirir.
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
- MS ve 2,5 Alt/Üst pazarlarındaki sinyalli 581 bahsin Bet365 oranıyla getirisi −%5,2 (±6,2). Tüm maçlara düz oynanan MS 1 −%7,8, MS X −%5,3, MS 2 −%11,4, 2,5 Üst −%4,1, 2,5 Alt −%7,2 getirdi (en yüksek oran seçilse bile −%1 ile −%7).
- 62 birleşik/ek pazarda (handikap, İY/MS, MS + Alt/Üst, KG + Alt/Üst, toplam gol aralığı, yarı sonuçları) modelin ihtimali ile gerçekleşen oran arasındaki ortalama fark 0,5 puan, en büyük fark 1,5 puan (handikap pazarları).

Ayrıntılar ve yeniden üretme adımları: [`arastirma/README.md`](arastirma/README.md).

## Dosyalar

| Dosya | Ne |
|---|---|
| `index.html`, `v1.html` | Sayfalar (tek dosya; `veri.json`'u okurlar) |
| `guncelle.py` | Veriyi indirir, birleştirir, model değerlerini hesaplayıp `veri.json` üretir |
| `modelkit.py`, `katsayilar.json` | Model çekirdeği (yalnızca numpy) ve eğitilmiş katsayılar |
| `kaynak/` | `index.html`'in kaynakları (`model.js`, `pazarlar.js`, `betik.js`, `stil.css`, `govde.html`); `python3 kaynak/derle.py --repo .` ile derlenir; `node kaynak/parite_test.js` JS modelini Python ile karşılaştırır |
| `arastirma/` | Geriye dönük test betikleri ve sonuç tablosu |
| `.github/workflows/guncelle.yml` | Saatlik güncelleme ve Pages yayını |

## Kurulum (bir kerelik)

1. GitHub'da **New repository** → **Public** → **Create repository**.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions** seçin.
3. Bu depodaki dosyaları ekleyin (özellikle `index.html`, `v1.html`, `guncelle.py`, `modelkit.py`, `katsayilar.json` ve `.github/workflows/guncelle.yml`).
4. **Actions** sekmesinde **Verileri güncelle** iş akışı çalışır (çalışmazsa **Run workflow**). 1–2 dakika sonra sayfa açılır: `https://KULLANICI-ADINIZ.github.io/DEPO-ADI/`
5. iPhone'da Safari ile açıp **Paylaş → Ana Ekrana Ekle** diyebilirsiniz.

## Bilinmesi gerekenler

- Depo herkese açık olduğu için sayfa da bağlantıyı bilen herkese açıktır.
- GitHub, 60 gün hiç işlem görmeyen depolarda zamanlanmış iş akışlarını durdurur ve e-posta atar; e-postadaki bağlantıyla tek tıkla yeniden açılır.
- football-data.co.uk gelecek maçların oranlarını hafta sonu için Cuma, hafta içi için Salı öğleden sonra yayınlar.
- Korner ve kart sayıları, football-data.co.uk sonuçları yayınlayana kadar (aynı gün skor football-data.org'dan gelse bile) eksik olabilir.
