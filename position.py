from datetime import datetime

import config
from binance_api import get_current_price
from cooldown import (
    format_remaining_time,
    get_remaining_seconds,
    is_in_cooldown,
    start_cooldown,
)
from risk import get_trading_status
from storage import load_state, save_state
from trade_logger import save_trade


balance, positions = load_state(
    config.STARTING_BALANCE
)


def open_position(candidate):
    global balance

    trading_status = get_trading_status()

    if not trading_status["can_trade"]:
        print(
            "신규 진입 중단: "
            f"{trading_status['reason']}"
        )
        return False

    symbol = candidate["symbol"]
    side = candidate["side"]

    # 이미 보유 중인 종목
    if symbol in positions:
        print(
            f"{symbol}: 이미 보유 중이라 "
            "추가 진입하지 않습니다."
        )
        return False

    # 청산 후 재진입 대기
    if is_in_cooldown(symbol):
        remaining_seconds = (
            get_remaining_seconds(symbol)
        )

        print(
            f"{symbol}: 재진입 대기 중 "
            f"({format_remaining_time(remaining_seconds)} 남음)"
        )
        return False

    # 최대 포지션 제한
    if len(positions) >= config.MAX_POSITIONS:
        print(
            "최대 포지션 개수에 "
            "도달했습니다."
        )
        return False

    current_price = get_current_price(
        symbol
    )

    investment = (
        balance
        * config.POSITION_SIZE_PERCENT
        / 100
    )

    positions[symbol] = {
        "symbol": symbol,
        "side": side,
        "entry_price": current_price,
        "investment": investment,
        "score": candidate["score"],
        "reasons": candidate.get(
            "reasons",
            [],
        ),
        "opened_at": datetime.now(),
    }

    save_state(
        balance,
        positions,
    )

    print()
    print("🚀 가상 포지션 진입")
    print(f"종목: {symbol}")
    print(f"방향: {side}")
    print(f"점수: {candidate['score']}점")
    print(
        f"진입가: "
        f"{current_price:,.8f} USDT"
    )
    print(
        f"가상 투입금: "
        f"{investment:,.0f}원"
    )
    print(
        f"왕복 수수료 가정: "
        f"{config.ROUND_TRIP_FEE_PERCENT}%"
    )

    reasons = candidate.get(
        "reasons",
        [],
    )

    if reasons:
        print(
            "진입 이유: "
            + ", ".join(reasons)
        )

    print()

    return True


def calculate_gross_profit_percent(
    position_data,
    current_price,
):
    entry_price = float(
        position_data["entry_price"]
    )

    side = position_data["side"]

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


def calculate_net_profit_percent(
    position_data,
    current_price,
):
    gross_percent = (
        calculate_gross_profit_percent(
            position_data,
            current_price,
        )
    )

    return (
        gross_percent
        - config.ROUND_TRIP_FEE_PERCENT
    )


def close_position(
    symbol,
    current_price,
    reason,
):
    global balance

    if symbol not in positions:
        return

    position_data = positions[symbol]

    gross_percent = (
        calculate_gross_profit_percent(
            position_data,
            current_price,
        )
    )

    net_percent = (
        calculate_net_profit_percent(
            position_data,
            current_price,
        )
    )

    profit_amount = (
        float(position_data["investment"])
        * net_percent
        / 100
    )

    balance += profit_amount

    print()
    print("💰 가상 포지션 청산")
    print(f"종목: {symbol}")
    print(
        f"방향: "
        f"{position_data['side']}"
    )
    print(
        f"진입가: "
        f"{position_data['entry_price']:,.8f}"
    )
    print(
        f"청산가: "
        f"{current_price:,.8f}"
    )
    print(f"청산 이유: {reason}")
    print(
        f"가격 수익률: "
        f"{gross_percent:+.3f}%"
    )
    print(
        f"수수료 반영: "
        f"{net_percent:+.3f}%"
    )
    print(
        f"손익: "
        f"{profit_amount:+,.0f}원"
    )
    print(
        f"현재 가상잔고: "
        f"{balance:,.0f}원"
    )

    save_trade(
        symbol=symbol,
        side=position_data["side"],
        entry_price=position_data[
            "entry_price"
        ],
        exit_price=current_price,
        investment=position_data[
            "investment"
        ],
        profit_percent=net_percent,
        profit_amount=profit_amount,
        reason=reason,
        opened_at=position_data[
            "opened_at"
        ],
    )

    del positions[symbol]

    save_state(
        balance,
        positions,
    )

    # 청산 직후 재진입 방지
    start_cooldown(symbol)

    remaining_seconds = (
        get_remaining_seconds(symbol)
    )

    print(
        f"{symbol} 재진입 대기 시작: "
        f"{format_remaining_time(remaining_seconds)}"
    )
    print()


def monitor_positions():
    if not positions:
        print("현재 보유 포지션 없음")
        return

    symbols = list(
        positions.keys()
    )

    for symbol in symbols:
        try:
            current_price = (
                get_current_price(symbol)
            )

            position_data = positions[
                symbol
            ]

            gross_percent = (
                calculate_gross_profit_percent(
                    position_data,
                    current_price,
                )
            )

            net_percent = (
                calculate_net_profit_percent(
                    position_data,
                    current_price,
                )
            )

            unrealized_profit = (
                float(
                    position_data[
                        "investment"
                    ]
                )
                * net_percent
                / 100
            )

            print(
                f"[보유] {symbol:<12} "
                f"{position_data['side']:<5} | "
                f"현재가 {current_price:,.8f} | "
                f"가격 {gross_percent:+.3f}% | "
                f"수수료반영 {net_percent:+.3f}% | "
                f"{unrealized_profit:+,.0f}원"
            )

            # 손절과 익절은 가격 움직임 기준
            if (
                gross_percent
                <= -config.STOP_LOSS_PERCENT
            ):
                close_position(
                    symbol=symbol,
                    current_price=current_price,
                    reason=(
                        f"손절 "
                        f"-{config.STOP_LOSS_PERCENT}%"
                    ),
                )

            elif (
                gross_percent
                >= config.TAKE_PROFIT_PERCENT
            ):
                close_position(
                    symbol=symbol,
                    current_price=current_price,
                    reason=(
                        f"익절 "
                        f"+{config.TAKE_PROFIT_PERCENT}%"
                    ),
                )

        except Exception as error:
            print(
                f"{symbol} 가격 확인 오류: "
                f"{repr(error)}"
            )


def open_top_candidates(candidates):
    trading_status = get_trading_status()

    if not trading_status["can_trade"]:
        print()
        print(
            "⛔ 오늘 신규 진입이 "
            "중단됐습니다."
        )
        print(
            trading_status["reason"]
        )
        return

    available_slots = (
        config.MAX_POSITIONS
        - len(positions)
    )

    if available_slots <= 0:
        print(
            "최대 포지션 개수에 "
            "도달했습니다."
        )
        return

    opened_count = 0

    for candidate in candidates:
        if opened_count >= available_slots:
            break

        if open_position(candidate):
            opened_count += 1

    if opened_count == 0:
        print(
            "새롭게 진입한 포지션이 없습니다."
        )
    else:
        print(
            f"신규 포지션 "
            f"{opened_count}개 진입 완료"
        )


def print_account_status():
    print()
    print("=" * 70)
    print(
        f"가상잔고: "
        f"{balance:,.0f}원"
    )
    print(
        f"보유 포지션: "
        f"{len(positions)}/"
        f"{config.MAX_POSITIONS}"
    )

    for symbol, position_data in (
        positions.items()
    ):
        print(
            f"- {symbol:<12} "
            f"{position_data['side']:<5} | "
            f"진입가 "
            f"{position_data['entry_price']:,.8f} | "
            f"투입금 "
            f"{position_data['investment']:,.0f}원"
        )

    print("=" * 70)