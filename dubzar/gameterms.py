"""Game-interface text that a general translation model gets wrong, handled by rules that cannot go wrong on other text:

* ``match_prompt``: "Press E to open the door." / "Hold F to repair." / "Press any button to continue." The model translates the
  purpose part ("to open the door" -> "Kapıyı açmak için") well and the whole sentence badly; so only that part goes to the
  model and the rest is put together here ("... E tuşuna bas.").
* ``memory_lookup``: a small translation memory of very common whole interface lines ("Game saved.", "Inventory is full.").
  Only an exact match (ignoring case and end punctuation) is used, so it never touches ordinary speech.
"""

import re
from typing import Callable

KEY = (r"(?P<key>any (?:button|key)|[A-Z0-9]{1,3}|F\d{1,2}|Space(?:bar)?|Enter|Tab|Shift|Ctrl|Alt|Esc|Escape|Backspace|"
       r"[LRM]MB|Left Click|Right Click|Mouse \d|[LR][123Tt]|D-?Pad)")
_PROMPT = re.compile(rf"^(?P<verb>Press|Hold|Tap|Double[- ]tap)\s+{KEY}\s+to\s+(?P<phrase>[^.!?]+?)\s*[.!]?$", re.IGNORECASE)
_KEY_NAMES = {"space": "Boşluk", "spacebar": "Boşluk", "lmb": "Sol fare", "rmb": "Sağ fare", "mmb": "Orta fare",
              "left click": "Sol fare", "right click": "Sağ fare", "esc": "Esc", "escape": "Esc"}
_PURPOSE_END = ("için", "amacıyla")
# the common game verbs the model gets wrong or leaves in English ("to sprint" -> "Sprint için", "to take cover" -> "örtmek için")
VERB_PURPOSE = {"sprint": "koşmak için", "run": "koşmak için", "aim": "nişan almak için", "take cover": "siper almak için",
                "cover": "siper almak için", "interact": "etkileşime geçmek için", "crouch": "çömelmek için",
                "shoot": "ateş etmek için", "fire": "ateş etmek için", "reload": "şarjör değiştirmek için",
                "jump": "zıplamak için", "climb": "tırmanmak için", "use": "kullanmak için", "open": "açmak için",
                "open the map": "haritayı açmak için", "open map": "haritayı açmak için",
                "open the inventory": "envanteri açmak için", "open inventory": "envanteri açmak için",
                "pick up": "almak için", "talk": "konuşmak için", "skip": "atlamak için", "continue": "devam etmek için",
                "pause": "duraklatmak için", "cancel": "iptal etmek için", "confirm": "onaylamak için",
                "select": "seçmek için", "accept": "kabul etmek için", "enter": "girmek için", "exit": "çıkmak için",
                "enter the vehicle": "araca binmek için", "exit the vehicle": "araçtan inmek için", "drive": "sürmek için",
                "brake": "fren yapmak için", "swim": "yüzmek için", "dive": "dalmak için", "hide": "saklanmak için",
                "repair": "tamir etmek için", "heal": "iyileşmek için", "dodge": "kaçınmak için", "roll": "yuvarlanmak için",
                "throw": "fırlatmak için", "grab": "tutmak için", "drop": "bırakmak için", "inspect": "incelemek için",
                "search": "aramak için", "loot": "yağmalamak için", "craft": "üretmek için", "switch weapon": "silah değiştirmek için",
                "change weapon": "silah değiştirmek için", "melee": "yakın dövüşe geçmek için", "attack": "saldırmak için"}


def match_prompt(text: str, translate_plain: Callable[[str], str]) -> str | None:
    """The Turkish sentence for "Press K to <something>", or None when ``text`` is not one (or the model's answer for the
    purpose does not end like a purpose clause, in which case the whole sentence is better left to the model)."""
    match = _PROMPT.match(text.strip())
    if not match:
        return None
    key = match.group("key")
    # a real key name is written in capitals; "press e to ..." in lower case is not a prompt we want to guess at
    if key.lower() not in ("any button", "any key") and not key[0].isupper():
        return None
    phrase = match.group("phrase").strip()
    purpose = VERB_PURPOSE.get(phrase.lower()) or translate_plain(f"to {phrase}").strip().rstrip(".!")
    if not purpose.lower().endswith(_PURPOSE_END):
        return None
    if purpose.lower().removesuffix(" için").strip() == phrase.lower():           # the word was only copied ("Sprint için")
        return None
    purpose = purpose[0].upper() + purpose[1:]
    if key.lower() in ("any button", "any key"):
        return f"{purpose} herhangi bir tuşa bas."
    name = _KEY_NAMES.get(key.lower(), key)
    held = match.group("verb").lower() == "hold"
    return f"{purpose} {name} tuşuna {'basılı tut' if held else 'bas'}."


# ---- translation memory (very common whole lines; informal "sen" for commands, as in most game text) ----
_MEMORY_SOURCE = {
    "Master Volume": "Ana ses",
    "Apply changes?": "Değişiklikler uygulansın mı?",
    "Release to throw": "Fırlatmak için bırak.",
    "Release to fire": "Ateş etmek için bırak.",
    "Game saved": "Oyun kaydedildi.",
    "Saving": "Kaydediliyor.",
    "Saving...": "Kaydediliyor...",
    "Loading": "Yükleniyor.",
    "Loading...": "Yükleniyor...",
    "Game over": "Oyun bitti.",
    "Mission complete": "Görev tamamlandı.",
    "Mission passed": "Görev tamamlandı.",
    "Mission failed": "Görev başarısız.",
    "Checkpoint reached": "Kontrol noktasına ulaşıldı.",
    "Checkpoint": "Kontrol noktası.",
    "Not enough ammo": "Yeterli cephane yok.",
    "Out of ammo": "Cephane bitti.",
    "Inventory is full": "Envanter dolu.",
    "Low health": "Can azaldı.",
    "Low ammo": "Cephane azaldı.",
    "Press any button to continue": "Devam etmek için herhangi bir tuşa bas.",
    "New objective": "Yeni görev.",
    "Objective updated": "Görev güncellendi.",
    "Objective complete": "Görev tamamlandı.",
    "Optional objective": "İsteğe bağlı görev.",
    "Quest started": "Görev başladı.",
    "Quest completed": "Görev tamamlandı.",
    "Quest updated": "Görev güncellendi.",
    "Level up": "Seviye atladın.",
    "You died": "Öldün.",
    "Wasted": "Harcandın.",
    "Busted": "Yakalandın.",
    "Resume": "Devam",
    "Continue": "Devam",
    "New game": "Yeni oyun",
    "Load game": "Oyunu yükle",
    "Save game": "Oyunu kaydet",
    "Options": "Seçenekler",
    "Settings": "Ayarlar",
    "Quit game": "Oyundan çık",
    "Exit game": "Oyundan çık",
    "Back": "Geri",
    "Cancel": "İptal",
    "Confirm": "Onayla",
    "Accept": "Kabul et",
    "Decline": "Reddet",
    "Yes": "Evet",
    "No": "Hayır",
    "Paused": "Duraklatıldı.",
    "Pause": "Duraklat",
    "Autosaving": "Otomatik kaydediliyor.",
    "Autosaving...": "Otomatik kaydediliyor...",
    "Do you want to quit without saving": "Kaydetmeden çıkmak istiyor musun?",
    "Do you want to save your progress": "İlerlemeni kaydetmek istiyor musun?",
    "Are you sure": "Emin misin?",
    "Fast travel unavailable": "Hızlı yolculuk kullanılamıyor.",
    "Fast travel is unavailable": "Hızlı yolculuk kullanılamıyor.",
    "You have unlocked a new skill": "Yeni bir yetenek açtın.",
    "New skill unlocked": "Yeni yetenek açıldı.",
    "Achievement unlocked": "Başarım kazanıldı.",
    "Trophy unlocked": "Kupa kazanıldı.",
}
_NORMALISE = re.compile(r"[\s.!?…]+$")


def _key(text: str) -> str:
    return _NORMALISE.sub("", re.sub(r"\s+", " ", text.strip())).lower()


MEMORY = {_key(source): target for source, target in _MEMORY_SOURCE.items()}


def memory_lookup(text: str) -> str | None:
    return MEMORY.get(_key(text))
