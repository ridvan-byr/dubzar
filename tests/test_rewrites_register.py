import pytest

from dubzar.register import is_command, singular_command
from dubzar.rewrites import apply_rewrites


@pytest.mark.parametrize("before,after", [
    ("Your game has been saved.", "Your game has been recorded."),
    ("Progress saved", "Progress recorded"),
    ("Saving your progress...", "Recording your progress..."),
    ("Save the hostages!", "Save the hostages!"),                             # rescuing: untouched
    ("He got jumped outside the bar.", "He was ambushed outside the bar."),
    ("She's a real ball-buster.", "She's a real troublemaker."),
    ("No dice. The deal's off.", "Not happening. The deal's off."),
    ("Some wannabe pushed me.", "Some poser pushed me."),
    ("Rescue them before the timer expires.", "Rescue them before time runs out."),
    ("Somebody must have tipped them off.", "Somebody must have warned them."),
    ("You're really starting to tick me off.", "You're really starting to annoy me."),
    ("Beat it, kid.", "Get lost, kid."),
    ("That was freaking awesome!", "That was really awesome!"),
    ("A great evil stirs beneath the mountain.", "A great evil is awakening beneath the mountain."),
    ("Darkness stirs in the east.", "Darkness is awakening in the east."),
    ("You stand accused of treason against the crown.", "You stand accused of treason against the king."),
    ("Check out this ride!", "Check out this car!"),
    ("Take a ride with me.", "Take a ride with me."),                          # "a ride" is a trip: untouched
    ("I'm going home.", "I'm going home."),
])
def test_rewrites(before, after):
    assert apply_rewrites(before) == after


@pytest.mark.parametrize("english,expected", [
    ("Rescue the hostages before time runs out.", True),
    ("Don't shoot!", True),
    ("Never look back.", True),
    ("Find a way into the control room.", True),
    ("Reach the rooftop and signal the helicopter.", False),                   # two clauses
    ("Keep your voice down, someone's coming.", False),                        # a comma
    ("She rescued the hostages.", False),
    ("Welcome to the city.", False),
    ("", False),
])
def test_is_command(english, expected):
    assert is_command(english) is expected


@pytest.mark.parametrize("before,after", [
    ("Rehineleri kurtarın.", "Rehineleri kurtar."),
    ("Kontrol odasına girmenin bir yolunu bulun.", "Kontrol odasına girmenin bir yolunu bul."),
    ("Ateş etmeyin!", "Ateş etme!"),
    ("Sakin olun.", "Sakin ol."),
    ("Yarın bekleyin", "Yarın bekle"),
    ("Oraya gidin!", "Oraya git!"),
    ("Okuyun.", "Oku."),
    ("Bunu ona verin", "Bunu ona ver"),
    ("Kırmızı minibüsü fark edilmeden takip edin.", "Kırmızı minibüsü fark edilmeden takip et."),
    ("Kapıyı açtı.", "Kapıyı açtı."),                                          # not a plural command
])
def test_singular_command(before, after):
    assert singular_command(before) == after


def test_label_with_a_value_only_is_not_a_speaker():
    from dubzar.textsplit import split_pieces

    assert split_pieces("Fuel: 40%")[0].speaker is None
    assert split_pieces("Experience: 1200 / 2000")[0].speaker is None
    assert split_pieces("Brian: Fuel is low.")[0].speaker == "Brian"


def test_take_out_and_let_it_be_known_are_rewritten():
    from dubzar.rewrites import apply_rewrites

    assert apply_rewrites("Take out the sniper.") == "Kill the sniper."
    assert apply_rewrites("Let it be known that he lied.") == "Everyone should know that he lied."


def test_more_command_verbs():
    from dubzar.register import is_command

    assert is_command("Lure the guards away.")
    assert is_command("Distract the dog.")
