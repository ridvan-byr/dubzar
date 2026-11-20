from dubzar.subtitle_tracker import SubtitleTracker, Update

LINE = "Donnie: Just like that. Just like ol' Donnie does it."


def feed(tracker, *frames):
    return [tracker.update(f) for f in frames]


def test_new_subtitle_is_confirmed_on_the_second_identical_frame():
    t = SubtitleTracker()
    first, second, third = feed(t, [LINE], [LINE], [LINE])

    assert first == Update(None, False)         # one sighting could be a flash or a half-drawn line
    assert second == Update(LINE, False)
    assert third == Update(None, False)          # same subtitle: nothing new


def test_small_ocr_differences_do_not_count_as_a_new_subtitle():
    t = SubtitleTracker()
    feed(t, ["Okay, Iooking good."], ["Okay, looking good."])   # l / I confusion
    update = t.update(["Okay, Iooking good."])

    assert update == Update(None, False)


def test_next_subtitle_replaces_the_previous_one():
    t = SubtitleTracker()
    feed(t, ["Keep your head down."], ["Keep your head down."])
    a, b = feed(t, ["We need more time, they are almost here."], ["We need more time, they are almost here."])

    assert a.text is None and b.text == "We need more time, they are almost here."


def test_subtitle_is_cleared_after_it_stays_gone():
    t = SubtitleTracker(gone_frames=2)
    feed(t, [LINE], [LINE])

    assert t.update([]) == Update(None, False)   # one empty frame: OCR may just have missed it
    assert t.update([]) == Update(None, True)
    assert t.update([]) == Update(None, False)   # clear is reported once


def test_multi_line_subtitle_is_joined_into_one_text():
    t = SubtitleTracker()
    lines = ["Hold on, I think I can see", "something moving over there."]
    feed(t, lines)

    assert t.update(lines).text == "Hold on, I think I can see something moving over there."


def test_junk_lines_are_ignored():
    t = SubtitleTracker()
    junk = ["MKIceAndFire", "5 ft", "N", "12:43", "@@ ##", "OK"]

    assert feed(t, junk, junk, junk) == [Update(None, False)] * 3


def test_our_own_turkish_subtitle_is_never_read_back():
    t = SubtitleTracker()
    turkish = ["Ve şey, duyduğuma göre pek fazla yokmuş"]

    assert feed(t, turkish, turkish)[-1] == Update(None, False)


def test_a_different_text_only_seen_once_does_not_replace_the_current_subtitle():
    t = SubtitleTracker()
    feed(t, [LINE], [LINE])
    flash = t.update(["Totally different words appear for a moment."])
    back = t.update([LINE])

    assert flash.text is None and back == Update(None, False)
