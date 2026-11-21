# Çeviri karşılaştırması: Opus-MT ile Claude'un referans çevirileri

120 satır, chrF ortalaması **66.7**

| Tür | satır | chrF |
|---|---|---|
| konusma | 25 | 86.3 |
| argo | 20 | 53.0 |
| gorev | 20 | 70.5 |
| arayuz | 15 | 58.7 |
| resmi | 15 | 64.0 |
| kisa | 15 | 52.6 |
| ocr | 10 | 75.0 |

## En düşük 30 satır

| chrF | tür | İngilizce | Opus-MT | referans |
|---|---|---|---|---|
| 2 | kisa | Get down! | Eğilin! | Yat yere! |
| 4 | kisa | Move! | Çekilin! | Kımılda! |
| 6 | arayuz | Difficulty: Hard | Difficulty: Sert | Zorluk: Zor |
| 9 | kisa | After you. | Önden buyurun. | Önce siz. |
| 10 | arayuz | Low health. Find cover. | Düşük sağlık. Saklanın. | Can azaldı. Siper bul. |
| 12 | argo | That's some messed up stuff right there. | Şurası berbat bir yer. | Bu gerçekten çok sapıkça bir şey. |
| 13 | argo | He's loaded, that son of a gun. | O, silahın oğlu, çok zengin. | Adamın parası çok, şu hınzır. |
| 15 | argo | Man, that was freaking awesome! | Adamım, bu müthişti! | Dostum, bu inanılmazdı! |
| 15 | argo | Don't screw this up, got it? | Bu işi batırma, tamam mı? | Bunu berbat etme, anladın mı? |
| 18 | argo | Yo, check out this ride! | Hey, şu gezintiye bak! | Yo, şu arabaya bak! |
| 20 | kisa | Nice shot. | İyi atıştı. | Güzel atış. |
| 21 | kisa | Over here! | Bu tarafa! | Buraya! |
| 22 | ocr | Y0u'll never make it out alive. | Hayatta kalmayı asla başaramazsın. | Buradan sağ çıkamayacaksın. |
| 26 | kisa | Hold your fire! | Ateşi kesin! | Ateş etmeyin! |
| 26 | kisa | Cover me! | Koru beni! | Beni koru! |
| 27 | arayuz | Press R to reload. | Yeniden yüklemek için R tuşuna basın. | Doldurmak için R'ye bas. |
| 27 | ocr | We need to get out of here n0w. | Buradan n0w ile çıkmalıyız. | Hemen buradan çıkmamız gerekiyor. |
| 29 | kisa | Not now. | Şimdi olmaz. | Şimdi değil. |
| 30 | argo | She's hot as hell, no joke. | Çok seksi, şaka yok. | Çok çekici, şaka yapmıyorum. |
| 32 | resmi | Darkness spreads across the land, and hope grows faint. | Karanlığın tüm dünyaya yayıldığı ve umudun sönük kaldığı. | Karanlık topraklara yayılıyor ve umut sönükleşiyor. |
| 34 | resmi | The kingdom has fallen, and only you can restore it. | Krallık düştü ve onu sadece sen geri getirebilirsin. | Krallık yıkıldı ve onu yalnızca sen yeniden kurabilirsin. |
| 34 | arayuz | Hold F to repair. | Onarım için F'yi tutun. | Onarmak için F'ye basılı tut. |
| 36 | arayuz | Do you want to quit without saving? | Tasarruf etmeden bırakmak ister misiniz? | Kaydetmeden çıkmak istiyor musun? |
| 37 | argo | I ain't got time for this crap. | Bu saçmalık için zamanım yok. | Bu saçmalıklara ayıracak vaktim yok. |
| 38 | argo | You think you're tough, huh? | Kendini sert mi sanıyorsun? | Sert olduğunu sanıyorsun, ha? |
| 38 | gorev | Escape the building before the alarm triggers. | Alarm tetiklemeden binadan çıkın. | Alarm çalmadan binadan kaç. |
| 40 | gorev | Return to the safehouse. | Güvenli eve geri dön. | Sığınağa geri dön. |
| 40 | gorev | Reach the extraction point before time runs out. | Zaman dolmadan çıkarma noktasına ulaş. | Süre bitmeden tahliye noktasına ulaş. |
| 42 | konusma | What are you doing here so late? | Bu saatte burada ne işin var? | Bu kadar geç saatte burada ne yapıyorsun? |
| 42 | resmi | By the order of the council, you are hereby banished. | Konseyin emriyle, buradan kovuldun. | Konseyin emriyle sürgüne gönderildiniz. |

## Tüm satırlar

| chrF | tür | İngilizce | Opus-MT | referans |
|---|---|---|---|---|
| 100 | konusma | I thought you were coming with us tonight. | Bu gece bizimle geleceğini sanıyordum. | Bu gece bizimle geleceğini sanıyordum. |
| 60 | konusma | Don't worry about it, I'll take care of everything. | Merak etme, her şeyi halledeceğim. | Boşver, her şeyi ben halledeceğim. |
| 83 | konusma | Did you really think I wouldn't find out? | Gerçekten öğrenmeyeceğimi mi sandın? | Öğrenmeyeceğimi mi sandın gerçekten? |
| 50 | konusma | We've been waiting for you for over an hour. | Bir saattir seni bekliyoruz. | Seni bir saatten fazladır bekliyoruz. |
| 100 | konusma | I'm sorry, I didn't mean to scare you. | Özür dilerim, seni korkutmak istememiştim. | Özür dilerim, seni korkutmak istememiştim. |
| 100 | konusma | How long has he been like this? | Ne zamandır böyle? | Ne zamandır böyle? |
| 100 | konusma | That's not what he told me yesterday. | Dün bana söylediği bu değildi. | Dün bana söylediği bu değildi. |
| 100 | konusma | You should get some rest, you look terrible. | Biraz dinlenmelisin, berbat görünüyorsun. | Biraz dinlenmelisin, berbat görünüyorsun. |
| 87 | konusma | Let me guess, he forgot to mention that part. | Dur tahmin edeyim, o kısmı söylemeyi unutmuş. | Tahmin edeyim, o kısmı söylemeyi unuttu. |
| 88 | konusma | I can't believe she actually said yes. | Gerçekten evet dediğine inanamıyorum. | Evet dediğine inanamıyorum. |
| 100 | konusma | Where did you get that from? | Bunu nereden buldun? | Bunu nereden buldun? |
| 54 | konusma | If it were up to me, we'd leave right now. | Eğer bana kalsaydı, hemen şimdi giderdik. | Bana kalsa, hemen şimdi çıkardık. |
| 88 | konusma | I've never seen anything like it in my life. | Hayatımda hiç böyle bir şey görmedim. | Hayatımda böyle bir şey görmedim. |
| 100 | konusma | Just give me a minute to think. | Düşünmem için bana bir dakika ver. | Düşünmem için bana bir dakika ver. |
| 69 | konusma | He's been acting strange ever since the accident. | Kazadan beri garip davranıyor. | Kazadan beri tuhaf davranıyor. |
| 42 | konusma | What are you doing here so late? | Bu saatte burada ne işin var? | Bu kadar geç saatte burada ne yapıyorsun? |
| 100 | konusma | You promised you'd be back by midnight. | Gece yarısına kadar döneceğine söz vermiştin. | Gece yarısına kadar döneceğine söz vermiştin. |
| 54 | konusma | I don't care what they say, I trust you. | Ne dedikleri umurumda değil, sana güveniyorum. | Ne derlerse desinler, sana güveniyorum. |
| 100 | konusma | It's not as bad as it looks. | Göründüğü kadar kötü değil. | Göründüğü kadar kötü değil. |
| 100 | konusma | Who else knows about this place? | Bu yeri başka kim biliyor? | Bu yeri başka kim biliyor? |
| 100 | konusma | I owe you an apology, and an explanation. | Sana bir özür ve bir açıklama borçluyum. | Sana bir özür ve bir açıklama borçluyum. |
| 100 | konusma | We'll talk about this later, okay? | Bunu sonra konuşuruz, tamam mı? | Bunu sonra konuşuruz, tamam mı? |
| 100 | konusma | She left without saying a word. | Tek kelime etmeden gitti. | Tek kelime etmeden gitti. |
| 100 | konusma | Was that really necessary? | Bu gerçekten gerekli miydi? | Bu gerçekten gerekli miydi? |
| 84 | konusma | I'm starting to think this was a mistake. | Bunun bir hata olduğunu düşünmeye başladım. | Bunun bir hata olduğunu düşünmeye başlıyorum. |
| 100 | argo | Get your ass over here, now! | Hemen buraya gel! | Hemen buraya gel! |
| 61 | argo | That guy is a total jerk. | Bu adam tam bir pislik. | Şu herif tam bir pislik. |
| 65 | argo | Shut up and drive, man. | Kapa çeneni ve sür, dostum. | Kes sesini ve sür, dostum. |
| 37 | argo | I ain't got time for this crap. | Bu saçmalık için zamanım yok. | Bu saçmalıklara ayıracak vaktim yok. |
| 100 | argo | You're out of your damn mind. | Aklını kaçırmışsın sen. | Aklını kaçırmışsın sen. |
| 84 | argo | What the hell is wrong with you? | Senin neyin var böyle? | Senin neyin var be? |
| 13 | argo | He's loaded, that son of a gun. | O, silahın oğlu, çok zengin. | Adamın parası çok, şu hınzır. |
| 51 | argo | Quit messing around and focus. | Ortalığı karıştırmayı bırak ve odaklan. | Oyalanmayı bırak da odaklan. |
| 46 | argo | No way, dude, you're pulling my leg. | Olmaz dostum, bacağımı çekiyorsun. | Olamaz dostum, benimle dalga geçiyorsun. |
| 15 | argo | Don't screw this up, got it? | Bu işi batırma, tamam mı? | Bunu berbat etme, anladın mı? |
| 93 | argo | I'm so sick of your bullshit. | Senin saçmalıklarından bıktım artık. | Saçmalıklarından bıktım artık. |
| 18 | argo | Yo, check out this ride! | Hey, şu gezintiye bak! | Yo, şu arabaya bak! |
| 15 | argo | Man, that was freaking awesome! | Adamım, bu müthişti! | Dostum, bu inanılmazdı! |
| 55 | argo | He bailed on us at the last minute. | Bizi son anda yüzüstü bıraktı. | Son dakikada bizi yüzüstü bıraktı. |
| 77 | argo | Keep your hands where I can see 'em. | Ellerini görebileceğim bir yerde tut. | Ellerini göreceğim yerde tut. |
| 12 | argo | That's some messed up stuff right there. | Şurası berbat bir yer. | Bu gerçekten çok sapıkça bir şey. |
| 38 | argo | You think you're tough, huh? | Kendini sert mi sanıyorsun? | Sert olduğunu sanıyorsun, ha? |
| 49 | argo | I'm gonna kick your ass if you touch that. | Ona dokunursan kıçına tekmeyi basarım. | Ona dokunursan canına okurum. |
| 100 | argo | Whatever, I'm out of here. | Her neyse, ben gidiyorum. | Her neyse, ben gidiyorum. |
| 30 | argo | She's hot as hell, no joke. | Çok seksi, şaka yok. | Çok çekici, şaka yapmıyorum. |
| 40 | gorev | Reach the extraction point before time runs out. | Zaman dolmadan çıkarma noktasına ulaş. | Süre bitmeden tahliye noktasına ulaş. |
| 85 | gorev | Find the keycard and unlock the server room. | Anahtar kartını bulun ve sunucu odasının kilidini açın. | Anahtar kartı bul ve sunucu odasının kilidini aç. |
| 57 | gorev | Eliminate all hostiles in the area. | Bölgedeki tüm düşmanları ortadan kaldırın. | Bölgedeki tüm düşmanları etkisiz hale getir. |
| 45 | gorev | Follow the courier without being seen. | Görülmeden kuryeyi takip edin. | Kuryeyi görünmeden takip et. |
| 40 | gorev | Return to the safehouse. | Güvenli eve geri dön. | Sığınağa geri dön. |
| 91 | gorev | Collect 5 medical supplies. | 5 tıbbi malzeme toplayın. | 5 tıbbi malzeme topla. |
| 73 | gorev | Defend the radio tower for 3 minutes. | Radyo kulesini 3 dakika savunun. | Radyo kulesini 3 dakika boyunca savun. |
| 100 | gorev | Speak to the blacksmith in the market district. | Pazar bölgesindeki demirciyle konuş. | Pazar bölgesindeki demirciyle konuş. |
| 80 | gorev | Steal the ledger from the mayor's office. | Hesap defterini belediye başkanının ofisinden çal. | Belediye başkanının ofisinden defteri çal. |
| 38 | gorev | Escape the building before the alarm triggers. | Alarm tetiklemeden binadan çıkın. | Alarm çalmadan binadan kaç. |
| 86 | gorev | Destroy the three generators. | Üç jeneratörü yok edin. | Üç jeneratörü yok et. |
| 100 | gorev | Meet your contact at the old pier. | Bağlantınla eski iskelede buluş. | Bağlantınla eski iskelede buluş. |
| 45 | gorev | Optional: Take photos of the wildlife. | Optional: Vahşi yaşamın fotoğraflarını çekin. | İsteğe bağlı: Yaban hayatının fotoğraflarını çek. |
| 78 | gorev | Hack the terminal to open the gate. | Kapıyı açmak için terminali hackleyin. | Kapıyı açmak için terminale sız. |
| 57 | gorev | Lose the police by hiding in an alley. | Polisi bir sokakta saklanarak kaybedin. | Bir sokakta saklanarak polisten kurtul. |
| 62 | gorev | Deliver the package to the marked location. | Paketi işaretli yere teslim edin. | Paketi işaretli konuma teslim et. |
| 73 | gorev | Wanted level: 3 stars. Evade the pursuit. | Aranan seviye: 3 yıldız. Takipten kurtulun. | Aranma seviyesi: 3 yıldız. Takipten kurtul. |
| 74 | gorev | New objective: Investigate the abandoned warehouse. | Yeni hedef: Terk edilmiş depoyu araştırın. | Yeni görev: Terk edilmiş depoyu araştır. |
| 86 | gorev | Mission failed. The target escaped. | Görev başarısız oldu. Hedef kaçtı. | Görev başarısız. Hedef kaçtı. |
| 100 | gorev | Checkpoint reached. | Kontrol noktasına ulaşıldı. | Kontrol noktasına ulaşıldı. |
| 68 | arayuz | Press E to open the door. | Kapıyı açmak için E tuşuna basın. | Kapıyı açmak için E'ye bas. |
| 34 | arayuz | Hold F to repair. | Onarım için F'yi tutun. | Onarmak için F'ye basılı tut. |
| 100 | arayuz | Game saved. | Oyun kaydedildi. | Oyun kaydedildi. |
| 100 | arayuz | Not enough ammo. | Yeterli cephane yok. | Yeterli cephane yok. |
| 100 | arayuz | Inventory is full. | Envanter dolu. | Envanter dolu. |
| 36 | arayuz | Do you want to quit without saving? | Tasarruf etmeden bırakmak ister misiniz? | Kaydetmeden çıkmak istiyor musun? |
| 75 | arayuz | Press any button to continue. | Devam etmek için herhangi bir düğmeye basın. | Devam etmek için herhangi bir tuşa bas. |
| 6 | arayuz | Difficulty: Hard | Difficulty: Sert | Zorluk: Zor |
| 55 | arayuz | Fast travel unavailable in combat. | Hızlı yolculuk savaşta kullanılamaz. | Çatışma sırasında hızlı yolculuk kullanılamaz. |
| 72 | arayuz | You have unlocked a new skill. | Yeni bir yeteneğin kilidini açtın. | Yeni bir yetenek açtın. |
| 10 | arayuz | Low health. Find cover. | Düşük sağlık. Saklanın. | Can azaldı. Siper bul. |
| 27 | arayuz | Press R to reload. | Yeniden yüklemek için R tuşuna basın. | Doldurmak için R'ye bas. |
| 71 | arayuz | Autosaving, please do not turn off the console. | Otomatik kaydetme, lütfen konsolu kapatma. | Otomatik kaydediliyor, lütfen konsolu kapatmayın. |
| 66 | arayuz | Gear up before you leave the camp. | Kamptan ayrılmadan önce hazırlanın. | Kamptan ayrılmadan önce teçhizatını hazırla. |
| 61 | arayuz | Controls: Move, Aim, Fire | Controls: Hareket et, Nişan al, Ateş | Kontroller: Hareket, Nişan, Ateş |
| 34 | resmi | The kingdom has fallen, and only you can restore it. | Krallık düştü ve onu sadece sen geri getirebilirsin. | Krallık yıkıldı ve onu yalnızca sen yeniden kurabilirsin. |
| 42 | resmi | By the order of the council, you are hereby banished. | Konseyin emriyle, buradan kovuldun. | Konseyin emriyle sürgüne gönderildiniz. |
| 60 | resmi | Long ago, the old gods walked among mortals. | Uzun zaman önce, eski tanrılar ölümlüler arasında yürüdüler. | Çok eskiden, eski tanrılar ölümlüler arasında dolaşırdı. |
| 100 | resmi | Your Majesty, the army has crossed the border. | Majesteleri, ordu sınırı geçti. | Majesteleri, ordu sınırı geçti. |
| 100 | resmi | I swear on my honor that I will protect you. | Şerefim üzerine yemin ederim ki seni koruyacağım. | Şerefim üzerine yemin ederim ki seni koruyacağım. |
| 55 | resmi | The prophecy speaks of a chosen one. | Kehanet seçilmiş birinden bahseder. | Kehanet seçilmiş bir kişiden söz ediyor. |
| 78 | resmi | Welcome, traveler. You look weary from the road. | Hoş geldin gezgin. Yoldan yorgun görünüyorsun. | Hoş geldin, yolcu. Yoldan yorgun görünüyorsun. |
| 69 | resmi | This ancient relic must never fall into their hands. | Bu eski kalıntı asla onların eline geçmemeli. | Bu kadim emanet asla onların eline geçmemeli. |
| 100 | resmi | Ladies and gentlemen, the show is about to begin. | Bayanlar ve baylar, gösteri başlamak üzere. | Bayanlar ve baylar, gösteri başlamak üzere. |
| 57 | resmi | In accordance with the law, you have the right to remain silent. | Yasalara göre sessiz kalma hakkına sahipsiniz. | Kanun gereği susma hakkına sahipsiniz. |
| 45 | resmi | The council will hear your petition at dawn. | Meclis dilekçeni şafakta duyacak. | Konsey dilekçenizi şafakta dinleyecek. |
| 32 | resmi | Darkness spreads across the land, and hope grows faint. | Karanlığın tüm dünyaya yayıldığı ve umudun sönük kaldığı. | Karanlık topraklara yayılıyor ve umut sönükleşiyor. |
| 83 | resmi | Our scientists have confirmed the signal's origin. | Bilim adamlarımız sinyalin kaynağını doğruladı. | Bilim insanlarımız sinyalin kaynağını doğruladı. |
| 46 | resmi | You are cleared to land on runway two. | İkinci piste inmeye hazırsınız. | İkinci piste inmek için izin verildi. |
| 60 | resmi | Citizens are advised to remain indoors. | Vatandaşların içeride kalmaları tavsiye edilir. | Vatandaşların evlerinde kalmaları önerilir. |
| 4 | kisa | Move! | Çekilin! | Kımılda! |
| 100 | kisa | Watch out! | Dikkat et! | Dikkat et! |
| 2 | kisa | Get down! | Eğilin! | Yat yere! |
| 21 | kisa | Over here! | Bu tarafa! | Buraya! |
| 29 | kisa | Not now. | Şimdi olmaz. | Şimdi değil. |
| 100 | kisa | Are you okay? | İyi misin? | İyi misin? |
| 100 | kisa | Behind you! | Arkanda! | Arkanda! |
| 26 | kisa | Cover me! | Koru beni! | Beni koru! |
| 100 | kisa | Go, go, go! | Hadi, hadi, hadi! | Hadi, hadi, hadi! |
| 49 | kisa | Wait for it. | Bekle biraz. | Bekle. |
| 100 | kisa | I'm hit! | Vuruldum! | Vuruldum! |
| 20 | kisa | Nice shot. | İyi atıştı. | Güzel atış. |
| 9 | kisa | After you. | Önden buyurun. | Önce siz. |
| 26 | kisa | Hold your fire! | Ateşi kesin! | Ateş etmeyin! |
| 100 | kisa | Stay with me. | Benimle kal. | Benimle kal. |
| 90 | ocr | l told you not to come here. | Sana buraya gelme demiştim. | Buraya gelme demiştim. |
| 77 | ocr | Wh0 are you, and what do you want? | Sen nesin ve ne istiyorsun? | Sen kimsin ve ne istiyorsun? |
| 27 | ocr | We need to get out of here n0w. | Buradan n0w ile çıkmalıyız. | Hemen buradan çıkmamız gerekiyor. |
| 22 | ocr | Y0u'll never make it out alive. | Hayatta kalmayı asla başaramazsın. | Buradan sağ çıkamayacaksın. |
| 88 | ocr | Th e door is locked from the inside. | Kapı içeriden kilitlendi. | Kapı içeriden kilitli. |
| 82 | ocr | Where is the key? I cant find it. | Anahtar nerede? Onu bulamıyorum. | Anahtar nerede? Bulamıyorum. |
| 100 | ocr | He s been waiting for hours. | Saatlerdir bekliyor. | Saatlerdir bekliyor. |
| 89 | ocr | Let' s go before they see us. | Onlar bizi görmeden gidelim. | Bizi görmeden gidelim. |
| 100 | ocr | It was a lovely night, wasn't it? | Güzel bir geceydi, değil mi? | Güzel bir geceydi, değil mi? |
| 75 | ocr | I dont know what youre talking about. | Neden bahsettiğini bilmiyorum. | Ne dediğini bilmiyorum. |
