import csv
import json
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
)

SNAPSHOT_FILE = (
    PROJECT_ROOT
    / "entry_snapshots.csv"
)

FIELDNAMES = [
    "snapshot_time",
    "symbol",
    "side",
    "score",
    "long_score",
    "short_score",
    "strategy_profile",
    "entry_price",
    "investment",
    "stop_price",
    "target_price",
    "stop_percent",
    "take_profit_percent",
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
    "long_score_components",
    "short_score_components",
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


def save_entry_snapshot(
    candidate,
    entry_price,
    investment,
    stop_price,
    target_price,
    stop_percent,
    take_profit_percent,
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

    row = {
        "snapshot_time": (
            datetime.now()
            .isoformat(
                timespec="seconds"
            )
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
        "entry_price": entry_price,
        "investment": investment,
        "stop_price": stop_price,
        "target_price": target_price,
        "stop_percent": stop_percent,
        "take_profit_percent": (
            take_profit_percent
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
        "long_score_components": (
            candidate.get(
                "long_score_components",
                {},
            )
        ),
        "short_score_components": (
            candidate.get(
                "short_score_components",
                {},
            )
        ),
    }

    file_exists = (
        SNAPSHOT_FILE.exists()
        and SNAPSHOT_FILE.stat().st_size
        > 0
    )

    with SNAPSHOT_FILE.open(
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

    return SNAPSHOT_FILE
