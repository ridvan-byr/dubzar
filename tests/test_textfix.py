import pytest

from dubzar.textfix import Vocabulary, fix_text, text_quality

WORDS = ("the to and of a in is you i for that it looking good okay love low stay tell my wife her will be "
         "published results basil tomato soup day all week running mouth his future we are late do not "
         "don't can't i'm i'll cops everywhere look out first this job clean score no witnesses hello there "
         "she was never same after accident worked hard life give children better").split()


@pytest.fixture(scope="module")
def vocab():
    return Vocabulary({w: -3.0 - i * 0.01 for i, w in enumerate(WORDS)})


@pytest.mark.parametrize("read,expected", [
    ("Okay, Iooking good.", "Okay, looking good."),             # capital I read for a lower-case l
    ("Stay Iow.", "Stay low."),
    ("Tell my wife I Iove her.", "Tell my wife I love her."),   # the pronoun I stays, the misread one is fixed
    ("The soup is basi].", "The soup is basil."),                # a bracket read for an l
    ("The rezultz will be published.", "The results will be published."),
    ("He worked hard for a better füture.", "He worked hard for a better future."),   # Turkish engine letters
    ("Ali week.", "All week."),
])
def test_common_misreadings_are_repaired(vocab, read, expected):
    assert fix_text(read, vocab) == expected


def test_a_misread_first_word_is_capitalised_again(vocab):
    assert fix_text("Iooking good.", vocab) == "Looking good."


@pytest.mark.parametrize("read,expected", [
    ("I dont know", "I don't know"),
    ("Im late", "I'm late"),
    ("We cant do this", "We can't do this"),
])
def test_missing_apostrophes_are_put_back(vocab, read, expected):
    assert fix_text(read, vocab) == expected


@pytest.mark.parametrize("text", [
    "Donnie said hello there.",           # a name the vocabulary has never seen
    "Look out! Cops everywhere.",
    "She was never the same after the accident.",
    "I'll do it, don't worry.",
    "At 5:30 we leave, 100%.",
])
def test_correct_text_is_left_alone(vocab, text):
    assert fix_text(text, vocab) == text


def test_names_in_the_middle_of_a_sentence_are_not_rewritten(vocab):
    assert fix_text("Tell Brian the job is clean.", vocab) == "Tell Brian the job is clean."


def test_stray_symbols_are_cleaned_but_punctuation_stays(vocab):
    assert fix_text("Look out• the cops’ job…", vocab) == "Look out the cops' job…"


def test_quality_prefers_real_text_over_garbage(vocab):
    good = text_quality("The job was never the same after the accident.", vocab)
    garbled = text_quality("Tiıe zzierıziz zil e.'.perirnenz", vocab)

    assert good > 0.9 and garbled < 0.3


def test_quality_of_nothing_is_zero(vocab):
    assert text_quality("", vocab) == 0.0


@pytest.fixture(scope="module")
def real_like():
    """Frequencies like the real vocabulary: common words around -3..-9, rare ones around -11."""
    return Vocabulary({"all": -6.2, "ali": -10.7, "next": -8.2, "nest": -11.6, "week": -8.6, "the": -3.5, "tell": -7.0,
                       "news": -8.0, "coast": -10.8, "mouth": -9.9, "test": -8.9})


@pytest.mark.parametrize("read,expected", [
    ("the ali week", "the all week"),                    # a rare name-like word where the common one fits
    ("the nezt test", "the next test"),          # z read for x: 'next' beats 'nest'
    ("the weeh", "the week"),                    # h read for k
])
def test_rare_words_are_replaced_by_much_commoner_lookalikes(real_like, read, expected):
    assert fix_text(read, real_like) == expected


@pytest.mark.parametrize("text", [
    "Tell Ali the news",         # a capitalised word may be a name
    "the coast",                 # rare but real, no commoner lookalike
    "the mouth",
])
def test_real_rare_words_and_names_stay(real_like, text):
    assert fix_text(text, real_like) == text


# --- found on a real in-game frame: the game's apostrophe is read as l ! : and words run together ---------------
@pytest.fixture(scope="module")
def game_vocab():
    words = ("i've i'm picked up quite a collection in my travels chaotic times like these people line of work trade "
             "freely sure you can find something to your liking quick hand the sure").split()
    return Vocabulary({w: -6.0 - (i % 7) * 0.5 for i, w in enumerate(words)})


@pytest.mark.parametrize("read,expected", [
    ("Ilve picked up", "I've picked up"),                 # the apostrophe read as l
    ("Itve picked up", "I've picked up"),
    ("lJve picked up", "I've picked up"),
    ("Ilm sure you can find", "I'm sure you can find"),
    ("I m sure you can find", "I'm sure you can find"),   # the apostrophe lost: a lone I and an m
    ("you can't", "you can't"),
])
def test_the_games_apostrophe_misread_as_letters_is_repaired(game_vocab, read, expected):
    assert fix_text(read, game_vocab) == expected


@pytest.mark.parametrize("read,expected", [
    ("In chaotictimes like", "In chaotic times like"),
    ("people trade freely tradefreely", "people trade freely trade freely"),
    ("a collectionin my travels", "a collection in my travels"),
    ("find somethingto your liking", "find something to your liking"),
    ("in mytravels", "in my travels"),
])
def test_words_that_ran_together_are_split_back_apart(game_vocab, read, expected):
    assert fix_text(read, game_vocab) == expected


def test_a_word_is_only_split_when_every_part_is_a_real_word(game_vocab):
    assert fix_text("the Zhangwei trade", game_vocab) == "the Zhangwei trade"      # a name stays whole


def test_stray_capitals_inside_a_word_are_lowered(game_vocab):
    assert fix_text("something to your liKing", game_vocab) == "something to your liking"
    assert fix_text("tHe line", game_vocab) == "the line"


@pytest.mark.parametrize("read,expected", [
    ("the nest. in the week", "the nest. In the week"),       # a new sentence starts with a capital
    ("the nest! all week", "the nest! All week"),
    ("Wait... all week", "Wait... all week"),                  # an ellipsis may continue the sentence
    ("the nest, all week", "the nest, all week"),
])
def test_a_word_right_after_a_sentence_end_gets_its_capital(real_like, read, expected):
    assert fix_text(read, real_like) == expected
