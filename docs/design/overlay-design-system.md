# Dubzar oyun içi panel: tasarım sistemi (Yön B, "sıcak konsol")

Panel, oyunun üstünde kısayolla açılan ve kısa süre kullanılan bir ayar kartıdır. Oyunun dikkatini çalmaz,
sakin ve sıcaktır. Referans alınan ilkeler: Warp'ın sıcak koyu zemini, PlayStation'ın ince yazı ağırlığı,
tek vurgu rengi. Hiçbir markanın kimliği kopyalanmaz.

## İlkeler
1. **Tek vurgu:** Yumuşak altın (`accent`). Yalnızca "açık" durumları, seçili öğeyi ve odak halkasını boyar.
2. **Gölge yok, basamak var:** Derinlik zemin ve yüzey renk farkıyla, ince çizgiyle kurulur.
3. **Hap şekli:** Etkileşimli her kontrol tam yuvarlak (`pill`). Panel kartı 16 px.
4. **İnce yazı:** Gövde 400, vurgu 500. Kalın (600+) kullanılmaz.
5. **Bir imza anı:** İtalik serif yalnızca "Dubzar" yazısında.
6. **Hareket sakin:** Ease-out, kısa süre, sekme veya zıplama yok. Azaltılmış hareket tercihine uyulur.

## Renkler
| Token | Değer | Kullanım |
|---|---|---|
| `bg` | `#2B2622` (%96 opak) | Panel zemini |
| `surface` | `#352F2A` | Mini ekran, tuş, kaydırıcı rayı |
| `hairline` | `#4A423B` | Tüm kenar çizgileri |
| `text` | `#F7F5F0` | Birincil yazı |
| `muted` | `#A89F94` | Etiket, ipucu |
| `accent` | `#F2C14E` | Açık durum, seçim, odak |
| `on-accent` | `#2B2622` | Vurgu üstündeki yazı/yuvarlak |

Kontrast (WCAG, hesaplandı): `text` / `bg` 13,7:1; `muted` / `bg` 5,7:1 (`surface` üstünde 5,1:1);
`accent` / `bg` 8,9:1; `on-accent` / `accent` 8,9:1. Metinler 4,5:1 eşiğinin üstünde.
`hairline` / `bg` yalnızca 1,5:1'dir: bu çizgiler **süstür**. Kontrolün varlığını ve durumunu çizgi değil dolgu
taşır (kapalı anahtarın yuvarlağı `muted`, açık olan `accent`, kaydırıcı tutamacı `accent`).

## Yazı tipleri
- Gövde ve etiket: **DM Sans** 400/500. Etiket 11,5–12 px, gövde 12,5–13 px.
- İmza: **Instrument Serif** italik, 22 px (yalnızca "Dubzar").
- Tuş ve değerler: DM Sans (mono kullanılmaz, yön B'nin yumuşaklığını bozar).
- Türkçe karakterler (ğ ş İ ı ö ü ç) tüm yazı tiplerinde doğrulanmalıdır. Yazı tipleri uygulamayla paketlenir; lisanslar `docs/LICENSES.md`'ye eklenir.

## Boşluk ve şekil
- Boşluk ölçeği: 4, 8, 12, 16. Panel iç boşluğu 16.
- Köşe: panel 16, kontroller hap (yarıçap = yükseklik / 2), mini ekran 10.
- Etkileşim hedefi en az 28 px (görsel küçük olsa da dokunma alanı büyütülür).

## Bileşenler
- **Anahtar (açma/kapama):** 32×18 hap. Açıkken `accent` zemin, `on-accent` yuvarlak sağda. Kapalıyken `surface` zemin, `muted` yuvarlak solda.
- **Tuş etiketi:** `surface` zemin, `hairline` çizgi, hap, `muted` yazı. Kısayolu gösterir.
- **Renk örneği:** 20 px daire, `hairline` çizgi. Seçiliyken 2 px `accent` halka, 2 px boşlukla.
- **Kaydırıcı:** 4 px ray (`surface`), dolu kısım `accent`, 14 px `accent` tutamaç.
- **Konum denetimi:** 58 px yüksekliğinde mini ekran. İçindeki altyazı çubuğu dikey sürüklenir (fare veya yön tuşları).
- **Hayalet düğme** ("Varsayılana dön"): saydam zemin, `hairline` çizgi, hap, `text` yazı.

## Hareket
| Olay | Süre | Eğri |
|---|---|---|
| Panel açılma | 160 ms | ease-out (`0.2, 0.8, 0.2, 1`), 8 px yukarıdan kayma + solma |
| Panel kapanma | 120 ms | ease-out, solma |
| Anahtar | 160 ms | ease-out |
| Düğme basma | 80 ms | `scale(0.97)` |
Windows "animasyonları göster" kapalıysa tüm hareketler anında olur.

## Erişilebilirlik
- Tab sırası yukarıdan aşağıya. `Esc` paneli kapatır. Kaydırıcılar ve konum denetimi yön tuşlarıyla ayarlanır.
- Odak halkası `accent`, 2 px.
- Renk tek başına bilgi taşımaz: açık/kapalı durumu konumdan da anlaşılır.

## Dil (Türkçe)
Cümle düzeni küçük harf, noktalama yok, kısa. Fiille başla ("Varsayılana dön"). "Lütfen", "başarıyla" gibi
dolgu sözcükler yok. Ünlem yok.
