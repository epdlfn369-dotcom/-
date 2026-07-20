import argparse
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

ENTRY_FILE = (
    PROJECT_ROOT
    / "entry_snapshots.csv"
)

TRADE_FILE = (
    PROJECT_ROOT
    / "trade_log.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "training_dataset.csv"
)


def read_csv_rows(path):
    if not path.exists():
        return []

    for encoding in (
        "utf-8-sig",
        "utf-8",
        "cp949",
    ):
        try:
            with path.open(
                "r",
                encoding=encoding,
                newline="",
            ) as file:
                return list(
                    csv.DictReader(file)
                )

        except UnicodeDecodeError:
            continue

    return []


def first_value(
    row,
    names,
    default="",
):
    for name in names:
        value = row.get(name)

        if value not in (
            None,
            "",
        ):
            return value

    return default


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


def parse_datetime(value):
    if not value:
        return None

    text = str(value).strip()

    for candidate in (
        text,
        text.replace(
            "Z",
            "+00:00",
        ),
    ):
        try:
            parsed = datetime.fromisoformat(
                candidate
            )

            if parsed.tzinfo is not None:
                parsed = parsed.replace(
                    tzinfo=None
                )

            return parsed

        except ValueError:
            pass

    for format_string in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ):
        try:
            return datetime.strptime(
                text,
                format_string,
            )

        except ValueError:
            pass

    return None


def normalize_trade(row):
    return {
        "symbol": str(
            first_value(
                row,
                [
                    "symbol",
                    "coin",
                    "ticker",
                ],
            )
        ).upper(),
        "side": str(
            first_value(
                row,
                [
                    "side",
                    "direction",
                ],
            )
        ).upper(),
        "entry_time": parse_datetime(
            first_value(
                row,
                [
                    "opened_at",
                    "entry_time",
                    "open_time",
                    "created_at",
                ],
            )
        ),
        "exit_time": parse_datetime(
            first_value(
                row,
                [
                    "closed_at",
                    "exit_time",
                    "timestamp",
                    "time",
                ],
            )
        ),
        "entry_price": to_float(
            first_value(
                row,
                [
                    "entry_price",
                    "open_price",
                ],
                0,
            )
        ),
        "exit_price": to_float(
            first_value(
                row,
                [
                    "exit_price",
                    "close_price",
                ],
                0,
            )
        ),
        "profit_amount": to_float(
            first_value(
                row,
                [
                    "profit_amount",
                    "pnl",
                    "profit",
                    "realized_pnl",
                ],
                0,
            )
        ),
        "profit_percent": to_float(
            first_value(
                row,
                [
                    "profit_percent",
                    "net_percent",
                    "pnl_percent",
                    "return_percent",
                ],
                0,
            )
        ),
        "reason": str(
            first_value(
                row,
                [
                    "reason",
                    "exit_reason",
                    "close_reason",
                ],
                "UNKNOWN",
            )
        ),
    }


def match_trade(
    entry,
    trades,
    tolerance_minutes,
):
    symbol = str(
        entry.get(
            "symbol",
            "",
        )
    ).upper()

    side = str(
        entry.get(
            "side",
            "",
        )
    ).upper()

    snapshot_time = parse_datetime(
        entry.get(
            "snapshot_time"
        )
    )

    entry_price = to_float(
        entry.get(
            "entry_price",
            0,
        )
    )

    candidates = []

    for trade in trades:
        if trade["symbol"] != symbol:
            continue

        if (
            trade["side"]
            and side
            and trade["side"] != side
        ):
            continue

        time_reference = (
            trade["entry_time"]
            or trade["exit_time"]
        )

        if (
            snapshot_time is not None
            and time_reference is not None
        ):
            difference = abs(
                (
                    time_reference
                    - snapshot_time
                ).total_seconds()
            )

            if difference > (
                tolerance_minutes
                * 60
            ):
                continue

        price_difference = abs(
            trade["entry_price"]
            - entry_price
        )

        if entry_price > 0:
            price_difference_percent = (
                price_difference
                / entry_price
                * 100
            )
        else:
            price_difference_percent = 0.0

        time_difference = (
            abs(
                (
                    time_reference
                    - snapshot_time
                ).total_seconds()
            )
            if (
                snapshot_time is not None
                and time_reference is not None
            )
            else float("inf")
        )

        candidates.append(
            (
                time_difference,
                price_difference_percent,
                trade,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    return candidates[0][2]


def safe_json(value):
    if not value:
        return {}

    try:
        parsed = json.loads(
            value
        )

        return (
            parsed
            if isinstance(
                parsed,
                dict,
            )
            else {}
        )

    except (
        json.JSONDecodeError,
        TypeError,
    ):
        return {}


def build_dataset(
    tolerance_minutes,
):
    entries = read_csv_rows(
        ENTRY_FILE
    )

    trades = [
        normalize_trade(row)
        for row in read_csv_rows(
            TRADE_FILE
        )
    ]

    output_rows = []
    matched_count = 0

    for entry in entries:
        trade = match_trade(
            entry,
            trades,
            tolerance_minutes,
        )

        matched = trade is not None

        if matched:
            matched_count += 1

        profit_amount = (
            trade["profit_amount"]
            if matched
            else ""
        )

        profit_percent = (
            trade["profit_percent"]
            if matched
            else ""
        )

        if not matched:
            outcome = "OPEN_OR_UNMATCHED"

        elif trade["profit_amount"] > 0:
            outcome = "WIN"

        elif trade["profit_amount"] < 0:
            outcome = "LOSS"

        else:
            outcome = "BREAKEVEN"

        components = safe_json(
            entry.get(
                "score_components",
                "",
            )
        )

        output = dict(entry)

        output.update(
            {
                "trade_matched": matched,
                "outcome": outcome,
                "exit_time": (
                    trade["exit_time"]
                    .isoformat(
                        timespec="seconds"
                    )
                    if (
                        matched
                        and trade["exit_time"]
                        is not None
                    )
                    else ""
                ),
                "exit_price": (
                    trade["exit_price"]
                    if matched
                    else ""
                ),
                "profit_amount": (
                    profit_amount
                ),
                "profit_percent": (
                    profit_percent
                ),
                "exit_reason": (
                    trade["reason"]
                    if matched
                    else ""
                ),
                "holding_minutes": (
                    (
                        trade["exit_time"]
                        - trade["entry_time"]
                    ).total_seconds()
                    / 60
                    if (
                        matched
                        and trade["entry_time"]
                        is not None
                        and trade["exit_time"]
                        is not None
                    )
                    else ""
                ),
                "component_volume": (
                    components.get(
                        "volume",
                        0,
                    )
                ),
                "component_ema_trend": (
                    components.get(
                        "ema_trend",
                        0,
                    )
                ),
                "component_move_5m": (
                    components.get(
                        "move_5m",
                        0,
                    )
                ),
                "component_rsi": (
                    components.get(
                        "rsi",
                        0,
                    )
                ),
                "component_change_24h": (
                    components.get(
                        "change_24h",
                        0,
                    )
                ),
                "component_overheat": (
                    components.get(
                        "change_24h_overheat",
                        0,
                    )
                ),
            }
        )

        output_rows.append(
            output
        )

    return (
        output_rows,
        len(entries),
        matched_count,
    )


def write_dataset(rows):
    if not rows:
        return

    fieldnames = []

    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(
                    key
                )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(
            rows
        )


def print_summary(
    rows,
    total_entries,
    matched_count,
):
    wins = sum(
        1
        for row in rows
        if row["outcome"] == "WIN"
    )

    losses = sum(
        1
        for row in rows
        if row["outcome"] == "LOSS"
    )

    breakeven = sum(
        1
        for row in rows
        if row["outcome"]
        == "BREAKEVEN"
    )

    unmatched = (
        total_entries
        - matched_count
    )

    print()
    print("=" * 84)
    print(
        "BinanceBot 학습 데이터셋 생성"
    )
    print("=" * 84)
    print(
        f"진입 스냅샷: "
        f"{total_entries}건"
    )
    print(
        f"청산 결과 연결: "
        f"{matched_count}건"
    )
    print(
        f"미연결·보유 중: "
        f"{unmatched}건"
    )
    print(
        f"WIN / LOSS / BE: "
        f"{wins} / {losses} / {breakeven}"
    )
    print(
        f"출력 파일: "
        f"{OUTPUT_FILE}"
    )
    print("=" * 84)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "진입 스냅샷과 청산 결과를 "
            "연결해 학습 데이터셋 생성"
        )
    )

    parser.add_argument(
        "--tolerance",
        type=int,
        default=10,
        help=(
            "진입 시각 매칭 허용 오차(분). "
            "기본값 10"
        ),
    )

    args = parser.parse_args()

    if args.tolerance < 0:
        parser.error(
            "--tolerance는 0 이상이어야 합니다."
        )

    rows, total, matched = (
        build_dataset(
            args.tolerance
        )
    )

    write_dataset(
        rows
    )

    print_summary(
        rows,
        total,
        matched,
    )


if __name__ == "__main__":
    main()
