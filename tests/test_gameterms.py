from dubzar.gameterms import match_prompt, memory_lookup
from dubzar.textsplit import split_pieces
from dubzar.translate import OpusMtTranslator

# what the model says for a purpose clause ("to open the door"); anything else is not meant to be asked
PURPOSE = {"to open the door": "Kapıyı açmak için", "to repair": "tamir etmek için", "to continue": "devam etmek için",
           "to interact": "etkileşim için", "to sprint": "Sprint"}


def purpose(text):
    return PURPOSE.get(text, text)


def test_a_press_prompt_is_put_together_around_the_purpose_clause():
    assert match_prompt("Press E to open the door.", purpose) == "Kapıyı açmak için E tuşuna bas."


def test_a_hold_prompt_says_hold():
    assert match_prompt("Hold F to repair.", purpose) == "Tamir etmek için F tuşuna basılı tut."


def test_any_button_and_named_keys():
    assert match_prompt("Press any button to continue.", purpose) == "Devam etmek için herhangi bir tuşa bas."
    assert match_prompt("Press Space to open the door.", purpose) == "Kapıyı açmak için Boşluk tuşuna bas."
    assert match_prompt("Press LMB to open the door", purpose) == "Kapıyı açmak için Sol fare tuşuna bas."


def test_a_model_answer_that_is_not_a_purpose_clause_leaves_the_sentence_to_the_model():
    assert match_prompt("Press E to sprint.", purpose) is None             # "Sprint" does not end with "için"


def test_ordinary_text_is_not_a_prompt():
    assert match_prompt("Press the button to see what happens.", purpose) is None
    assert match_prompt("I said press e to open it.", purpose) is None
    assert match_prompt("Please press E to open the door.", purpose) is None


def test_the_memory_matches_whole_lines_only_ignoring_case_and_end_marks():
    assert memory_lookup("Game saved.") == "Oyun kaydedildi."
    assert memory_lookup("game SAVED") == "Oyun kaydedildi."
    assert memory_lookup("Game saved and the door is open.") is None


def test_an_interface_label_is_not_taken_for_a_speaker():
    assert [(p.speaker, p.text) for p in split_pieces("Difficulty: Hard")] == [(None, "Difficulty: Hard")]
    assert [(p.speaker, p.text) for p in split_pieces("Controls: Move, Aim, Fire")] == [(None, "Controls: Move, Aim, Fire")]
    assert [(p.speaker, p.text) for p in split_pieces("Wanted Level: 3 stars.")] == [(None, "Wanted Level: 3 stars.")]


def test_real_speakers_stay_speakers():
    assert [(p.speaker, p.text) for p in split_pieces("Brian: But the count was good.")] == [("Brian", "But the count was good.")]
    assert [(p.speaker, p.text) for p in split_pieces("Mr. Jones: Get in.")] == [("Mr. Jones", "Get in.")]


def test_the_translator_uses_the_prompt_rule_and_the_memory():
    seen = []

    def backend(text):
        seen.append(text)
        return PURPOSE.get(text, "?" + text)

    translator = OpusMtTranslator(backend=backend)

    assert translator.translate("Press E to open the door.") == "Kapıyı açmak için E tuşuna bas."
    assert translator.translate("Game saved.") == "Oyun kaydedildi."
    assert seen == ["to open the door"]                  # the memory line never reached the model
