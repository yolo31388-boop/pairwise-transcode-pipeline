"""Batch transcode pipeline helpers."""

LADDER = [(2160, 9000), (1080, 5000), (720, 2800), (480, 1400), (360, 800)]

# Filters the pipeline is allowed to emit.  The value is the inclusive
# (minimum, maximum) argument count; ``None`` means "unbounded".
FILTER_SPECS = {
    "scale": (2, 2),
    "scale2ref": (2, 2),
    "crop": (2, 4),
    "pad": (2, 4),
    "drawtext": (1, None),
    "overlay": (1, 4),
    "subtitles": (1, 1),
    "ass": (1, 1),
    "format": (1, 1),
    "fps": (1, 1),
    "setpts": (1, 1),
    "trim": (2, 2),
    "setdar": (1, 1),
    "setsar": (1, 1),
    "transpose": (1, 1),
    "rotate": (1, 1),
    "hflip": (0, 0),
    "vflip": (0, 0),
    "null": (0, 0),
    "showinfo": (0, 0),
    "yadif": (0, 2),
    "bwdif": (0, 2),
    "deinterlace": (0, 1),
    "fieldorder": (1, 1),
    "telecine": (0, 1),
    "tonemap": (1, 2),
    "zscale": (1, None),
    "eq": (1, 3),
    "hue": (1, 3),
    "unsharp": (1, 3),
    "lut": (0, None),
    "curves": (1, None),
    "colorchannelmixer": (1, None),
    "select": (1, 1),
    "concat": (1, 2),
    "split": (1, 1),
    "asplit": (1, 1),
    "amix": (1, 3),
    "aresample": (1, 2),
    "atempo": (1, 1),
    "volume": (1, 1),
    "loudnorm": (0, None),
    "pan": (1, None),
    "channelmap": (1, None),
    "amerge": (1, 1),
    "astats": (0, None),
}

# ISO 639-2 (bibliographic/terminological) and a few common aliases mapped to
# their ISO 639-1 primary subtag.  BCP-47 tags such as ``zh-Hans`` are reduced
# to their primary subtag before lookup.
_LANGUAGE_ALIASES = {
    "chi": "zh", "zho": "zh", "cmn": "zh",
    "eng": "en",
    "jpn": "ja",
    "kor": "ko",
    "fra": "fr", "fre": "fr",
    "deu": "de", "ger": "de",
    "spa": "es",
    "por": "pt",
    "ita": "it",
    "rus": "ru",
    "ara": "ar",
    "nld": "nl", "dut": "nl",
    "pol": "pl",
    "tur": "tr",
    "vie": "vi",
    "tha": "th",
    "ind": "id",
    "msa": "ms", "may": "ms",
    "hin": "hi",
    "ben": "bn",
    "tam": "ta",
    "tel": "te",
    "mal": "ml",
    "kan": "kn",
    "guj": "gu",
    "mar": "mr",
    "pan": "pa",
    "urd": "ur",
    "fas": "fa", "per": "fa",
    "heb": "he",
    "ell": "el", "gre": "el",
    "ces": "cs", "cze": "cs",
    "slk": "sk", "slo": "sk",
    "hun": "hu",
    "ron": "ro", "rum": "ro",
    "bul": "bg",
    "hrv": "hr",
    "srp": "sr",
    "slv": "sl",
    "ukr": "uk",
    "swe": "sv",
    "nor": "no",
    "dan": "da",
    "fin": "fi",
    "isl": "is", "ice": "is",
    "est": "et",
    "lav": "lv",
    "lit": "lt",
    "cat": "ca",
    "eus": "eu", "baq": "eu",
    "glg": "gl",
    "afr": "af",
    "swa": "sw",
    "fil": "tl", "tgl": "tl",
}


def plan_ladder(source_height, source_kbps, cap_kbps=None):
    """Select ladder renditions that never upscale or exceed the source.

    A rendition is usable when its height is at or below the source height
    and its bitrate is at or below both the source bitrate and the optional
    platform cap.  Renditions that would require inventing detail (upscaling
    or bitrate above the source) are dropped rather than clipped.
    """
    ladder = []
    for height, kbps in LADDER:
        if height > source_height:
            continue
        if kbps > source_kbps:
            continue
        if cap_kbps is not None and kbps > cap_kbps:
            continue
        ladder.append(dict(height=height, kbps=kbps))
    return ladder


def _even(value, minimum=2):
    """Round down to the nearest even integer, never below ``minimum``."""
    number = int(round(value))
    number -= number % 2
    return max(minimum, number)


def rendition_size(src_w, src_h, target_h):
    """Scale ``target_h`` to the source aspect ratio, keeping both sides even."""
    if src_w <= 0 or src_h <= 0:
        raise ValueError("source dimensions must be positive")
    height = _even(min(target_h, src_h))
    width = _even(src_w * height / src_h)
    return (width, height)


def _escape_arg(value):
    """Escape characters that would otherwise split an ffmpeg filtergraph."""
    text = str(value)
    return (text.replace("\\", "\\\\")
                .replace(",", "\\,")
                .replace(":", "\\:"))


def build_filter_chain(ops):
    """Build a filtergraph string, preserving the caller's operation order."""
    parts = []
    for op in ops:
        try:
            name, args = op
        except (TypeError, ValueError):
            raise ValueError(f"invalid filter operation: {op!r}") from None
        if name not in FILTER_SPECS:
            raise ValueError(f"unknown filter: {name!r}")
        args = list(args)
        minimum, maximum = FILTER_SPECS[name]
        if len(args) < minimum or (maximum is not None and len(args) > maximum):
            raise ValueError(
                f"filter {name!r} expects {minimum}"
                + (f"..{maximum}" if maximum is not None else "+")
                + f" arguments, got {len(args)}"
            )
        if args:
            parts.append(name + "=" + ":".join(_escape_arg(arg) for arg in args))
        else:
            parts.append(name)
    return ",".join(parts)


def _normalise_language(tag):
    """Reduce a language tag to a comparable ISO 639-1 primary subtag."""
    if not tag:
        return None
    primary = str(tag).strip().lower().replace("_", "-").split("-", 1)[0]
    return _LANGUAGE_ALIASES.get(primary, primary)


def select_subtitle(streams, lang, burn=False):
    """Pick the best subtitle track for ``lang``.

    Language tags are normalised (``chi`` matches ``zh-Hans``), disabled
    tracks are ignored, and a forced track wins over a non-forced one.
    Burning subtitles into the picture requires re-encoding the video.
    """
    wanted = _normalise_language(lang)
    candidates = []
    for position, stream in enumerate(streams):
        if not stream.get("enabled", True):
            continue
        if _normalise_language(stream.get("lang")) != wanted:
            continue
        candidates.append((position, stream))
    if not candidates:
        return None

    _, chosen = min(
        candidates,
        key=lambda item: (not item[1].get("forced", False), item[0]),
    )
    return {
        "index": chosen["index"],
        "burn": bool(burn),
        "reencode": bool(burn),
    }


def resume_plan(total_segments, completed):
    """Resume only past a contiguous run of completed segments.

    A checkpoint with a gap means the work after the gap cannot be trusted,
    so the whole job restarts.  Out-of-range checkpoints are likewise treated
    as corrupt.
    """
    total = int(total_segments)
    completed_set = set(completed)

    invalid = any(
        not isinstance(index, int) or index < 0 or index >= total
        for index in completed_set
    )
    if invalid:
        return {
            "start": 0,
            "remaining": list(range(total)),
            "restart": True,
        }

    start = 0
    while start in completed_set:
        start += 1

    if completed_set != set(range(start)):
        return {
            "start": 0,
            "remaining": list(range(total)),
            "restart": True,
        }

    return {
        "start": start,
        "remaining": list(range(start, total)),
        "restart": False,
    }
