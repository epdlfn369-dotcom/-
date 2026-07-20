import csv
import json
import uuid
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
)

HISTORY_FILE = (
    PROJECT_ROOT
    / "candidate_history.csv"
)

FIELDNAMES = [
    "scan_id",
    "scan_time",
    "rank",
    "selected",
    "selection_reason",
    "symbol",
    "side",
    "score",
    "long_score",
    "short_score",
    "strategy_profile",
    "move_5m",
    "volume_ratio",
    "price_change_24h",
    "ema20",
    "ema50",
    "ema_gap_percent",
    "rsi",
    "adx",
    "atr",
    "atr_percent",
    "quote_volume",
    "higher_timeframe_side",
    "higher_timeframe_adx",
    "higher_timeframe_ema20",
    "higher_timeframe_ema50",
    "reasons",
    "score_components",
]


def to_float(
    value,
    default=0.0,
):
    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def serialize(value):
    if isinstance(
        value,
        (
            dict,
            list,
            tuple,
        ),
    ):
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
        )

    if value is None:
        return ""

    return value


def build_history_row(
    candidate,
    scan_id,
    scan_time,
    rank,
    selected,
    selection_reason,
):
    ema20 = to_float(
        candidate.get(
            "ema20",
            0,
        )
    )

    ema50 = to_float(
        candidate.get(
            "ema50",
            0,
        )
    )

    ema_gap_percent = (
        (
            ema20
            - ema50
        )
        / ema50
        * 100
        if ema50
        else 0.0
    )

    return {
        "scan_id": scan_id,
        "scan_time": scan_time,
        "rank": rank,
        "selected": selected,
        "selection_reason": (
            selection_reason
        ),
        "symbol": candidate.get(
            "symbol",
            "",
        ),
        "side": candidate.get(
            "side",
            "",
        ),
        "score": candidate.get(
            "score",
            0,
        ),
        "long_score": candidate.get(
            "long_score",
            0,
        ),
        "short_score": candidate.get(
            "short_score",
            0,
        ),
        "strategy_profile": (
            candidate.get(
                "strategy_profile",
                "",
            )
        ),
        "move_5m": candidate.get(
            "move_5m",
            0,
        ),
        "volume_ratio": (
            candidate.get(
                "volume_ratio",
                0,
            )
        ),
        "price_change_24h": (
            candidate.get(
                "price_change_24h",
                0,
            )
        ),
        "ema20": ema20,
        "ema50": ema50,
        "ema_gap_percent": (
            ema_gap_percent
        ),
        "rsi": candidate.get(
            "rsi",
            0,
        ),
        "adx": candidate.get(
            "adx",
            0,
        ),
        "atr": candidate.get(
            "atr",
            0,
        ),
        "atr_percent": candidate.get(
            "atr_percent",
            0,
        ),
        "quote_volume": candidate.get(
            "quote_volume",
            0,
        ),
        "higher_timeframe_side": (
            candidate.get(
                "higher_timeframe_side",
                "",
            )
        ),
        "higher_timeframe_adx": (
            candidate.get(
                "higher_timeframe_adx",
                0,
            )
        ),
        "higher_timeframe_ema20": (
            candidate.get(
                "higher_timeframe_ema20",
                0,
            )
        ),
        "higher_timeframe_ema50": (
            candidate.get(
                "higher_timeframe_ema50",
                0,
            )
        ),
        "reasons": candidate.get(
            "reasons",
            [],
        ),
        "score_components": (
            candidate.get(
                "score_components",
                {},
            )
        ),
    }


def save_candidate_history(
    candidates,
    selected_limit,
    blocked_symbols=None,
):
    if not candidates:
        return None

    blocked = set(
        blocked_symbols
        or []
    )

    scan_id = uuid.uuid4().hex

    scan_time = (
        datetime.now()
        .isoformat(
            timespec="seconds"
        )
    )

    selected_count = 0
    rows = []

    for rank, candidate in enumerate(
        candidates,
        start=1,
    ):
        symbol = str(
            candidate.get(
                "symbol",
                "",
            )
        )

        if symbol in blocked:
            selected = False
            selection_reason = (
                "ALREADY_OPEN"
            )

        elif selected_count < selected_limit:
            selected = True
            selection_reason = (
                "TOP_CANDIDATE"
            )

            selected_count += 1

        else:
            selected = False
            selection_reason = (
                "RANK_OUTSIDE_LIMIT"
            )

        rows.append(
            build_history_row(
                candidate=candidate,
                scan_id=scan_id,
                scan_time=scan_time,
                rank=rank,
                selected=selected,
                selection_reason=(
                    selection_reason
                ),
            )
        )

    file_exists = (
        HISTORY_FILE.exists()
        and HISTORY_FILE.stat().st_size
        > 0
    )

    with HISTORY_FILE.open(
        "a",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
            extrasaction="ignore",
        )

        if not file_exists:
            writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    key: serialize(
                        row.get(
                            key,
                            "",
                        )
                    )
                    for key in FIELDNAMES
                }
            )

    return {
        "path": HISTORY_FILE,
        "scan_id": scan_id,
        "candidate_count": len(rows),
        "selected_count": (
            selected_count
        ),
    }
