from dubzar.layout import dialogue_block
from dubzar.ocr import OcrLine


def line(text, y, height=0.09, x=0.5):
    return OcrLine(text, x, y, height)


def texts(lines):
    return [l.text for l in lines]


def test_a_hud_hint_far_above_the_dialogue_is_not_part_of_it():
    lines = [line("HOLD TO USE ARMOR PLATES", 0.02), line("Laswell: How many?", 0.46),
             line("Ghost: There's a cove with four boats.", 0.64), line("One bird near the beach.", 0.81)]

    assert texts(dialogue_block(lines)) == ["Laswell: How many?", "Ghost: There's a cove with four boats.",
                                            "One bird near the beach."]


def test_a_speaker_line_a_little_above_the_words_stays_with_them():
    lines = [line("Quick Hand Zhang", 0.28), line("Just between you and me, I'm on a job", 0.47),
             line("for someone I can't name.", 0.65)]

    assert len(dialogue_block(lines)) == 3


def test_when_two_groups_compete_the_one_with_more_words_wins():
    lines = [line("Search for the missing miners", 0.05, height=0.05), line("What do you think? We get out of here.", 0.7),
             line("They never sent you testing before?", 0.85)]

    assert texts(dialogue_block(lines))[0].startswith("What do you think")


def test_a_single_line_is_its_own_block_and_nothing_gives_nothing():
    assert texts(dialogue_block([line("Hello there my friend", 0.5)])) == ["Hello there my friend"]
    assert dialogue_block([]) == []


def test_lines_without_a_known_height_still_group_sensibly():
    lines = [OcrLine("noise", 0.5, 0.02), OcrLine("a real sentence here", 0.5, 0.7), OcrLine("and its second line", 0.5, 0.85)]

    assert texts(dialogue_block(lines)) == ["a real sentence here", "and its second line"]
