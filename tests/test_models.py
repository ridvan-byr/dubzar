import dataclasses

import pytest

from dubzar.models import Cue, MatchResult


def test_cue_is_immutable_and_roundtrips():
    cue = Cue("a1", "hi", "selam", 1.2)
    changed = dataclasses.replace(cue, text_tr="x")

    assert changed.text_tr == "x"
    assert cue.text_tr == "selam"
    assert cue.speaker is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        cue.text_tr = "y"


def test_match_result_fields():
    result = MatchResult("a1", 12, 9)

    assert (result.line_id, result.offset_frames, result.votes) == ("a1", 12, 9)
