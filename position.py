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


# ==================================================
# 공통 계산
# ==================================================

def clamp(
    value,
    minimum,
    maximum,
):
    return max(
        minimum,
        min(
            value,
            maximum,
        ),
    )


def calculate_exit_percentages(
    candidate,
):
    if config.EXIT_MODE == "FIXED":
        return (
            config.STOP_LOSS_PERCENT,
            config.TAKE_PROFIT_PERCENT,
        )

    atr_percent = float(
        candidate.get(
            "atr_percent",
            0,
        )
    )

    if atr_percent <= 0:
        print(
            "ATR 값이 없어 고정 손절·익절을 사용합니다."
        )

        return (
            config.STOP_LOSS_PERCENT,
            config.TAKE_PROFIT_PERCENT,
        )

    stop_percent = (
        atr_percent
        * config.ATR_STOP_MULTIPLIER
    )

    take_profit_percent = (
        atr_percent
        * config.ATR_TAKE_PROFIT_MULTIPLIER
    )

    stop_percent = clamp(
        stop_percent,
        config.MINIMUM_STOP_PERCENT,
        config.MAXIMUM_STOP_PERCENT,
    )

    take_profit_percent = clamp(
        take_profit_percent,
        config.MINIMUM_TAKE_PROFIT_PERCENT,
        config.MAXIMUM_TAKE_PROFIT_PERCENT,
    )

    return (
        stop_percent,
        take_profit_percent,
    )


def calculate_exit_prices(
    side,
    entry_price,
    stop_percent,
    take_profit_percent,
):
    if side == "LONG":
        stop_price = (
            entry_price
            * (
                1
                - stop_percent / 100
            )
        )

        target_price = (
            entry_price
            * (
                1
                + take_profit_percent
                / 100
            )
        )

    elif side == "SHORT":
        stop_price = (
            entry_price
            * (
                1
                + stop_percent / 100
            )
        )

        target_price = (
            entry_price
            * (
                1
                - take_profit_percent
                / 100
            )
        )

    else:
        raise ValueError(
            f"지원하지 않는 방향: {side}"
        )

    return (
        stop_price,
        target_price,
    )


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


# ==================================================
# 기존 포지션 호환
# ==================================================

def ensure_exit_data(
    symbol,
    position_data,
):
    required_keys = {
        "stop_price",
        "target_price",
        "stop_percent",
        "take_profit_percent",
    }

    if required_keys.issubset(
        position_data.keys()
    ):
        return False

    entry_price = float(
        position_data["entry_price"]
    )

    side = position_data["side"]

    # 예전 포지션에는 ATR 값이 없으므로
    # 고정 손절·익절을 사용
    stop_percent = (
        config.STOP_LOSS_PERCENT
    )

    take_profit_percent = (
        config.TAKE_PROFIT_PERCENT
    )

    stop_price, target_price = (
        calculate_exit_prices(
            side=side,
            entry_price=entry_price,
            stop_percent=stop_percent,
            take_profit_percent=(
                take_profit_percent
            ),
        )
    )

    position_data.update(
        {
            "exit_mode": "FIXED_LEGACY",
            "stop_percent": stop_percent,
            "take_profit_percent": (
                take_profit_percent
            ),
            "stop_price": stop_price,
            "target_price": target_price,
        }
    )

    positions[symbol] = position_data

    return True


# ==================================================
# 진입
# ==================================================

def open_position(candidate):
    global balance

    trading_status = (
        get_trading_status()
    )

    if not trading_status["can_trade"]:
        print(
            "신규 진입 중단: "
            f"{trading_status['reason']}"
        )
        return False

    symbol = candidate["symbol"]
    side = candidate["side"]

    if symbol in positions:
        print(
            f"{symbol}: 이미 보유 중"
        )
        return False

    if is_in_cooldown(symbol):
        remaining_seconds = (
            get_remaining_seconds(
                symbol
            )
        )

        print(
            f"{symbol}: 재진입 대기 중 "
            f"({format_remaining_time(remaining_seconds)})"
        )
        return False

    if (
        len(positions)
        >= config.MAX_POSITIONS
    ):
        print(
            "최대 포지션 개수에 "
            "도달했습니다."
        )
        return False

    current_price = float(
        get_current_price(
            symbol
        )
    )

    investment = (
        balance
        * config.POSITION_SIZE_PERCENT
        / 100
    )

    (
        stop_percent,
        take_profit_percent,
    ) = calculate_exit_percentages(
        candidate
    )

    (
        stop_price,
        target_price,
    ) = calculate_exit_prices(
        side=side,
        entry_price=current_price,
        stop_percent=stop_percent,
        take_profit_percent=(
            take_profit_percent
        ),
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
        "atr": float(
            candidate.get(
                "atr",
                0,
            )
        ),
        "atr_percent": float(
            candidate.get(
                "atr_percent",
                0,
            )
        ),
        "exit_mode": config.EXIT_MODE,
        "stop_percent": stop_percent,
        "take_profit_percent": (
            take_profit_percent
        ),
        "stop_price": stop_price,
        "target_price": target_price,
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
    print(
        f"점수: "
        f"{candidate['score']}점"
    )
    print(
        f"진입가: "
        f"{current_price:,.8f}"
    )
    print(
        f"투입금: "
        f"{investment:,.0f}원"
    )
    print(
        f"청산 방식: "
        f"{config.EXIT_MODE}"
    )
    print(
        f"ATR: "
        f"{candidate.get('atr_percent', 0):.3f}%"
    )
    print(
        f"손절 폭: "
        f"-{stop_percent:.3f}%"
    )
    print(
        f"손절가: "
        f"{stop_price:,.8f}"
    )
    print(
        f"익절 폭: "
        f"+{take_profit_percent:.3f}%"
    )
    print(
        f"익절가: "
        f"{target_price:,.8f}"
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


# ==================================================
# 청산
# ==================================================

def close_position(
    symbol,
    current_price,
    reason,
):
    global balance

    if symbol not in positions:
        return

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

    profit_amount = (
        float(
            position_data["investment"]
        )
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
    print(
        f"청산 이유: {reason}"
    )
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
        f"현재 잔고: "
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

    start_cooldown(symbol)

    print(
        f"{symbol} 재진입 대기 시작"
    )
    print()


# ==================================================
# 포지션 감시
# ==================================================

def monitor_positions():
    if not positions:
        print(
            "현재 보유 포지션 없음"
        )
        return

    state_changed = False

    for symbol in list(
        positions.keys()
    ):
        try:
            position_data = positions[
                symbol
            ]

            if ensure_exit_data(
                symbol,
                position_data,
            ):
                state_changed = True

            current_price = float(
                get_current_price(
                    symbol
                )
            )

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

            stop_price = float(
                position_data[
                    "stop_price"
                ]
            )

            target_price = float(
                position_data[
                    "target_price"
                ]
            )

            print(
                f"[보유] {symbol:<14} "
                f"{position_data['side']:<5} | "
                f"현재 {current_price:,.8f} | "
                f"{net_percent:+.3f}% | "
                f"{unrealized_profit:+,.0f}원 | "
                f"SL {stop_price:,.8f} | "
                f"TP {target_price:,.8f}"
            )

            side = position_data["side"]

            if side == "LONG":
                if current_price <= stop_price:
                    close_position(
                        symbol=symbol,
                        current_price=current_price,
                        reason=(
                            f"손절 "
                            f"-{position_data['stop_percent']:.3f}%"
                        ),
                    )

                elif current_price >= target_price:
                    close_position(
                        symbol=symbol,
                        current_price=current_price,
                        reason=(
                            f"익절 "
                            f"+{position_data['take_profit_percent']:.3f}%"
                        ),
                    )

            elif side == "SHORT":
                if current_price >= stop_price:
                    close_position(
                        symbol=symbol,
                        current_price=current_price,
                        reason=(
                            f"손절 "
                            f"-{position_data['stop_percent']:.3f}%"
                        ),
                    )

                elif current_price <= target_price:
                    close_position(
                        symbol=symbol,
                        current_price=current_price,
                        reason=(
                            f"익절 "
                            f"+{position_data['take_profit_percent']:.3f}%"
                        ),
                    )

        except Exception as error:
            print(
                f"{symbol} 감시 오류: "
                f"{repr(error)}"
            )

    if state_changed:
        save_state(
            balance,
            positions,
        )


# ==================================================
# 후보 진입
# ==================================================

def open_top_candidates(
    candidates,
):
    trading_status = (
        get_trading_status()
    )

    if not trading_status["can_trade"]:
        print(
            "오늘 신규 진입이 "
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
            "최대 포지션에 "
            "도달했습니다."
        )
        return

    opened_count = 0

    for candidate in candidates:
        if (
            opened_count
            >= available_slots
        ):
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
            f"{opened_count}개 진입"
        )


def print_account_status():
    print()
    print("=" * 85)
    print(
        f"가상잔고: "
        f"{balance:,.0f}원"
    )
    print(
        f"보유 포지션: "
        f"{len(positions)}/"
        f"{config.MAX_POSITIONS}"
    )

    for symbol, data in (
        positions.items()
    ):
        print(
            f"- {symbol:<14} "
            f"{data['side']:<5} | "
            f"진입 "
            f"{data['entry_price']:,.8f} | "
            f"SL "
            f"{data.get('stop_price', 0):,.8f} | "
            f"TP "
            f"{data.get('target_price', 0):,.8f}"
        )

    print("=" * 85)