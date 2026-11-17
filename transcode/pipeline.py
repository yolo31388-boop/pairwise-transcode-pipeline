"""Batch transcode pipeline helpers (starter code with known defects)."""

LADDER = [(2160, 9000), (1080, 5000), (720, 2800), (480, 1400), (360, 800)]


def plan_ladder(source_height, source_kbps, cap_kbps=None):
    return [dict(height=h, kbps=k) for h, k in LADDER]


def rendition_size(src_w, src_h, target_h):
    return (1280, 720)


def build_filter_chain(ops):
    parts = []
    for name, args in sorted(ops, key=lambda item: item[0]):
        parts.append(f"{name}=" + ":".join(str(arg) for arg in args))
    return ",".join(parts)


def select_subtitle(streams, lang, burn=False):
    candidates = [s for s in streams if s["lang"] == lang]
    if not candidates:
        return None
    return {"index": candidates[0]["index"], "burn": burn, "reencode": False}


def resume_plan(total_segments, completed):
    return {"start": 0, "remaining": list(range(total_segments)), "restart": False}
