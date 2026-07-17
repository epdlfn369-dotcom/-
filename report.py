import csv
import os
from collections import defaultdict


TRADE_LOG_FILE = "trade_log.csv"


def load_trades():
    """
    trade_log.csv 파일에서 거래 내역을 읽는다.
    """

    if not os.path.exists(TRADE_LOG_FILE):
        return []

    trades = []

    with open(
        TRADE_LOG_FILE,
        "r",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            try:
                trades.append(
                    {
                        "symbol": row["종목"],
                        "side": row["방향"],
                        "profit_percent": float(
                            row["수익률"]
                        ),
                        "profit_amount": float(
                            row["손익"]
                        ),
                        "result": row["결과"],
                        "holding_seconds": int(
                            float(row["보유초"])
                        ),
                        "reason": row["청산이유"],
                    }
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

    return trades


def calculate_max_streak(trades, result_name):
    """
    최대 연속 승리 또는 연속 손실을 계산한다.
    """

    maximum = 0
    current = 0

    for trade in trades:
        if trade["result"] == result_name:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0

    return maximum


def format_holding_time(seconds):
    """
    보유시간을 보기 편한 형태로 바꾼다.
    """

    if seconds < 60:
        return f"{seconds}초"

    minutes = seconds // 60

    if minutes < 60:
        return f"{minutes}분"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    return f"{hours}시간 {remaining_minutes}분"


def create_symbol_statistics(trades):
    """
    코인별 거래 횟수와 승률을 계산한다.
    """

    symbol_data = defaultdict(
        lambda: {
            "trades": 0,
            "wins": 0,
            "profit": 0.0,
        }
    )

    for trade in trades:
        symbol = trade["symbol"]

        symbol_data[symbol]["trades"] += 1
        symbol_data[symbol]["profit"] += (
            trade["profit_amount"]
        )

        if trade["result"] == "WIN":
            symbol_data[symbol]["wins"] += 1

    results = []

    for symbol, data in symbol_data.items():
        win_rate = 0.0

        if data["trades"] > 0:
            win_rate = (
                data["wins"]
                / data["trades"]
                * 100
            )

        results.append(
            {
                "symbol": symbol,
                "trades": data["trades"],
                "wins": data["wins"],
                "win_rate": win_rate,
                "profit": data["profit"],
            }
        )

    results.sort(
        key=lambda item: item["profit"],
        reverse=True,
    )

    return results


def print_report():
    trades = load_trades()

    print()
    print("=" * 60)
    print("BinanceBot 가상매매 성적표")
    print("=" * 60)

    if not trades:
        print("아직 청산된 거래 기록이 없습니다.")
        print("=" * 60)
        return

    total_trades = len(trades)

    winning_trades = [
        trade
        for trade in trades
        if trade["result"] == "WIN"
    ]

    losing_trades = [
        trade
        for trade in trades
        if trade["result"] == "LOSS"
    ]

    wins = len(winning_trades)
    losses = len(losing_trades)

    win_rate = (
        wins / total_trades * 100
    )

    total_profit = sum(
        trade["profit_amount"]
        for trade in trades
    )

    average_profit_percent = sum(
        trade["profit_percent"]
        for trade in trades
    ) / total_trades

    average_holding_seconds = int(
        sum(
            trade["holding_seconds"]
            for trade in trades
        ) / total_trades
    )

    average_win = 0.0

    if winning_trades:
        average_win = sum(
            trade["profit_amount"]
            for trade in winning_trades
        ) / len(winning_trades)

    average_loss = 0.0

    if losing_trades:
        average_loss = sum(
            trade["profit_amount"]
            for trade in losing_trades
        ) / len(losing_trades)

    best_trade = max(
        trades,
        key=lambda trade: trade["profit_amount"],
    )

    worst_trade = min(
        trades,
        key=lambda trade: trade["profit_amount"],
    )

    maximum_win_streak = calculate_max_streak(
        trades,
        "WIN",
    )

    maximum_loss_streak = calculate_max_streak(
        trades,
        "LOSS",
    )

    print(f"총 거래 횟수: {total_trades}회")
    print(f"승리: {wins}회")
    print(f"손실: {losses}회")
    print(f"승률: {win_rate:.2f}%")
    print()

    print(f"누적 손익: {total_profit:+,.0f}원")
    print(
        f"평균 거래 수익률: "
        f"{average_profit_percent:+.3f}%"
    )
    print(f"평균 수익금: {average_win:+,.0f}원")
    print(f"평균 손실금: {average_loss:+,.0f}원")
    print()

    print(
        f"최고 거래: "
        f"{best_trade['symbol']} "
        f"{best_trade['side']} "
        f"{best_trade['profit_amount']:+,.0f}원"
    )

    print(
        f"최악 거래: "
        f"{worst_trade['symbol']} "
        f"{worst_trade['side']} "
        f"{worst_trade['profit_amount']:+,.0f}원"
    )

    print(
        f"평균 보유시간: "
        f"{format_holding_time(average_holding_seconds)}"
    )

    print(
        f"최대 연속 승리: "
        f"{maximum_win_streak}회"
    )

    print(
        f"최대 연속 손실: "
        f"{maximum_loss_streak}회"
    )

    symbol_statistics = create_symbol_statistics(
        trades
    )

    print()
    print("코인별 성과")
    print("-" * 60)

    for item in symbol_statistics[:10]:
        print(
            f"{item['symbol']:<14} "
            f"{item['trades']:>3}회 | "
            f"승률 {item['win_rate']:>6.2f}% | "
            f"손익 {item['profit']:+,.0f}원"
        )

    print("=" * 60)


if __name__ == "__main__":
    print_report()