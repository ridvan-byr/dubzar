# Dubzar logosu

**Fikir:** "D" harfinin içindeki boşluk bir zar noktası. Tek şekil hem **D**ublajı hem **zar**ı (oyunu) anlatır.
Logo açılışta büyük D belirir, "ubzar" harfleri D'nin yuvarlak silüetinin arkasından sağa kayarak açılır.

## Dosyalar (`assets/logo/`)
| Dosya | Ne için |
|---|---|
| `dubzar-mark.svg` | Yalnızca D-zar işareti (dolu amber, şeffaf zar noktası). Küçük boyut, simge. |
| `dubzar-badge.svg` | Amber köşeli yuvarlak üzerinde grafit D. Uygulama ikonu. |
| `dubzar-reveal.svg` | Animasyonlu açılış logosu (tarayıcıda oynar). `prefers-reduced-motion` ile animasyonsuz. |
| `dubzar-reveal-final.svg` | Açılışın son kare hâli (D + "ubzar"), kenar boşluklu. |
| `dubzar-lockup.svg`, `dubzar-wordmark-*.svg` | Eski denemeler: işaret + yazı ve ince çizgili D. Kullanılmıyor, referans olarak duruyor. |
| `build_logo.py` | Hepsini üretir: `python assets/logo/build_logo.py`. Yazı, Instrument Serif Italic'ten eğriye çevrilir. |

Uygulamanın içinde kullanılanlar `dubzar/ui/` altına üretilir: `dubzar-logo.svg` (kenar boşluksuz, panel başlığı),
`dubzar-logo-d.svg` ve `dubzar-logo-word.svg` (aynı viewBox'lı iki katman, açılış animasyonu için), `dubzar.ico` (Windows ikonu: 16, 24, 32, 48, 64, 128, 256 piksel).

## Açılış animasyonu uygulamada
`dubzar/ui/Intro.qml` + `intro.py`. Qt'de SVG kırpma ve CSS animasyonu yok; aynı görüntü şöyle elde edilir: harfler,
D'nin zar noktasının sağından başlayan bir dikdörtgenle kırpılır ve D harflerin **üstüne** çizilir. D opak olduğu için
harfler yalnızca D'nin yuvarlak silüetinin dışında görünür (tarayıcıdaki SVG kırpmasıyla aynı sonuç).
Windows'ta animasyonlar kapalıysa son hâl hemen gösterilir, sonra pencere kaybolur.

## Ayarlar (elle ayarlandı)
D yüksekliğinin yaklaşık yarısı kadar küçük harfler (170 px, D = 264 birim), aralık 1, yazı D'nin tabanından 6 birim yukarıda.
Animasyon: D 360 ms (büyüyerek belirir), harfler 520 ms sonra 720 ms içinde açılır ve D ortadan yerine süzülür.
Eğri `cubic-bezier(.2, .8, .2, 1)`. Değerler `build_logo.py` başındaki `TEXT_*` sabitlerinde.

## Kullanım
- Renkler: amber `#FFB224`, grafit `#0E0F11`, krem `#F7F5F0`. Yalnızca bu üçü.
- İşaret en küçük 16 piksel; 16 pikselde bile "D içinde nokta" okunur (ölçüldü).
- Logoyu çevirme, gölge, kontur veya gradyan eklemeyin. D'nin oranını ve içindeki noktayı değiştirmeyin.
- Açık zeminde işaret grafit değil, amber kalır; yazı krem yerine grafit olur (henüz üretilmedi, yapılacaklar listesinde).

## Lisans notu
Yazı eğrileri Instrument Serif (SIL OFL 1.1) glifleridir. OFL, yazı tipinden türetilen çizimlerin kullanılmasına izin verir;
yazı tipi dosyası ürünle dağıtılmaz sayılsa bile `docs/LICENSES.md` kaydı korunur.
