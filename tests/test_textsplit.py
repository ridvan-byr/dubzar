from dubzar.textsplit import Piece, split_pieces


def test_two_sentences_become_two_pieces():
    assert split_pieces("You think this is a game? People die out here.") == [
        Piece(None, "You think this is a game?"), Piece(None, "People die out here.")]


def test_abbreviations_and_numbers_do_not_split():
    assert len(split_pieces("Dr. Smith went home. He slept.")) == 2
    assert split_pieces("He took 3.5 percent of it.") == [Piece(None, "He took 3.5 percent of it.")]
    assert len(split_pieces("Mr. White said no.")) == 1


def test_ellipsis_followed_by_lowercase_is_one_sentence():
    assert len(split_pieces("Wait... what is that?")) == 1


def test_speaker_label_is_separated_from_the_words():
    assert split_pieces("Brian: But the count was good.") == [Piece("Brian", "But the count was good.")]


def test_speaker_changes_inside_one_subtitle():
    assert split_pieces("Brian: Hello there. Donnie: Hi, Brian.") == [
        Piece("Brian", "Hello there."), Piece("Donnie", "Hi, Brian.")]


def test_later_sentence_of_the_same_speaker_has_no_label():
    assert split_pieces("Brian: Hold on. Something is wrong.") == [
        Piece("Brian", "Hold on."), Piece(None, "Something is wrong.")]


def test_times_and_ordinary_words_before_a_colon_are_not_speakers():
    assert split_pieces("12:30 is too late.") == [Piece(None, "12:30 is too late.")]
    assert split_pieces("Objective: reach the dock.") == [Piece(None, "Objective: reach the dock.")]
    assert split_pieces("he said: wait") == [Piece(None, "he said: wait")]


def test_multi_word_and_upper_case_names_are_speakers():
    assert split_pieces("Mr. White: Sit down.")[0].speaker == "Mr. White"
    assert split_pieces("OFFICER DAVIS: Freeze!")[0] == Piece("OFFICER DAVIS", "Freeze!")


def test_empty_text_has_no_pieces():
    assert split_pieces("   ") == []
