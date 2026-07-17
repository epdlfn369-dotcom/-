import json
import os

from binance_api import get_current_price


STATE_FILE = "state.json"


def load_positions():
    if not os.path.exists(STATE_FILE):
        return 1_000_000.0, {}

    with open(
        STATE_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    balance = float(
        data.get("balance", 1_000_000)
    )

    positions = data.get(
        "positions",
        {},
    )

    return balance, positions


def calculate_profit_percent(
    side,
    entry_price,
    current_price,
):
    if entry_price <= 0:
        return 0.0

    if side == "LONG":
        return (
            (current_price - entry_price)
            / entry_price
            * 100
        )

    if side == "SHORT":
        return (
            (entry_price - current_price)
            / entry_price
            * 100
        )

    return 0.0


def create_position_snapshot():
    balance, positions = load_positions()

    snapshots = []
    total_unrealized_profit = 0.0

    for symbol, position in positions.items():
        try:
            side = position.get("side", "")
            entry_price = float(
                position.get("entry_price", 0)
            )

            investment = float(
                position.get("investment", 0)
            )

            current_price = get_current_price(
                symbol
            )

            profit_percent = (
                calculate_profit_percent(
                    side,
                    entry_price,
                    current_price,
                )
            )

            profit_amount = (
                investment
                * profit_percent
                / 100
            )

            total_unrealized_profit += (
                profit_amount
            )

            snapshots.append(
                {
                    "symbol": symbol,
                    "side": side,
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "investment": investment,
                    "profit_percent": profit_percent,
                    "profit_amount": profit_amount,
                    "score": position.get(
                        "score",
                        0,
                    ),
                    "opened_at": position.get(
                        "opened_at",
                        "",
                    ),
                }
            )

        except Exception as error:
            snapshots.append(
                {
                    "symbol": symbol,
                    "side": position.get(
                        "side",
                        "",
                    ),
                    "error": str(error),
                }
            )

    estimated_balance = (
        balance
        + total_unrealized_profit
    )

    return {
        "balance": balance,
        "positions": snapshots,
        "total_unrealized_profit": (
            total_unrealized_profit
        ),
        "estimated_balance": estimated_balance,
    }


def print_snapshot():
    result = create_position_snapshot()

    print()
    print("=" * 75)
    print("BinanceBot 실시간 포지션 현황")
    print("=" * 75)

    print(
        f"확정 가상잔고: "
        f"{result['balance']:,.0f}원"
    )

    print(
        f"미실현 손익: "
        f"{result['total_unrealized_profit']:+,.0f}원"
    )

    print(
        f"미실현 포함 잔고: "
        f"{result['estimated_balance']:,.0f}원"
    )

    print()

    positions = result["positions"]

    if not positions:
        print("현재 보유 중인 포지션이 없습니다.")
        print("=" * 75)
        return

    for position in positions:
        if "error" in position:
            print(
                f"{position['symbol']} "
                f"가격 확인 실패: "
                f"{position['error']}"
            )
            continue

        print(
            f"{position['symbol']:<14} "
            f"{position['side']:<5} | "
            f"진입 {position['entry_price']:,.8f} | "
            f"현재 {position['current_price']:,.8f} | "
            f"{position['profit_percent']:+.3f}% | "
            f"{position['profit_amount']:+,.0f}원"
        )

    print("=" * 75)


if __name__ == "__main__":
    print_snapshot()