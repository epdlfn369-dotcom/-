import csv
import os
from collections import defaultdict
from datetime import datetime


TRADE_LOG_FILE = "trade_log.csv"


def load_trades():
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
                entry_time = datetime.strptime(
                    row["진입시간"],
                    "%Y-%m-%d %H:%M:%S",
                )

                exit_time = datetime.strptime(
                    row["청산시간"],
                    "%Y-%m-%d %H:%M:%S",
                )

                trades.append(
                    {
                        "entry_time": entry_time,
                        "exit_time": exit_time,
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


def calculate_profit_factor(trades):
    gross_profit = sum(
        trade["profit_amount"]
        for trade in trades
        if trade["profit_amount"] > 0
    )

    gross_loss = abs(
        sum(
            trade["profit_amount"]
            for trade in trades
            if trade["profit_amount"] < 0
        )
    )

    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0

    return gross_profit / gross_loss


def calculate_max_streak(trades, target_result):
    maximum = 0
    current = 0

    for trade in trades:
        if trade["result"] == target_result:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0

    return maximum


def calculate_group_statistics(
    trades,
    key_function,
):
    grouped = defaultdict(list)

    for trade in trades:
        key = key_function(trade)
        grouped[key].append(trade)

    results = []

    for key, group_trades in grouped.items():
        total = len(group_trades)

        wins = sum(
            1
            for trade in group_trades
            if trade["profit_amount"] > 0
        )

        losses = total - wins

        total_profit = sum(
            trade["profit_amount"]
            for trade in group_trades
        )

        average_profit = (
            total_profit / total
            if total > 0
            else 0.0
        )

        win_rate = (
            wins / total * 100
            if total > 0
            else 0.0
        )

        profit_factor = calculate_profit_factor(
            group_trades
        )

        results.append(
            {
                "name": key,
                "trades": total,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "total_profit": total_profit,
                "average_profit": average_profit,
                "profit_factor": profit_factor,
            }
        )

    results.sort(
        key=lambda item: item["total_profit"],
        reverse=True,
    )

    return results


def classify_time_period(hour):
    if 0 <= hour < 6:
        return "새벽"

    if 6 <= hour < 12:
        return "오전"

    if 12 <= hour < 18:
        return "오후"

    return "저녁"


def format_profit_factor(value):
    if value == float("inf"):
        return "∞"

    return f"{value:.2f}"


def print_group_report(
    title,
    statistics,
    limit=None,
):
    print()
    print(title)
    print("-" * 85)

    if not statistics:
        print("분석할 데이터가 없습니다.")
        return

    rows = (
        statistics[:limit]
        if limit is not None
        else statistics
    )

    for item in rows:
        print(
            f"{str(item['name']):<16} | "
            f"{item['trades']:>4}회 | "
            f"승률 {item['win_rate']:>6.2f}% | "
            f"손익 {item['total_profit']:+>10,.0f}원 | "
            f"평균 {item['average_profit']:+>8,.0f}원 | "
            f"PF {format_profit_factor(item['profit_factor']):>5}"
        )


def print_analytics():
    trades = load_trades()

    print()
    print("=" * 85)
    print("BinanceBot 거래 심층 분석")
    print("=" * 85)

    if not trades:
        print("아직 분석할 청산 거래가 없습니다.")
        print("=" * 85)
        return

    total_trades = len(trades)

    winning_trades = [
        trade
        for trade in trades
        if trade["profit_amount"] > 0
    ]

    losing_trades = [
        trade
        for trade in trades
        if trade["profit_amount"] <= 0
    ]

    wins = len(winning_trades)
    losses = len(losing_trades)

    win_rate = wins / total_trades * 100

    total_profit = sum(
        trade["profit_amount"]
        for trade in trades
    )

    average_profit = (
        total_profit / total_trades
    )

    average_holding_seconds = int(
        sum(
            trade["holding_seconds"]
            for trade in trades
        )
        / total_trades
    )

    profit_factor = calculate_profit_factor(
        trades
    )

    maximum_win_streak = calculate_max_streak(
        trades,
        "WIN",
    )

    maximum_loss_streak = calculate_max_streak(
        trades,
        "LOSS",
    )

    best_trade = max(
        trades,
        key=lambda trade: trade["profit_amount"],
    )

    worst_trade = min(
        trades,
        key=lambda trade: trade["profit_amount"],
    )

    print(f"총 거래: {total_trades}회")
    print(f"승리: {wins}회")
    print(f"손실: {losses}회")
    print(f"승률: {win_rate:.2f}%")
    print()

    print(f"누적 손익: {total_profit:+,.0f}원")
    print(f"평균 거래 손익: {average_profit:+,.0f}원")
    print(
        f"Profit Factor: "
        f"{format_profit_factor(profit_factor)}"
    )

    print(
        f"평균 보유시간: "
        f"{average_holding_seconds // 60}분 "
        f"{average_holding_seconds % 60}초"
    )

    print(f"최대 연승: {maximum_win_streak}회")
    print(f"최대 연패: {maximum_loss_streak}회")

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

    side_statistics = calculate_group_statistics(
        trades,
        lambda trade: trade["side"],
    )

    symbol_statistics = calculate_group_statistics(
        trades,
        lambda trade: trade["symbol"],
    )

    weekday_names = {
        0: "월요일",
        1: "화요일",
        2: "수요일",
        3: "목요일",
        4: "금요일",
        5: "토요일",
        6: "일요일",
    }

    weekday_statistics = calculate_group_statistics(
        trades,
        lambda trade: weekday_names[
            trade["entry_time"].weekday()
        ],
    )

    time_statistics = calculate_group_statistics(
        trades,
        lambda trade: classify_time_period(
            trade["entry_time"].hour
        ),
    )

    reason_statistics = calculate_group_statistics(
        trades,
        lambda trade: trade["reason"],
    )

    print_group_report(
        "LONG / SHORT별 성과",
        side_statistics,
    )

    print_group_report(
        "코인별 성과 TOP10",
        symbol_statistics,
        limit=10,
    )

    print_group_report(
        "요일별 성과",
        weekday_statistics,
    )

    print_group_report(
        "시간대별 성과",
        time_statistics,
    )

    print_group_report(
        "청산 이유별 성과",
        reason_statistics,
    )

    print()
    print("=" * 85)


if __name__ == "__main__":
    print_analytics()