import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

STATE_FILE = PROJECT_ROOT / "state.json"
BOT_STATUS_FILE = PROJECT_ROOT / "bot_status.json"
TRADE_LOG_FILE = PROJECT_ROOT / "trade_log.csv"
LOGS_DIR = PROJECT_ROOT / "logs"


def load_json(path, default):
    if not path.exists():
        return default

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return data

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
    ):
        return default


def parse_number(value, default=0.0):
    try:
        if value in (
            None,
            "",
        ):
            return default

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

    candidates = [
        text,
        text.replace(
            "Z",
            "+00:00",
        ),
    ]

    for candidate in candidates:
        try:
            return datetime.fromisoformat(
                candidate
            )

        except ValueError:
            pass

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ]

    for format_string in formats:
        try:
            return datetime.strptime(
                text,
                format_string,
            )

        except ValueError:
            pass

    return None


def is_today(value):
    parsed = parse_datetime(
        value
    )

    if parsed is None:
        return False

    return (
        parsed.date()
        == datetime.now().date()
    )


def load_trade_rows():
    if not TRADE_LOG_FILE.exists():
        return []

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp949",
    ]

    for encoding in encodings:
        try:
            with TRADE_LOG_FILE.open(
                "r",
                encoding=encoding,
                newline="",
            ) as file:
                return list(
                    csv.DictReader(file)
                )

        except (
            UnicodeDecodeError,
            OSError,
        ):
            continue

    return []


def get_first_value(
    row,
    names,
    default=None,
):
    for name in names:
        if name in row:
            value = row.get(name)

            if value not in (
                None,
                "",
            ):
                return value

    return default


def normalize_trade(row):
    timestamp = get_first_value(
        row,
        [
            "closed_at",
            "exit_time",
            "timestamp",
            "time",
            "created_at",
            "date",
        ],
    )

    symbol = get_first_value(
        row,
        [
            "symbol",
            "coin",
            "ticker",
        ],
        "UNKNOWN",
    )

    side = str(
        get_first_value(
            row,
            [
                "side",
                "direction",
            ],
            "UNKNOWN",
        )
    ).upper()

    reason = str(
        get_first_value(
            row,
            [
                "reason",
                "exit_reason",
                "close_reason",
            ],
            "UNKNOWN",
        )
    )

    profit_amount = parse_number(
        get_first_value(
            row,
            [
                "profit_amount",
                "pnl",
                "profit",
                "realized_pnl",
            ],
            0,
        )
    )

    profit_percent = parse_number(
        get_first_value(
            row,
            [
                "profit_percent",
                "net_percent",
                "pnl_percent",
                "return_percent",
            ],
            0,
        )
    )

    return {
        "timestamp": timestamp,
        "symbol": str(symbol),
        "side": side,
        "reason": reason,
        "profit_amount": (
            profit_amount
        ),
        "profit_percent": (
            profit_percent
        ),
    }


def read_today_log_lines():
    today_name = (
        datetime.now()
        .strftime(
            "%Y-%m-%d.log"
        )
    )

    path = LOGS_DIR / today_name

    if not path.exists():
        return []

    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp949",
    ]

    for encoding in encodings:
        try:
            return path.read_text(
                encoding=encoding,
                errors="replace",
            ).splitlines()

        except OSError:
            continue

    return []


def count_log_metrics(lines):
    metrics = {
        "scan_started": 0,
        "scan_completed": 0,
        "adx_excluded": 0,
        "htf_excluded": 0,
        "volume_excluded": 0,
        "candidates_85_plus": 0,
        "entries": 0,
        "partial_takes": 0,
        "errors": 0,
    }

    for line in lines:
        lowered = line.lower()

        if (
            "스캔 시작"
            in line
            or "scan started"
            in lowered
        ):
            metrics[
                "scan_started"
            ] += 1

        if (
            "스캔 완료"
            in line
            or "scan completed"
            in lowered
        ):
            metrics[
                "scan_completed"
            ] += 1

        if (
            "adx 부족 제외"
            in line
        ):
            metrics[
                "adx_excluded"
            ] += 1

        if (
            "1시간 추세 제외"
            in line
            or "1시간 추세·adx 제외"
            in line.lower()
        ):
            metrics[
                "htf_excluded"
            ] += 1

        if (
            "거래량 부족 제외"
            in line
        ):
            metrics[
                "volume_excluded"
            ] += 1

        if (
            "85점"
            in line
            and (
                "후보"
                in line
                or "long"
                in lowered
                or "short"
                in lowered
            )
        ):
            metrics[
                "candidates_85_plus"
            ] += 1

        if (
            "가상 진입"
            in line
            or "포지션 진입"
            in line
            or "paper entry"
            in lowered
        ):
            metrics[
                "entries"
            ] += 1

        if (
            "가상 부분익절"
            in line
            or "부분익절"
            in line
        ):
            metrics[
                "partial_takes"
            ] += 1

        if (
            "오류"
            in line
            or "실패"
            in line
            or "traceback"
            in lowered
            or "error"
            in lowered
        ):
            metrics[
                "errors"
            ] += 1

    return metrics


def calculate_max_drawdown(
    starting_balance,
    trades,
):
    balance = float(
        starting_balance
    )

    peak = balance
    maximum_drawdown = 0.0

    for trade in trades:
        balance += trade[
            "profit_amount"
        ]

        peak = max(
            peak,
            balance,
        )

        if peak > 0:
            drawdown = (
                (
                    peak
                    - balance
                )
                / peak
                * 100
            )

            maximum_drawdown = max(
                maximum_drawdown,
                drawdown,
            )

    return maximum_drawdown


def format_money(value):
    return f"{value:,.0f}원"


def format_percent(value):
    return f"{value:+.3f}%"


def extract_state_values(state):
    balance = parse_number(
        state.get(
            "balance",
            state.get(
                "current_balance",
                0,
            ),
        )
    )

    positions = state.get(
        "positions",
        {},
    )

    if isinstance(
        positions,
        list,
    ):
        position_count = len(
            positions
        )

    elif isinstance(
        positions,
        dict,
    ):
        position_count = len(
            positions
        )

    else:
        position_count = 0

    return (
        balance,
        position_count,
    )


def main():
    state = load_json(
        STATE_FILE,
        {},
    )

    bot_status = load_json(
        BOT_STATUS_FILE,
        {},
    )

    balance, position_count = (
        extract_state_values(
            state
        )
    )

    starting_balance = parse_number(
        state.get(
            "starting_balance",
            1_000_000,
        ),
        1_000_000,
    )

    normalized_trades = [
        normalize_trade(row)
        for row in load_trade_rows()
    ]

    today_trades = [
        trade
        for trade in normalized_trades
        if is_today(
            trade["timestamp"]
        )
    ]

    wins = [
        trade
        for trade in today_trades
        if trade[
            "profit_amount"
        ] > 0
    ]

    losses = [
        trade
        for trade in today_trades
        if trade[
            "profit_amount"
        ] <= 0
    ]

    total_profit = sum(
        trade["profit_amount"]
        for trade in today_trades
    )

    average_percent = (
        sum(
            trade[
                "profit_percent"
            ]
            for trade in today_trades
        )
        / len(today_trades)
        if today_trades
        else 0.0
    )

    win_rate = (
        len(wins)
        / len(today_trades)
        * 100
        if today_trades
        else 0.0
    )

    maximum_drawdown = (
        calculate_max_drawdown(
            starting_balance,
            today_trades,
        )
    )

    symbol_stats = defaultdict(
        lambda: {
            "count": 0,
            "wins": 0,
            "profit": 0.0,
        }
    )

    reason_counts = Counter()

    for trade in today_trades:
        symbol = trade["symbol"]

        symbol_stats[
            symbol
        ]["count"] += 1

        symbol_stats[
            symbol
        ]["profit"] += trade[
            "profit_amount"
        ]

        if trade[
            "profit_amount"
        ] > 0:
            symbol_stats[
                symbol
            ]["wins"] += 1

        reason_counts[
            trade["reason"]
        ] += 1

    log_lines = (
        read_today_log_lines()
    )

    metrics = count_log_metrics(
        log_lines
    )

    today_text = (
        datetime.now()
        .strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print()
    print("=" * 92)
    print("BinanceBot 가상매매 성과 리포트 v2")
    print("=" * 92)
    print(f"생성 시각: {today_text}")
    print()

    print("현재 상태")
    print("-" * 92)
    print(
        f"현재 잔고: "
        f"{format_money(balance)}"
    )
    print(
        f"보유 포지션: "
        f"{position_count}개"
    )
    print(
        f"봇 상태: "
        f"{bot_status.get('status', 'UNKNOWN')}"
    )
    print(
        f"최근 하트비트: "
        f"{bot_status.get('heartbeat', bot_status.get('last_heartbeat', 'UNKNOWN'))}"
    )

    print()
    print("오늘 스캔·필터")
    print("-" * 92)
    print(
        f"스캔 시작: "
        f"{metrics['scan_started']}회"
    )
    print(
        f"스캔 완료: "
        f"{metrics['scan_completed']}회"
    )
    print(
        f"ADX 제외 로그: "
        f"{metrics['adx_excluded']}회"
    )
    print(
        f"1시간 추세 제외 로그: "
        f"{metrics['htf_excluded']}회"
    )
    print(
        f"거래량 제외 로그: "
        f"{metrics['volume_excluded']}회"
    )
    print(
        f"85점 이상 후보 로그: "
        f"{metrics['candidates_85_plus']}회"
    )
    print(
        f"진입 로그: "
        f"{metrics['entries']}회"
    )
    print(
        f"부분익절 로그: "
        f"{metrics['partial_takes']}회"
    )
    print(
        f"오류·실패 로그: "
        f"{metrics['errors']}회"
    )

    print()
    print("오늘 거래 성과")
    print("-" * 92)
    print(
        f"총 거래: "
        f"{len(today_trades)}회"
    )
    print(
        f"승리/손실: "
        f"{len(wins)} / {len(losses)}"
    )
    print(
        f"승률: "
        f"{win_rate:.2f}%"
    )
    print(
        f"누적 손익: "
        f"{format_money(total_profit)}"
    )
    print(
        f"평균 거래 수익률: "
        f"{format_percent(average_percent)}"
    )
    print(
        f"오늘 최대 낙폭: "
        f"{maximum_drawdown:.3f}%"
    )

    print()
    print("종목별 성과")
    print("-" * 92)

    if not symbol_stats:
        print("오늘 종료된 거래가 없습니다.")

    else:
        ranked_symbols = sorted(
            symbol_stats.items(),
            key=lambda item: item[1][
                "profit"
            ],
            reverse=True,
        )

        for symbol, data in ranked_symbols:
            symbol_win_rate = (
                data["wins"]
                / data["count"]
                * 100
                if data["count"]
                else 0.0
            )

            print(
                f"{symbol:<14} | "
                f"{data['count']:>3}회 | "
                f"승률 "
                f"{symbol_win_rate:>6.2f}% | "
                f"손익 "
                f"{data['profit']:+,.0f}원"
            )

    print()
    print("청산 사유")
    print("-" * 92)

    if not reason_counts:
        print("오늘 청산 기록이 없습니다.")

    else:
        for reason, count in (
            reason_counts.most_common()
        ):
            print(
                f"{reason:<28} | "
                f"{count:>3}회"
            )

    print()
    print("최근 거래")
    print("-" * 92)

    if not today_trades:
        print("오늘 거래 기록이 없습니다.")

    else:
        for trade in today_trades[-10:]:
            print(
                f"{trade['timestamp']} | "
                f"{trade['symbol']:<14} | "
                f"{trade['side']:<5} | "
                f"{trade['profit_percent']:+.3f}% | "
                f"{trade['profit_amount']:+,.0f}원 | "
                f"{trade['reason']}"
            )

    print("=" * 92)


if __name__ == "__main__":
    main()
