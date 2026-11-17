import pytest

from transcode.pipeline import (build_filter_chain, plan_ladder,
                                rendition_size, resume_plan, select_subtitle)


def test_full_ladder_for_1080p_source():
    assert plan_ladder(1080, 5000) == [
        {"height": 1080, "kbps": 5000},
        {"height": 720, "kbps": 2800},
        {"height": 480, "kbps": 1400},
        {"height": 360, "kbps": 800},
    ]


def test_no_upscale_above_source_height():
    assert [r["height"] for r in plan_ladder(720, 2800)] == [720, 480, 360]


def test_cap_removes_expensive_renditions():
    assert [r["height"] for r in plan_ladder(1080, 5000, cap_kbps=1500)] == [480, 360]


def test_renditions_never_exceed_source_bitrate():
    assert [r["kbps"] for r in plan_ladder(1080, 2000)] == [1400, 800]


def test_rendition_size_keeps_aspect_ratio():
    assert rendition_size(1440, 1080, 720) == (960, 720)


def test_filter_chain_preserves_order():
    ops = [("scale", ["1280", "720"]), ("crop", ["640", "480"])]
    assert build_filter_chain(ops) == "scale=1280:720,crop=640:480"


def test_filter_chain_escapes_special_characters():
    ops = [("drawtext", ["text=a,b:c"])]
    assert build_filter_chain(ops) == "drawtext=text=a\\,b\\:c"


def test_unknown_filter_is_rejected():
    with pytest.raises(ValueError):
        build_filter_chain([("sharpen", ["1.0"])])


def test_missing_filter_argument_is_rejected():
    with pytest.raises(ValueError):
        build_filter_chain([("scale", ["1280"])])


def test_subtitle_matches_language_tag_variants():
    streams = [{"index": 1, "lang": "zh-Hans"}]
    assert select_subtitle(streams, "chi")["index"] == 1


def test_forced_subtitle_wins_when_burning_in():
    streams = [
        {"index": 1, "lang": "zh-Hans", "forced": False},
        {"index": 2, "lang": "zh-Hans", "forced": True},
    ]
    assert select_subtitle(streams, "chi")["index"] == 2


def test_burn_in_requires_reencode():
    streams = [{"index": 1, "lang": "chi"}]
    assert select_subtitle(streams, "chi", burn=True)["reencode"] is True


def test_disabled_subtitle_track_is_skipped():
    streams = [
        {"index": 1, "lang": "zh-Hans", "enabled": False},
        {"index": 2, "lang": "zh-Hans", "enabled": True},
    ]
    assert select_subtitle(streams, "chi")["index"] == 2


def test_resume_plan_skips_completed_prefix():
    plan = resume_plan(6, [0, 1, 2])
    assert plan["start"] == 3
    assert plan["remaining"] == [3, 4, 5]
    assert plan["restart"] is False


def test_resume_plan_restarts_on_checkpoint_gap():
    plan = resume_plan(6, [0, 2])
    assert plan["restart"] is True
    assert plan["start"] == 0
    assert plan["remaining"] == [0, 1, 2, 3, 4, 5]
