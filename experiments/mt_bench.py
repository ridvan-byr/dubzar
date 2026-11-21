"""Translation benchmark for game subtitles: English lines written for this test (not taken from any game), each with a
Turkish reference written by Claude. The score says how close a model comes to that reference, not that the reference is
the truth: have a native speaker rate a sample (see docs/superpowers/specs) before trusting small differences.

    python experiments/mt_bench.py --threads 8 --out experiments/mt_bench_report.md

Categories: konusma (everyday dialogue), argo (slang, swearing), gorev (quest and objective text), arayuz (prompts and menus),
resmi (formal, fantasy, narration), kisa (shouts and one-word lines), ocr (lines with typical screen-reading mistakes).
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).parent))

from translation_eval import chrf  # noqa: E402

BENCH: list[tuple[str, str, str]] = [
    # ---- konusma
    ("konusma", "I thought you were coming with us tonight.", "Bu gece bizimle geleceğini sanıyordum."),
    ("konusma", "Don't worry about it, I'll take care of everything.", "Boşver, her şeyi ben halledeceğim."),
    ("konusma", "Did you really think I wouldn't find out?", "Öğrenmeyeceğimi mi sandın gerçekten?"),
    ("konusma", "We've been waiting for you for over an hour.", "Seni bir saatten fazladır bekliyoruz."),
    ("konusma", "I'm sorry, I didn't mean to scare you.", "Özür dilerim, seni korkutmak istememiştim."),
    ("konusma", "How long has he been like this?", "Ne zamandır böyle?"),
    ("konusma", "That's not what he told me yesterday.", "Dün bana söylediği bu değildi."),
    ("konusma", "You should get some rest, you look terrible.", "Biraz dinlenmelisin, berbat görünüyorsun."),
    ("konusma", "Let me guess, he forgot to mention that part.", "Tahmin edeyim, o kısmı söylemeyi unuttu."),
    ("konusma", "I can't believe she actually said yes.", "Evet dediğine inanamıyorum."),
    ("konusma", "Where did you get that from?", "Bunu nereden buldun?"),
    ("konusma", "If it were up to me, we'd leave right now.", "Bana kalsa, hemen şimdi çıkardık."),
    ("konusma", "I've never seen anything like it in my life.", "Hayatımda böyle bir şey görmedim."),
    ("konusma", "Just give me a minute to think.", "Düşünmem için bana bir dakika ver."),
    ("konusma", "He's been acting strange ever since the accident.", "Kazadan beri tuhaf davranıyor."),
    ("konusma", "What are you doing here so late?", "Bu kadar geç saatte burada ne yapıyorsun?"),
    ("konusma", "You promised you'd be back by midnight.", "Gece yarısına kadar döneceğine söz vermiştin."),
    ("konusma", "I don't care what they say, I trust you.", "Ne derlerse desinler, sana güveniyorum."),
    ("konusma", "It's not as bad as it looks.", "Göründüğü kadar kötü değil."),
    ("konusma", "Who else knows about this place?", "Bu yeri başka kim biliyor?"),
    ("konusma", "I owe you an apology, and an explanation.", "Sana bir özür ve bir açıklama borçluyum."),
    ("konusma", "We'll talk about this later, okay?", "Bunu sonra konuşuruz, tamam mı?"),
    ("konusma", "She left without saying a word.", "Tek kelime etmeden gitti."),
    ("konusma", "Was that really necessary?", "Bu gerçekten gerekli miydi?"),
    ("konusma", "I'm starting to think this was a mistake.", "Bunun bir hata olduğunu düşünmeye başlıyorum."),
    # ---- argo
    ("argo", "Get your ass over here, now!", "Hemen buraya gel!"),
    ("argo", "That guy is a total jerk.", "Şu herif tam bir pislik."),
    ("argo", "Shut up and drive, man.", "Kes sesini ve sür, dostum."),
    ("argo", "I ain't got time for this crap.", "Bu saçmalıklara ayıracak vaktim yok."),
    ("argo", "You're out of your damn mind.", "Aklını kaçırmışsın sen."),
    ("argo", "What the hell is wrong with you?", "Senin neyin var be?"),
    ("argo", "He's loaded, that son of a gun.", "Adamın parası çok, şu hınzır."),
    ("argo", "Quit messing around and focus.", "Oyalanmayı bırak da odaklan."),
    ("argo", "No way, dude, you're pulling my leg.", "Olamaz dostum, benimle dalga geçiyorsun."),
    ("argo", "Don't screw this up, got it?", "Bunu berbat etme, anladın mı?"),
    ("argo", "I'm so sick of your bullshit.", "Saçmalıklarından bıktım artık."),
    ("argo", "Yo, check out this ride!", "Yo, şu arabaya bak!"),
    ("argo", "Man, that was freaking awesome!", "Dostum, bu inanılmazdı!"),
    ("argo", "He bailed on us at the last minute.", "Son dakikada bizi yüzüstü bıraktı."),
    ("argo", "Keep your hands where I can see 'em.", "Ellerini göreceğim yerde tut."),
    ("argo", "That's some messed up stuff right there.", "Bu gerçekten çok sapıkça bir şey."),
    ("argo", "You think you're tough, huh?", "Sert olduğunu sanıyorsun, ha?"),
    ("argo", "I'm gonna kick your ass if you touch that.", "Ona dokunursan canına okurum."),
    ("argo", "Whatever, I'm out of here.", "Her neyse, ben gidiyorum."),
    ("argo", "She's hot as hell, no joke.", "Çok çekici, şaka yapmıyorum."),
    # ---- gorev
    ("gorev", "Reach the extraction point before time runs out.", "Süre bitmeden tahliye noktasına ulaş."),
    ("gorev", "Find the keycard and unlock the server room.", "Anahtar kartı bul ve sunucu odasının kilidini aç."),
    ("gorev", "Eliminate all hostiles in the area.", "Bölgedeki tüm düşmanları etkisiz hale getir."),
    ("gorev", "Follow the courier without being seen.", "Kuryeyi görünmeden takip et."),
    ("gorev", "Return to the safehouse.", "Sığınağa geri dön."),
    ("gorev", "Collect 5 medical supplies.", "5 tıbbi malzeme topla."),
    ("gorev", "Defend the radio tower for 3 minutes.", "Radyo kulesini 3 dakika boyunca savun."),
    ("gorev", "Speak to the blacksmith in the market district.", "Pazar bölgesindeki demirciyle konuş."),
    ("gorev", "Steal the ledger from the mayor's office.", "Belediye başkanının ofisinden defteri çal."),
    ("gorev", "Escape the building before the alarm triggers.", "Alarm çalmadan binadan kaç."),
    ("gorev", "Destroy the three generators.", "Üç jeneratörü yok et."),
    ("gorev", "Meet your contact at the old pier.", "Bağlantınla eski iskelede buluş."),
    ("gorev", "Optional: Take photos of the wildlife.", "İsteğe bağlı: Yaban hayatının fotoğraflarını çek."),
    ("gorev", "Hack the terminal to open the gate.", "Kapıyı açmak için terminale sız."),
    ("gorev", "Lose the police by hiding in an alley.", "Bir sokakta saklanarak polisten kurtul."),
    ("gorev", "Deliver the package to the marked location.", "Paketi işaretli konuma teslim et."),
    ("gorev", "Wanted level: 3 stars. Evade the pursuit.", "Aranma seviyesi: 3 yıldız. Takipten kurtul."),
    ("gorev", "New objective: Investigate the abandoned warehouse.", "Yeni görev: Terk edilmiş depoyu araştır."),
    ("gorev", "Mission failed. The target escaped.", "Görev başarısız. Hedef kaçtı."),
    ("gorev", "Checkpoint reached.", "Kontrol noktasına ulaşıldı."),
    # ---- arayuz
    ("arayuz", "Press E to open the door.", "Kapıyı açmak için E'ye bas."),
    ("arayuz", "Hold F to repair.", "Onarmak için F'ye basılı tut."),
    ("arayuz", "Game saved.", "Oyun kaydedildi."),
    ("arayuz", "Not enough ammo.", "Yeterli cephane yok."),
    ("arayuz", "Inventory is full.", "Envanter dolu."),
    ("arayuz", "Do you want to quit without saving?", "Kaydetmeden çıkmak istiyor musun?"),
    ("arayuz", "Press any button to continue.", "Devam etmek için herhangi bir tuşa bas."),
    ("arayuz", "Difficulty: Hard", "Zorluk: Zor"),
    ("arayuz", "Fast travel unavailable in combat.", "Çatışma sırasında hızlı yolculuk kullanılamaz."),
    ("arayuz", "You have unlocked a new skill.", "Yeni bir yetenek açtın."),
    ("arayuz", "Low health. Find cover.", "Can azaldı. Siper bul."),
    ("arayuz", "Press R to reload.", "Doldurmak için R'ye bas."),
    ("arayuz", "Autosaving, please do not turn off the console.", "Otomatik kaydediliyor, lütfen konsolu kapatmayın."),
    ("arayuz", "Gear up before you leave the camp.", "Kamptan ayrılmadan önce teçhizatını hazırla."),
    ("arayuz", "Controls: Move, Aim, Fire", "Kontroller: Hareket, Nişan, Ateş"),
    # ---- resmi
    ("resmi", "The kingdom has fallen, and only you can restore it.", "Krallık yıkıldı ve onu yalnızca sen yeniden kurabilirsin."),
    ("resmi", "By the order of the council, you are hereby banished.", "Konseyin emriyle sürgüne gönderildiniz."),
    ("resmi", "Long ago, the old gods walked among mortals.", "Çok eskiden, eski tanrılar ölümlüler arasında dolaşırdı."),
    ("resmi", "Your Majesty, the army has crossed the border.", "Majesteleri, ordu sınırı geçti."),
    ("resmi", "I swear on my honor that I will protect you.", "Şerefim üzerine yemin ederim ki seni koruyacağım."),
    ("resmi", "The prophecy speaks of a chosen one.", "Kehanet seçilmiş bir kişiden söz ediyor."),
    ("resmi", "Welcome, traveler. You look weary from the road.", "Hoş geldin, yolcu. Yoldan yorgun görünüyorsun."),
    ("resmi", "This ancient relic must never fall into their hands.", "Bu kadim emanet asla onların eline geçmemeli."),
    ("resmi", "Ladies and gentlemen, the show is about to begin.", "Bayanlar ve baylar, gösteri başlamak üzere."),
    ("resmi", "In accordance with the law, you have the right to remain silent.", "Kanun gereği susma hakkına sahipsiniz."),
    ("resmi", "The council will hear your petition at dawn.", "Konsey dilekçenizi şafakta dinleyecek."),
    ("resmi", "Darkness spreads across the land, and hope grows faint.", "Karanlık topraklara yayılıyor ve umut sönükleşiyor."),
    ("resmi", "Our scientists have confirmed the signal's origin.", "Bilim insanlarımız sinyalin kaynağını doğruladı."),
    ("resmi", "You are cleared to land on runway two.", "İkinci piste inmek için izin verildi."),
    ("resmi", "Citizens are advised to remain indoors.", "Vatandaşların evlerinde kalmaları önerilir."),
    # ---- kisa
    ("kisa", "Move!", "Kımılda!"),
    ("kisa", "Watch out!", "Dikkat et!"),
    ("kisa", "Get down!", "Yat yere!"),
    ("kisa", "Over here!", "Buraya!"),
    ("kisa", "Not now.", "Şimdi değil."),
    ("kisa", "Are you okay?", "İyi misin?"),
    ("kisa", "Behind you!", "Arkanda!"),
    ("kisa", "Cover me!", "Beni koru!"),
    ("kisa", "Go, go, go!", "Hadi, hadi, hadi!"),
    ("kisa", "Wait for it.", "Bekle."),
    ("kisa", "I'm hit!", "Vuruldum!"),
    ("kisa", "Nice shot.", "Güzel atış."),
    ("kisa", "After you.", "Önce siz."),
    ("kisa", "Hold your fire!", "Ateş etmeyin!"),
    ("kisa", "Stay with me.", "Benimle kal."),
    # ---- ocr (typical screen-reading mistakes: l for I, 0 for O, missing letters, odd spacing)
    ("ocr", "l told you not to come here.", "Buraya gelme demiştim."),
    ("ocr", "Wh0 are you, and what do you want?", "Sen kimsin ve ne istiyorsun?"),
    ("ocr", "We need to get out of here n0w.", "Hemen buradan çıkmamız gerekiyor."),
    ("ocr", "Y0u'll never make it out alive.", "Buradan sağ çıkamayacaksın."),
    ("ocr", "Th e door is locked from the inside.", "Kapı içeriden kilitli."),
    ("ocr", "Where is the key? I cant find it.", "Anahtar nerede? Bulamıyorum."),
    ("ocr", "He s been waiting for hours.", "Saatlerdir bekliyor."),
    ("ocr", "Let' s go before they see us.", "Bizi görmeden gidelim."),
    ("ocr", "It was a lovely night, wasn't it?", "Güzel bir geceydi, değil mi?"),
    ("ocr", "I dont know what youre talking about.", "Ne dediğini bilmiyorum."),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")

    from dubzar.translate import OpusMtTranslator

    translator = OpusMtTranslator(threads=args.threads)
    translator.load()
    rows = []
    for category, english, reference in BENCH:
        hypothesis = translator.translate(english)
        rows.append((category, english, reference, hypothesis, chrf(hypothesis, reference)))

    by_category = defaultdict(list)
    for category, _, _, _, score in rows:
        by_category[category].append(score)
    overall = sum(r[4] for r in rows) / len(rows)
    lines = [f"# Çeviri karşılaştırması: Opus-MT ile Claude'un referans çevirileri", "",
             f"{len(rows)} satır, chrF ortalaması **{overall:.1f}**", "",
             "| Tür | satır | chrF |", "|---|---|---|"]
    for category, scores in by_category.items():
        lines.append(f"| {category} | {len(scores)} | {sum(scores) / len(scores):.1f} |")
    lines += ["", "## En düşük 30 satır", "", "| chrF | tür | İngilizce | Opus-MT | referans |", "|---|---|---|---|---|"]
    for category, english, reference, hypothesis, score in sorted(rows, key=lambda r: r[4])[:30]:
        lines.append(f"| {score:.0f} | {category} | {english} | {hypothesis} | {reference} |")
    lines += ["", "## Tüm satırlar", "", "| chrF | tür | İngilizce | Opus-MT | referans |", "|---|---|---|---|---|"]
    for category, english, reference, hypothesis, score in rows:
        lines.append(f"| {score:.0f} | {category} | {english} | {hypothesis} | {reference} |")
    report = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    print("\n".join(lines[:14]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
