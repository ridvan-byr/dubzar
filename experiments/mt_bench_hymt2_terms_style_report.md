# Opus-MT ile Hy-MT2-1.8B (terms+style): 120 satırlık kıyas

chrF ortalaması: Opus-MT **66.7**, Hy-MT2-1.8B (terms+style) **62.4**

Satır başına süre (sıcak): Opus-MT 104 ms, Hy-MT2-1.8B (terms+style) 661 ms (cuda)

| Tür | satır | Opus-MT | Hy-MT2-1.8B (terms+style) |
|---|---|---|---|
| konusma | 25 | 86.3 | 74.0 |
| argo | 20 | 53.0 | 49.9 |
| gorev | 20 | 70.5 | 67.5 |
| arayuz | 15 | 58.7 | 59.8 |
| resmi | 15 | 64.0 | 59.9 |
| kisa | 15 | 52.6 | 52.4 |
| ocr | 10 | 75.0 | 70.8 |

Hy-MT2-1.8B (terms+style), Opus-MT'den 5+ puan iyi: 37 satır; 5+ puan kötü: 52 satır; geri kalan 31 yakın.

## Tüm satırlar

| tür | İngilizce | Opus-MT | Hy-MT2-1.8B (terms+style) | referans |
|---|---|---|---|---|
| konusma | I thought you were coming with us tonight. | Bu gece bizimle geleceğini sanıyordum. (100) | Bu akşam bizimle geleceğini sanmıştım. (59) | Bu gece bizimle geleceğini sanıyordum. |
| konusma | Don't worry about it, I'll take care of everything. | Merak etme, her şeyi halledeceğim. (60) | Bu konuda endişelenme, her şeyi ben hallederim. (59) | Boşver, her şeyi ben halledeceğim. |
| konusma | Did you really think I wouldn't find out? | Gerçekten öğrenmeyeceğimi mi sandın? (83) | Bunu fark etmeyeceğimi gerçekten düşündün mü? (49) | Öğrenmeyeceğimi mi sandın gerçekten? |
| konusma | We've been waiting for you for over an hour. | Bir saattir seni bekliyoruz. (50) | Bir saatten fazla bekledik seni. (49) | Seni bir saatten fazladır bekliyoruz. |
| konusma | I'm sorry, I didn't mean to scare you. | Özür dilerim, seni korkutmak istememiştim. (100) | Üzgünüm, seni korkutmak istemedim. (59) | Özür dilerim, seni korkutmak istememiştim. |
| konusma | How long has he been like this? | Ne zamandır böyle? (100) | Ne kadar zamandır böyle? (82) | Ne zamandır böyle? |
| konusma | That's not what he told me yesterday. | Dün bana söylediği bu değildi. (100) | Dün bana söylediği bu değil. (89) | Dün bana söylediği bu değildi. |
| konusma | You should get some rest, you look terrible. | Biraz dinlenmelisin, berbat görünüyorsun. (100) | Biraz dinlenmelisin, çok kötü görünüyorsun. (76) | Biraz dinlenmelisin, berbat görünüyorsun. |
| konusma | Let me guess, he forgot to mention that part. | Dur tahmin edeyim, o kısmı söylemeyi unutmuş. (87) | Tahmin edeyim, o kısmı söylemeyi unuttu. (100) | Tahmin edeyim, o kısmı söylemeyi unuttu. |
| konusma | I can't believe she actually said yes. | Gerçekten evet dediğine inanamıyorum. (88) | Evet dediğine inanamıyorum. (100) | Evet dediğine inanamıyorum. |
| konusma | Where did you get that from? | Bunu nereden buldun? (100) | Bunu nereden aldın? (61) | Bunu nereden buldun? |
| konusma | If it were up to me, we'd leave right now. | Eğer bana kalsaydı, hemen şimdi giderdik. (54) | Eğer benim kararım olsaydı, hemen gidiyorduk. (27) | Bana kalsa, hemen şimdi çıkardık. |
| konusma | I've never seen anything like it in my life. | Hayatımda hiç böyle bir şey görmedim. (88) | Hayatımda böyle bir şeyi hiç görmedim. (87) | Hayatımda böyle bir şey görmedim. |
| konusma | Just give me a minute to think. | Düşünmem için bana bir dakika ver. (100) | Biraz düşünmem için bana bir dakika ver. (93) | Düşünmem için bana bir dakika ver. |
| konusma | He's been acting strange ever since the accident. | Kazadan beri garip davranıyor. (69) | Kazadan beri tuhaf davranıyor. (100) | Kazadan beri tuhaf davranıyor. |
| konusma | What are you doing here so late? | Bu saatte burada ne işin var? (42) | Bu kadar geçte ne yapıyorsun? (60) | Bu kadar geç saatte burada ne yapıyorsun? |
| konusma | You promised you'd be back by midnight. | Gece yarısına kadar döneceğine söz vermiştin. (100) | Gece yarısına kadar geri geleceğine söz verdin. (70) | Gece yarısına kadar döneceğine söz vermiştin. |
| konusma | I don't care what they say, I trust you. | Ne dedikleri umurumda değil, sana güveniyorum. (54) | Onların ne dediğine aldırmıyorum, sana güveniyorum. (50) | Ne derlerse desinler, sana güveniyorum. |
| konusma | It's not as bad as it looks. | Göründüğü kadar kötü değil. (100) | Göründüğü kadar kötü değil. (100) | Göründüğü kadar kötü değil. |
| konusma | Who else knows about this place? | Bu yeri başka kim biliyor? (100) | Bu yere kim daha iyi biliyor? (47) | Bu yeri başka kim biliyor? |
| konusma | I owe you an apology, and an explanation. | Sana bir özür ve bir açıklama borçluyum. (100) | Sana bir özür ve bir açıklama borçluyum. (100) | Sana bir özür ve bir açıklama borçluyum. |
| konusma | We'll talk about this later, okay? | Bunu sonra konuşuruz, tamam mı? (100) | Bunu daha sonra konuşuruz, tamam mı? (87) | Bunu sonra konuşuruz, tamam mı? |
| konusma | She left without saying a word. | Tek kelime etmeden gitti. (100) | Bir kelime bile söylemeden gitti. (58) | Tek kelime etmeden gitti. |
| konusma | Was that really necessary? | Bu gerçekten gerekli miydi? (100) | Bu gerçekten gerekli miydi? (100) | Bu gerçekten gerekli miydi? |
| konusma | I'm starting to think this was a mistake. | Bunun bir hata olduğunu düşünmeye başladım. (84) | Bu bir hata olduğunu düşünmeye başlıyorum. (89) | Bunun bir hata olduğunu düşünmeye başlıyorum. |
| argo | Get your ass over here, now! | Hemen buraya gel! (100) | Hemen buraya gel! (100) | Hemen buraya gel! |
| argo | That guy is a total jerk. | Bu adam tam bir pislik. (61) | O adam tam bir pislik. (61) | Şu herif tam bir pislik. |
| argo | Shut up and drive, man. | Kapa çeneni ve sür, dostum. (65) | Sus ve arabayı kullan, dostum. (31) | Kes sesini ve sür, dostum. |
| argo | I ain't got time for this crap. | Bu saçmalık için zamanım yok. (37) | Buna zamanım yok. (14) | Bu saçmalıklara ayıracak vaktim yok. |
| argo | You're out of your damn mind. | Aklını kaçırmışsın sen. (100) | Aklın tamamen karışmış. (25) | Aklını kaçırmışsın sen. |
| argo | What the hell is wrong with you? | Senin neyin var böyle? (84) | Ne oldu seninle? (16) | Senin neyin var be? |
| argo | He's loaded, that son of a gun. | O, silahın oğlu, çok zengin. (13) | Doldurulmuş, o çocuk. (8) | Adamın parası çok, şu hınzır. |
| argo | Quit messing around and focus. | Ortalığı karıştırmayı bırak ve odaklan. (51) | Oyun oynamayı bırak ve odaklan. (55) | Oyalanmayı bırak da odaklan. |
| argo | No way, dude, you're pulling my leg. | Olmaz dostum, bacağımı çekiyorsun. (46) | Hayır, dostum, sen benimle dalga geçiyorsun. (73) | Olamaz dostum, benimle dalga geçiyorsun. |
| argo | Don't screw this up, got it? | Bu işi batırma, tamam mı? (15) | Bunu bozma, anladın mı? (52) | Bunu berbat etme, anladın mı? |
| argo | I'm so sick of your bullshit. | Senin saçmalıklarından bıktım artık. (93) | Senin saçmalıklarından çok sıkıldım. (53) | Saçmalıklarından bıktım artık. |
| argo | Yo, check out this ride! | Hey, şu gezintiye bak! (18) | Hadi, bu arabaya bin! (49) | Yo, şu arabaya bak! |
| argo | Man, that was freaking awesome! | Adamım, bu müthişti! (15) | Dostum, bu inanılmaz derecede harikaydı! (80) | Dostum, bu inanılmazdı! |
| argo | He bailed on us at the last minute. | Bizi son anda yüzüstü bıraktı. (55) | Son dakikada bizi terk etti. (50) | Son dakikada bizi yüzüstü bıraktı. |
| argo | Keep your hands where I can see 'em. | Ellerini görebileceğim bir yerde tut. (77) | Ellerinizi görebileceğim bir yerde tutun. (64) | Ellerini göreceğim yerde tut. |
| argo | That's some messed up stuff right there. | Şurası berbat bir yer. (12) | Bu gerçekten çok saçma bir durum. (60) | Bu gerçekten çok sapıkça bir şey. |
| argo | You think you're tough, huh? | Kendini sert mi sanıyorsun? (38) | Zor biri olduğunu sanıyorsun, değil mi? (67) | Sert olduğunu sanıyorsun, ha? |
| argo | I'm gonna kick your ass if you touch that. | Ona dokunursan kıçına tekmeyi basarım. (49) | Eğer ona dokunursan seni tokatlarım. (45) | Ona dokunursan canına okurum. |
| argo | Whatever, I'm out of here. | Her neyse, ben gidiyorum. (100) | Sorun değil, buradan ayrılıyorum. (23) | Her neyse, ben gidiyorum. |
| argo | She's hot as hell, no joke. | Çok seksi, şaka yok. (30) | Çok seksi, şaka yapmıyorum. (71) | Çok çekici, şaka yapmıyorum. |
| gorev | Reach the extraction point before time runs out. | Zaman dolmadan çıkarma noktasına ulaş. (40) | Zaman tükenmeden çıkış noktasına ulaş. (48) | Süre bitmeden tahliye noktasına ulaş. |
| gorev | Find the keycard and unlock the server room. | Anahtar kartını bulun ve sunucu odasının kilidini açın. (85) | Anahtar kartı bul ve sunucu odasını aç. (75) | Anahtar kartı bul ve sunucu odasının kilidini aç. |
| gorev | Eliminate all hostiles in the area. | Bölgedeki tüm düşmanları ortadan kaldırın. (57) | Bölgedeki tüm düşmanları yok et. (59) | Bölgedeki tüm düşmanları etkisiz hale getir. |
| gorev | Follow the courier without being seen. | Görülmeden kuryeyi takip edin. (45) | Görülmeden kuryeyi takip et. (54) | Kuryeyi görünmeden takip et. |
| gorev | Return to the safehouse. | Güvenli eve geri dön. (40) | Sığınak'a geri dön. (71) | Sığınağa geri dön. |
| gorev | Collect 5 medical supplies. | 5 tıbbi malzeme toplayın. (91) | 5 tane tıbbi mal topla. (57) | 5 tıbbi malzeme topla. |
| gorev | Defend the radio tower for 3 minutes. | Radyo kulesini 3 dakika savunun. (73) | 3 dakika boyunca radyo kulesini savun. (80) | Radyo kulesini 3 dakika boyunca savun. |
| gorev | Speak to the blacksmith in the market district. | Pazar bölgesindeki demirciyle konuş. (100) | Pazar bölgesindeki demirciyle konuş. (100) | Pazar bölgesindeki demirciyle konuş. |
| gorev | Steal the ledger from the mayor's office. | Hesap defterini belediye başkanının ofisinden çal. (80) | Belediye binasından defteri çal. (53) | Belediye başkanının ofisinden defteri çal. |
| gorev | Escape the building before the alarm triggers. | Alarm tetiklemeden binadan çıkın. (38) | Alarm çalmadan binadan kaç. (100) | Alarm çalmadan binadan kaç. |
| gorev | Destroy the three generators. | Üç jeneratörü yok edin. (86) | Üç jeneratörü yok et. (100) | Üç jeneratörü yok et. |
| gorev | Meet your contact at the old pier. | Bağlantınla eski iskelede buluş. (100) | Eski iskelede iletişim kurduğun kişiyle buluş. (47) | Bağlantınla eski iskelede buluş. |
| gorev | Optional: Take photos of the wildlife. | Optional: Vahşi yaşamın fotoğraflarını çekin. (45) | İsteğe bağlı: Vahşi yaşam fotoğrafları çek. (55) | İsteğe bağlı: Yaban hayatının fotoğraflarını çek. |
| gorev | Hack the terminal to open the gate. | Kapıyı açmak için terminali hackleyin. (78) | Terminali hack edip kapıyı aç. (39) | Kapıyı açmak için terminale sız. |
| gorev | Lose the police by hiding in an alley. | Polisi bir sokakta saklanarak kaybedin. (57) | Sokağa saklanarak polisi kaçır. (48) | Bir sokakta saklanarak polisten kurtul. |
| gorev | Deliver the package to the marked location. | Paketi işaretli yere teslim edin. (62) | Paketi işaretli yere getir. (48) | Paketi işaretli konuma teslim et. |
| gorev | Wanted level: 3 stars. Evade the pursuit. | Aranan seviye: 3 yıldız. Takipten kurtulun. (73) | Aranma seviyesi: 3 yıldız. Takibi kaçın. (71) | Aranma seviyesi: 3 yıldız. Takipten kurtul. |
| gorev | New objective: Investigate the abandoned warehouse. | Yeni hedef: Terk edilmiş depoyu araştırın. (74) | Yeni görev: Terk edilmiş depoyu araştır. (100) | Yeni görev: Terk edilmiş depoyu araştır. |
| gorev | Mission failed. The target escaped. | Görev başarısız oldu. Hedef kaçtı. (86) | Misyon başarısız oldu. Hedef kaçtı. (65) | Görev başarısız. Hedef kaçtı. |
| gorev | Checkpoint reached. | Kontrol noktasına ulaşıldı. (100) | Kontrol noktasına ulaştık. (80) | Kontrol noktasına ulaşıldı. |
| arayuz | Press E to open the door. | Kapıyı açmak için E tuşuna basın. (68) | Kapıyı açmak için E tuşuna bas. (71) | Kapıyı açmak için E'ye bas. |
| arayuz | Hold F to repair. | Onarım için F'yi tutun. (34) | F tuşuna bas ve tamir et. (15) | Onarmak için F'ye basılı tut. |
| arayuz | Game saved. | Oyun kaydedildi. (100) | Oyun kaydedildi. (100) | Oyun kaydedildi. |
| arayuz | Not enough ammo. | Yeterli cephane yok. (100) | Cefane eksik. (12) | Yeterli cephane yok. |
| arayuz | Inventory is full. | Envanter dolu. (100) | Envanter dolu. (100) | Envanter dolu. |
| arayuz | Do you want to quit without saving? | Tasarruf etmeden bırakmak ister misiniz? (36) | Kaydetmeden çıkmak istiyor musun? (100) | Kaydetmeden çıkmak istiyor musun? |
| arayuz | Press any button to continue. | Devam etmek için herhangi bir düğmeye basın. (75) | Devam etmek için herhangi bir düğmeye bas. (77) | Devam etmek için herhangi bir tuşa bas. |
| arayuz | Difficulty: Hard | Difficulty: Sert (6) | Zorluk: Zor (100) | Zorluk: Zor |
| arayuz | Fast travel unavailable in combat. | Hızlı yolculuk savaşta kullanılamaz. (55) | Savaşta hızlı seyahat mümkün değil. (16) | Çatışma sırasında hızlı yolculuk kullanılamaz. |
| arayuz | You have unlocked a new skill. | Yeni bir yeteneğin kilidini açtın. (72) | Yeni bir yetenek açıldı. (78) | Yeni bir yetenek açtın. |
| arayuz | Low health. Find cover. | Düşük sağlık. Saklanın. (10) | Düşük can. Siper bul. (48) | Can azaldı. Siper bul. |
| arayuz | Press R to reload. | Yeniden yüklemek için R tuşuna basın. (27) | Doldur deme, araba. (25) | Doldurmak için R'ye bas. |
| arayuz | Autosaving, please do not turn off the console. | Otomatik kaydetme, lütfen konsolu kapatma. (71) | Kaydetmeyi kapatma, konsolu açmayın lütfen. (42) | Otomatik kaydediliyor, lütfen konsolu kapatmayın. |
| arayuz | Gear up before you leave the camp. | Kamptan ayrılmadan önce hazırlanın. (66) | Kampı terk etmeden önce hazırlan. (29) | Kamptan ayrılmadan önce teçhizatını hazırla. |
| arayuz | Controls: Move, Aim, Fire | Controls: Hareket et, Nişan al, Ateş (61) | Kontroller: Hareket et, Nişan al, Ateş et (82) | Kontroller: Hareket, Nişan, Ateş |
| resmi | The kingdom has fallen, and only you can restore it. | Krallık düştü ve onu sadece sen geri getirebilirsin. (34) | Krallık düştü, ve onu geri getirebilecek tek kişi sensin. (26) | Krallık yıkıldı ve onu yalnızca sen yeniden kurabilirsin. |
| resmi | By the order of the council, you are hereby banished. | Konseyin emriyle, buradan kovuldun. (42) | Konseyin emriyle, sen buradan kovuluyorsun. (41) | Konseyin emriyle sürgüne gönderildiniz. |
| resmi | Long ago, the old gods walked among mortals. | Uzun zaman önce, eski tanrılar ölümlüler arasında yürüdüler. (60) | Çok eskiden, eski tanrılar insanlar arasında dolaşırdı. (78) | Çok eskiden, eski tanrılar ölümlüler arasında dolaşırdı. |
| resmi | Your Majesty, the army has crossed the border. | Majesteleri, ordu sınırı geçti. (100) | Efendim, ordu sınırı geçti. (60) | Majesteleri, ordu sınırı geçti. |
| resmi | I swear on my honor that I will protect you. | Şerefim üzerine yemin ederim ki seni koruyacağım. (100) | Onu koruyacağıma yemin ederim. (47) | Şerefim üzerine yemin ederim ki seni koruyacağım. |
| resmi | The prophecy speaks of a chosen one. | Kehanet seçilmiş birinden bahseder. (55) | Kehanet, seçilmiş birini anlatıyor. (47) | Kehanet seçilmiş bir kişiden söz ediyor. |
| resmi | Welcome, traveler. You look weary from the road. | Hoş geldin gezgin. Yoldan yorgun görünüyorsun. (78) | Hoş geldin, yolcu dostum. Yoldan dolayı yorgun görünüyorsun. (82) | Hoş geldin, yolcu. Yoldan yorgun görünüyorsun. |
| resmi | This ancient relic must never fall into their hands. | Bu eski kalıntı asla onların eline geçmemeli. (69) | Bu eski eşya asla onların eline geçmemeli. (69) | Bu kadim emanet asla onların eline geçmemeli. |
| resmi | Ladies and gentlemen, the show is about to begin. | Bayanlar ve baylar, gösteri başlamak üzere. (100) | Bayanlar ve beyler, gösteri başlamak üzere. (83) | Bayanlar ve baylar, gösteri başlamak üzere. |
| resmi | In accordance with the law, you have the right to remain silent. | Yasalara göre sessiz kalma hakkına sahipsiniz. (57) | Yasalara göre, sessiz kalma hakkın var. (27) | Kanun gereği susma hakkına sahipsiniz. |
| resmi | The council will hear your petition at dawn. | Meclis dilekçeni şafakta duyacak. (45) | Konsey, şafak vakti senin dilekçeni dinleyecek. (63) | Konsey dilekçenizi şafakta dinleyecek. |
| resmi | Darkness spreads across the land, and hope grows faint. | Karanlığın tüm dünyaya yayıldığı ve umudun sönük kaldığı. (32) | Karanlık topraklara yayılıyor ve umut giderek azalıyor. (74) | Karanlık topraklara yayılıyor ve umut sönükleşiyor. |
| resmi | Our scientists have confirmed the signal's origin. | Bilim adamlarımız sinyalin kaynağını doğruladı. (83) | Bilimcilerimiz sinyalin kaynağını doğruladı. (71) | Bilim insanlarımız sinyalin kaynağını doğruladı. |
| resmi | You are cleared to land on runway two. | İkinci piste inmeye hazırsınız. (46) | İki numaralı piste inmek için izinlisin. (59) | İkinci piste inmek için izin verildi. |
| resmi | Citizens are advised to remain indoors. | Vatandaşların içeride kalmaları tavsiye edilir. (60) | Vatandaşların içeride kalmaları öneriliyor. (73) | Vatandaşların evlerinde kalmaları önerilir. |
| kisa | Move! | Çekilin! (4) | Hareket et! (4) | Kımılda! |
| kisa | Watch out! | Dikkat et! (100) | Dikkat et! (100) | Dikkat et! |
| kisa | Get down! | Eğilin! (2) | Aşağı in! (4) | Yat yere! |
| kisa | Over here! | Bu tarafa! (21) | Burada! (36) | Buraya! |
| kisa | Not now. | Şimdi olmaz. (29) | Şimdi değil. (100) | Şimdi değil. |
| kisa | Are you okay? | İyi misin? (100) | İyi misin? (100) | İyi misin? |
| kisa | Behind you! | Arkanda! (100) | Arkada! (39) | Arkanda! |
| kisa | Cover me! | Koru beni! (26) | Siperimi aç! (7) | Beni koru! |
| kisa | Go, go, go! | Hadi, hadi, hadi! (100) | Hadi, hadi, hadi! (100) | Hadi, hadi, hadi! |
| kisa | Wait for it. | Bekle biraz. (49) | Bekle onu. (54) | Bekle. |
| kisa | I'm hit! | Vuruldum! (100) | Vuruldum! (100) | Vuruldum! |
| kisa | Nice shot. | İyi atıştı. (20) | Aferin, iyi atış. (28) | Güzel atış. |
| kisa | After you. | Önden buyurun. (9) | Sonra sen. (8) | Önce siz. |
| kisa | Hold your fire! | Ateşi kesin! (26) | Sakin ol! (6) | Ateş etmeyin! |
| kisa | Stay with me. | Benimle kal. (100) | Benimle kal. (100) | Benimle kal. |
| ocr | l told you not to come here. | Sana buraya gelme demiştim. (90) | Buraya gelmemeni söylemiştim. (73) | Buraya gelme demiştim. |
| ocr | Wh0 are you, and what do you want? | Sen nesin ve ne istiyorsun? (77) | Sen kimsin ve ne istiyorsun? (100) | Sen kimsin ve ne istiyorsun? |
| ocr | We need to get out of here n0w. | Buradan n0w ile çıkmalıyız. (27) | Şimdi buradan çıkmamız gerekiyor. (82) | Hemen buradan çıkmamız gerekiyor. |
| ocr | Y0u'll never make it out alive. | Hayatta kalmayı asla başaramazsın. (22) | Hayatta kurtulamayacaksın. (47) | Buradan sağ çıkamayacaksın. |
| ocr | Th e door is locked from the inside. | Kapı içeriden kilitlendi. (88) | İçeriden kapı kilitli. (66) | Kapı içeriden kilitli. |
| ocr | Where is the key? I cant find it. | Anahtar nerede? Onu bulamıyorum. (82) | Anahtar nerede? Bulamıyorum. (100) | Anahtar nerede? Bulamıyorum. |
| ocr | He s been waiting for hours. | Saatlerdir bekliyor. (100) | Saatlerce bekledi. (40) | Saatlerdir bekliyor. |
| ocr | Let' s go before they see us. | Onlar bizi görmeden gidelim. (89) | Bizi görmeden gitelim. (79) | Bizi görmeden gidelim. |
| ocr | It was a lovely night, wasn't it? | Güzel bir geceydi, değil mi? (100) | Harika bir geceydi, değil mi? (76) | Güzel bir geceydi, değil mi? |
| ocr | I dont know what youre talking about. | Neden bahsettiğini bilmiyorum. (75) | Ne hakkında konuştuğunu bilmiyorum. (45) | Ne dediğini bilmiyorum. |
