import argparse
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator, EMAIndicator
from ta.volatility import AverageTrueRange

import config
from binance_api import request_json
import engine.strategy as strategy_engine
from engine.strategy_profiles import PROFILES, get_strategy_profile


# ==================================================
# 백테스트 설정
# ==================================================

SYMBOL = "BTCUSDT"
INTERVAL = "5m"
BACKTEST_DAYS = 30

STARTING_BALANCE = config.STARTING_BALANCE
POSITION_SIZE_PERCENT = config.POSITION_SIZE_PERCENT

STOP_LOSS_PERCENT = config.STOP_LOSS_PERCENT
TAKE_PROFIT_PERCENT = config.TAKE_PROFIT_PERCENT
ROUND_TRIP_FEE_PERCENT = config.ROUND_TRIP_FEE_PERCENT

ACTIVE_EXIT_MODE = config.EXIT_MODE

PARTIAL_TAKE_PROFIT_ENABLED = False
PARTIAL_TRIGGER_PERCENT = 1.5
PARTIAL_CLOSE_RATIO = 0.5
MOVE_STOP_TO_BREAKEVEN = True

EMA_FAST = 20
EMA_SLOW = 50
RSI_PERIOD = 14
ATR_PERIOD = 14

REQUEST_DELAY_SECONDS = 0.15


# ==================================================
# 시간 간격 계산
# ==================================================

def get_interval_minutes():
    interval = INTERVAL.lower().strip()

    if interval.endswith("m"):
        return int(interval[:-1])

    if interval.endswith("h"):
        return int(interval[:-1]) * 60

    if interval.endswith("d"):
        return int(interval[:-1]) * 1440

    raise ValueError(
        f"지원하지 않는 봉 간격: {INTERVAL}"
    )


def get_24h_lookback_bars():
    interval_minutes = get_interval_minutes()

    return max(
        1,
        int(1440 / interval_minutes),
    )


def get_momentum_lookback_bars():
    interval_minutes = get_interval_minutes()

    # 실제 전략의 5분 움직임과 최대한 동일하게 맞춤
    return max(
        1,
        int(round(5 / interval_minutes)),
    )


# ==================================================
# 과거 데이터 다운로드
# ==================================================

def datetime_to_milliseconds(value):
    return int(value.timestamp() * 1000)


def download_historical_candles():
    print(
        f"{SYMBOL} 최근 {BACKTEST_DAYS}일 "
        f"{INTERVAL} 캔들 다운로드 중...",
        flush=True,
    )

    end_time = datetime.now(timezone.utc)
    start_time = (
        end_time
        - timedelta(days=BACKTEST_DAYS)
    )

    current_start = (
        datetime_to_milliseconds(
            start_time
        )
    )

    final_end = (
        datetime_to_milliseconds(
            end_time
        )
    )

    all_candles = []

    while current_start < final_end:
        candles = request_json(
            "/fapi/v1/klines",
            {
                "symbol": SYMBOL,
                "interval": INTERVAL,
                "startTime": current_start,
                "endTime": final_end,
                "limit": 1500,
            },
        )

        if not candles:
            break

        all_candles.extend(candles)

        last_open_time = int(
            candles[-1][0]
        )

        next_start = last_open_time + 1

        if next_start <= current_start:
            break

        current_start = next_start

        print(
            f"\r다운로드된 캔들: "
            f"{len(all_candles):,}개",
            end="",
            flush=True,
        )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

        if len(candles) < 1500:
            break

    print()

    if not all_candles:
        raise RuntimeError(
            "캔들 데이터를 가져오지 못했습니다."
        )

    unique_candles = {
        int(candle[0]): candle
        for candle in all_candles
    }

    sorted_candles = [
        unique_candles[key]
        for key in sorted(unique_candles)
    ]

    return sorted_candles


def candles_to_dataframe(candles):
    rows = []

    for candle in candles:
        rows.append(
            {
                "time": pd.to_datetime(
                    int(candle[0]),
                    unit="ms",
                    utc=True,
                ),
                "open": float(
                    candle[1]
                ),
                "high": float(
                    candle[2]
                ),
                "low": float(
                    candle[3]
                ),
                "close": float(
                    candle[4]
                ),
                "volume": float(
                    candle[5]
                ),
            }
        )

    dataframe = pd.DataFrame(
        rows
    )

    # 현재 진행 중일 수 있는 마지막 봉 제외
    if len(dataframe) > 1:
        dataframe = (
            dataframe
            .iloc[:-1]
            .copy()
        )

    return dataframe


# ==================================================
# 지표 계산
# ==================================================

def add_indicators(dataframe):
    dataframe = dataframe.copy()

    dataframe["ema20"] = EMAIndicator(
        close=dataframe["close"],
        window=EMA_FAST,
    ).ema_indicator()

    dataframe["ema50"] = EMAIndicator(
        close=dataframe["close"],
        window=EMA_SLOW,
    ).ema_indicator()

    dataframe["rsi"] = RSIIndicator(
        close=dataframe["close"],
        window=RSI_PERIOD,
    ).rsi()

    dataframe["atr"] = AverageTrueRange(
        high=dataframe["high"],
        low=dataframe["low"],
        close=dataframe["close"],
        window=ATR_PERIOD,
    ).average_true_range()

    dataframe["atr_percent"] = (
        dataframe["atr"]
        / dataframe["close"]
        * 100
    )

    momentum_bars = (
        get_momentum_lookback_bars()
    )

    dataframe["move_5m"] = (
        dataframe["close"]
        .pct_change(
            periods=momentum_bars
        )
        * 100
    )

    dataframe[
        "previous_volume_average"
    ] = (
        dataframe["volume"]
        .shift(1)
        .rolling(window=5)
        .mean()
    )

    dataframe["volume_ratio"] = (
        dataframe["volume"]
        / dataframe[
            "previous_volume_average"
        ]
    )

    lookback_24h = (
        get_24h_lookback_bars()
    )

    dataframe["price_change_24h"] = (
        dataframe["close"]
        .pct_change(
            periods=lookback_24h
        )
        * 100
    )

    dataframe = (
        dataframe
        .dropna()
        .reset_index(drop=True)
    )

    return dataframe


# ==================================================
# 실제 전략 엔진을 사용하는 진입 신호
# ==================================================

def build_strategy_item(row):
    return {
        "symbol": SYMBOL,
        "current_price": float(
            row["close"]
        ),
        "move_5m": float(
            row["move_5m"]
        ),
        "volume_ratio": float(
            row["volume_ratio"]
        ),
        "price_change_24h": float(
            row["price_change_24h"]
        ),
        "ema20": float(
            row["ema20"]
        ),
        "ema50": float(
            row["ema50"]
        ),
        "rsi": float(
            row["rsi"]
        ),

        # 현재 strategy.py에는 직접 사용되지 않지만,
        # 실거래 스캐너 결과 구조와 맞추기 위해 포함
        "atr": float(
            row["atr"]
        ),
        "atr_percent": float(
            row["atr_percent"]
        ),
    }


def get_entry_result(row):
    strategy_item = (
        build_strategy_item(
            row
        )
    )

    return strategy_engine.calculate_score(
        strategy_item
    )


# ==================================================
# 손절·익절 가격
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
    row,
    exit_mode,
):
    normalized_mode = str(
        exit_mode
    ).upper()

    if normalized_mode == "FIXED":
        return (
            STOP_LOSS_PERCENT,
            TAKE_PROFIT_PERCENT,
        )

    atr_percent = float(
        row["atr_percent"]
    )

    if atr_percent <= 0:
        return (
            STOP_LOSS_PERCENT,
            TAKE_PROFIT_PERCENT,
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
                + take_profit_percent / 100
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
                - take_profit_percent / 100
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
    side,
    entry_price,
    exit_price,
):
    if side == "LONG":
        return (
            (
                exit_price
                - entry_price
            )
            / entry_price
            * 100
        )

    return (
        (
            entry_price
            - exit_price
        )
        / entry_price
        * 100
    )


def calculate_position_result(
    position,
    final_exit_price,
):
    remaining_ratio = float(
        position.get(
            "remaining_ratio",
            1.0,
        )
    )

    partial_gross_percent = float(
        position.get(
            "partial_gross_percent",
            0.0,
        )
    )

    final_gross_percent = (
        calculate_gross_profit_percent(
            position["side"],
            position["entry_price"],
            final_exit_price,
        )
    )

    weighted_gross_percent = (
        partial_gross_percent
        + final_gross_percent
        * remaining_ratio
    )

    net_percent = (
        weighted_gross_percent
        - ROUND_TRIP_FEE_PERCENT
    )

    profit_amount = (
        position["investment"]
        * net_percent
        / 100
    )

    return (
        weighted_gross_percent,
        net_percent,
        profit_amount,
    )


# ==================================================
# 백테스트 실행
# ==================================================

def run_backtest(
    dataframe,
    exit_mode=None,
    partial_exit_enabled=None,
):
    selected_exit_mode = (
        exit_mode
        or ACTIVE_EXIT_MODE
    ).upper()

    selected_partial_exit = (
        PARTIAL_TAKE_PROFIT_ENABLED
        if partial_exit_enabled is None
        else bool(partial_exit_enabled)
    )

    balance = float(
        STARTING_BALANCE
    )

    peak_balance = balance
    maximum_drawdown = 0.0

    position = None
    trades = []

    signal_count = 0

    for index in range(
        len(dataframe)
    ):
        row = dataframe.iloc[index]

        # ------------------------------------------
        # 기존 포지션 청산 검사
        # ------------------------------------------

        if position is not None:
            side = position["side"]

            stop_price = position[
                "stop_price"
            ]

            target_price = position[
                "target_price"
            ]

            exit_price = None
            exit_reason = None

            if side == "LONG":
                stop_touched = (
                    row["low"]
                    <= stop_price
                )

                target_touched = (
                    row["high"]
                    >= target_price
                )

                # 같은 봉에서 둘 다 닿으면
                # 보수적으로 손절 우선
                if stop_touched:
                    exit_price = (
                        stop_price
                    )

                    exit_reason = (
                        "STOP"
                    )

                elif target_touched:
                    exit_price = (
                        target_price
                    )

                    exit_reason = (
                        "TAKE_PROFIT"
                    )

            else:
                stop_touched = (
                    row["high"]
                    >= stop_price
                )

                target_touched = (
                    row["low"]
                    <= target_price
                )

                if stop_touched:
                    exit_price = (
                        stop_price
                    )

                    exit_reason = (
                        "STOP"
                    )

                elif target_touched:
                    exit_price = (
                        target_price
                    )

                    exit_reason = (
                        "TAKE_PROFIT"
                    )

            if exit_price is not None:
                (
                    gross_percent,
                    net_percent,
                    profit_amount,
                ) = calculate_position_result(
                    position,
                    exit_price,
                )

                balance += profit_amount

                trades.append(
                    {
                        "side": side,
                        "entry_time": (
                            position[
                                "entry_time"
                            ]
                        ),
                        "exit_time": (
                            row["time"]
                        ),
                        "entry_price": (
                            position[
                                "entry_price"
                            ]
                        ),
                        "exit_price": (
                            exit_price
                        ),
                        "gross_percent": (
                            gross_percent
                        ),
                        "net_percent": (
                            net_percent
                        ),
                        "profit_amount": (
                            profit_amount
                        ),
                        "reason": (
                            exit_reason
                        ),
                        "exit_mode": (
                            position[
                                "exit_mode"
                            ]
                        ),
                        "stop_percent": (
                            position[
                                "stop_percent"
                            ]
                        ),
                        "take_profit_percent": (
                            position[
                                "take_profit_percent"
                            ]
                        ),
                        "partial_exit_enabled": (
                            position[
                                "partial_exit_enabled"
                            ]
                        ),
                        "partial_taken": (
                            position[
                                "partial_taken"
                            ]
                        ),
                        "entry_score": (
                            position[
                                "entry_score"
                            ]
                        ),
                        "entry_reasons": (
                            position[
                                "entry_reasons"
                            ]
                        ),
                    }
                )

                peak_balance = max(
                    peak_balance,
                    balance,
                )

                drawdown = (
                    (
                        peak_balance
                        - balance
                    )
                    / peak_balance
                    * 100
                )

                maximum_drawdown = max(
                    maximum_drawdown,
                    drawdown,
                )

                position = None

                # 같은 봉에서 청산 후
                # 재진입하지 않음
                continue

            # --------------------------------------
            # 부분익절 + 본절 이동
            # --------------------------------------
            if (
                selected_partial_exit
                and not position[
                    "partial_taken"
                ]
            ):
                partial_price = position[
                    "partial_price"
                ]

                if side == "LONG":
                    partial_touched = (
                        row["high"]
                        >= partial_price
                    )
                else:
                    partial_touched = (
                        row["low"]
                        <= partial_price
                    )

                if partial_touched:
                    partial_gross = (
                        calculate_gross_profit_percent(
                            side,
                            position[
                                "entry_price"
                            ],
                            partial_price,
                        )
                    )

                    close_ratio = (
                        position[
                            "partial_close_ratio"
                        ]
                    )

                    position[
                        "partial_gross_percent"
                    ] = (
                        partial_gross
                        * close_ratio
                    )

                    position[
                        "remaining_ratio"
                    ] = (
                        1.0
                        - close_ratio
                    )

                    position[
                        "partial_taken"
                    ] = True

                    if MOVE_STOP_TO_BREAKEVEN:
                        position[
                            "stop_price"
                        ] = position[
                            "entry_price"
                        ]

                    # 같은 봉에서 최종 익절까지 닿은 경우
                    if side == "LONG":
                        target_touched = (
                            row["high"]
                            >= target_price
                        )
                    else:
                        target_touched = (
                            row["low"]
                            <= target_price
                        )

                    if target_touched:
                        exit_price = (
                            target_price
                        )
                        exit_reason = (
                            "PARTIAL_AND_TAKE_PROFIT"
                        )

                        (
                            gross_percent,
                            net_percent,
                            profit_amount,
                        ) = calculate_position_result(
                            position,
                            exit_price,
                        )

                        balance += profit_amount

                        trades.append(
                            {
                                "side": side,
                                "entry_time": position[
                                    "entry_time"
                                ],
                                "exit_time": row["time"],
                                "entry_price": position[
                                    "entry_price"
                                ],
                                "exit_price": exit_price,
                                "gross_percent": gross_percent,
                                "net_percent": net_percent,
                                "profit_amount": profit_amount,
                                "reason": exit_reason,
                                "exit_mode": position[
                                    "exit_mode"
                                ],
                                "stop_percent": position[
                                    "stop_percent"
                                ],
                                "take_profit_percent": position[
                                    "take_profit_percent"
                                ],
                                "partial_exit_enabled": True,
                                "partial_taken": True,
                                "entry_score": position[
                                    "entry_score"
                                ],
                                "entry_reasons": position[
                                    "entry_reasons"
                                ],
                            }
                        )

                        peak_balance = max(
                            peak_balance,
                            balance,
                        )

                        drawdown = (
                            (
                                peak_balance
                                - balance
                            )
                            / peak_balance
                            * 100
                        )

                        maximum_drawdown = max(
                            maximum_drawdown,
                            drawdown,
                        )

                        position = None
                        continue

        # ------------------------------------------
        # 신규 진입
        # ------------------------------------------

        if position is None:
            strategy_result = (
                get_entry_result(
                    row
                )
            )

            signal = (
                strategy_result[
                    "side"
                ]
            )

            if signal == "NONE":
                continue

            signal_count += 1

            entry_price = float(
                row["close"]
            )

            (
                stop_percent,
                take_profit_percent,
            ) = calculate_exit_percentages(
                row,
                selected_exit_mode,
            )

            (
                stop_price,
                target_price,
            ) = calculate_exit_prices(
                side=signal,
                entry_price=entry_price,
                stop_percent=stop_percent,
                take_profit_percent=(
                    take_profit_percent
                ),
            )

            investment = (
                balance
                * POSITION_SIZE_PERCENT
                / 100
            )

            position = {
                "side": signal,
                "entry_time": (
                    row["time"]
                ),
                "entry_price": (
                    entry_price
                ),
                "stop_price": (
                    stop_price
                ),
                "target_price": (
                    target_price
                ),
                "exit_mode": (
                    selected_exit_mode
                ),
                "stop_percent": (
                    stop_percent
                ),
                "take_profit_percent": (
                    take_profit_percent
                ),
                "partial_exit_enabled": (
                    selected_partial_exit
                ),
                "partial_trigger_percent": (
                    PARTIAL_TRIGGER_PERCENT
                ),
                "partial_close_ratio": (
                    PARTIAL_CLOSE_RATIO
                ),
                "partial_price": (
                    entry_price
                    * (
                        1
                        + (
                            PARTIAL_TRIGGER_PERCENT
                            / 100
                        )
                        * (
                            1
                            if signal == "LONG"
                            else -1
                        )
                    )
                ),
                "partial_taken": False,
                "partial_gross_percent": 0.0,
                "remaining_ratio": 1.0,
                "investment": (
                    investment
                ),
                "entry_score": (
                    strategy_result[
                        "score"
                    ]
                ),
                "entry_reasons": (
                    strategy_result[
                        "reasons"
                    ]
                ),
            }

    # 데이터 종료 시 열린 포지션 강제 청산
    if position is not None:
        last_row = (
            dataframe.iloc[-1]
        )

        exit_price = float(
            last_row["close"]
        )

        (
            gross_percent,
            net_percent,
            profit_amount,
        ) = calculate_position_result(
            position,
            exit_price,
        )

        balance += profit_amount

        trades.append(
            {
                "side": (
                    position["side"]
                ),
                "entry_time": (
                    position[
                        "entry_time"
                    ]
                ),
                "exit_time": (
                    last_row["time"]
                ),
                "entry_price": (
                    position[
                        "entry_price"
                    ]
                ),
                "exit_price": (
                    exit_price
                ),
                "gross_percent": (
                    gross_percent
                ),
                "net_percent": (
                    net_percent
                ),
                "profit_amount": (
                    profit_amount
                ),
                "reason": (
                    "END_OF_DATA"
                ),
                "exit_mode": (
                    position[
                        "exit_mode"
                    ]
                ),
                "stop_percent": (
                    position[
                        "stop_percent"
                    ]
                ),
                "take_profit_percent": (
                    position[
                        "take_profit_percent"
                    ]
                ),
                "partial_exit_enabled": (
                    position[
                        "partial_exit_enabled"
                    ]
                ),
                "partial_taken": (
                    position[
                        "partial_taken"
                    ]
                ),
                "entry_score": (
                    position[
                        "entry_score"
                    ]
                ),
                "entry_reasons": (
                    position[
                        "entry_reasons"
                    ]
                ),
            }
        )

    return {
        "starting_balance": (
            STARTING_BALANCE
        ),
        "ending_balance": (
            balance
        ),
        "maximum_drawdown": (
            maximum_drawdown
        ),
        "signal_count": (
            signal_count
        ),
        "exit_mode": (
            selected_exit_mode
        ),
        "partial_exit_enabled": (
            selected_partial_exit
        ),
        "trades": trades,
    }


# ==================================================
# 결과 출력
# ==================================================

def calculate_maximum_streak(
    trades,
    win,
):
    maximum = 0
    current = 0

    for trade in trades:
        is_win = (
            trade["profit_amount"]
            > 0
        )

        if is_win == win:
            current += 1

            maximum = max(
                maximum,
                current,
            )
        else:
            current = 0

    return maximum



def print_score_band_report(trades):
    bands = [
        (65, 69),
        (70, 74),
        (75, 79),
        (80, 84),
        (85, 89),
        (90, 999),
    ]

    print()
    print("진입 점수대별 성과")
    print("-" * 72)

    for minimum, maximum in bands:
        band_trades = [
            trade
            for trade in trades
            if minimum
            <= trade["entry_score"]
            <= maximum
        ]

        if not band_trades:
            continue

        wins = [
            trade
            for trade in band_trades
            if trade["profit_amount"] > 0
        ]

        win_rate = (
            len(wins)
            / len(band_trades)
            * 100
        )

        total_profit = sum(
            trade["profit_amount"]
            for trade in band_trades
        )

        average_percent = (
            sum(
                trade["net_percent"]
                for trade in band_trades
            )
            / len(band_trades)
        )

        label = (
            f"{minimum}+"
            if maximum >= 999
            else f"{minimum}-{maximum}"
        )

        print(
            f"{label:>7}점 | "
            f"{len(band_trades):>3}회 | "
            f"승률 {win_rate:>6.2f}% | "
            f"평균 {average_percent:+.3f}% | "
            f"손익 {total_profit:+,.0f}원"
        )


def print_exit_reason_report(trades):
    reasons = {}

    for trade in trades:
        reason = trade["reason"]

        if reason not in reasons:
            reasons[reason] = {
                "count": 0,
                "profit": 0.0,
            }

        reasons[reason]["count"] += 1
        reasons[reason]["profit"] += (
            trade["profit_amount"]
        )

    print()
    print("청산 사유별 성과")
    print("-" * 72)

    for reason, data in sorted(
        reasons.items()
    ):
        print(
            f"{reason:<16} | "
            f"{data['count']:>3}회 | "
            f"{data['profit']:+,.0f}원"
        )


def print_reason_combination_report(trades):
    combinations = {}

    for trade in trades:
        reasons = trade.get(
            "entry_reasons",
            [],
        )

        if reasons:
            key = " + ".join(
                sorted(reasons)
            )
        else:
            key = "이유 없음"

        if key not in combinations:
            combinations[key] = {
                "count": 0,
                "wins": 0,
                "profit": 0.0,
                "percent_sum": 0.0,
            }

        combinations[key]["count"] += 1
        combinations[key]["profit"] += float(
            trade["profit_amount"]
        )
        combinations[key]["percent_sum"] += float(
            trade["net_percent"]
        )

        if trade["profit_amount"] > 0:
            combinations[key]["wins"] += 1

    print()
    print("진입 이유 조합별 성과")
    print("-" * 95)

    ranked = sorted(
        combinations.items(),
        key=lambda item: item[1]["profit"],
        reverse=True,
    )

    for key, data in ranked:
        count = data["count"]

        win_rate = (
            data["wins"]
            / count
            * 100
            if count
            else 0.0
        )

        average_percent = (
            data["percent_sum"]
            / count
            if count
            else 0.0
        )

        print(
            f"{count:>3}회 | "
            f"승률 {win_rate:>6.2f}% | "
            f"평균 {average_percent:+.3f}% | "
            f"손익 {data['profit']:+,.0f}원 | "
            f"{key}"
        )

def print_report(
    result,
    dataframe,
):
    trades = result["trades"]

    print()
    print("=" * 72)
    print(
        "BinanceBot 통합 전략 백테스트 결과"
    )
    print("=" * 72)

    print(f"종목: {SYMBOL}")
    print(f"봉 간격: {INTERVAL}")
    print(
        f"분석 기간: "
        f"{BACKTEST_DAYS}일"
    )
    print(
        f"캔들 수: "
        f"{len(dataframe):,}개"
    )
    print(
        "전략 엔진: "
        "engine.strategy.calculate_score"
    )
    print(
        f"청산 방식: "
        f"{result['exit_mode']}"
    )
    print(
        "부분익절: "
        + (
            "ON"
            if result[
                "partial_exit_enabled"
            ]
            else "OFF"
        )
    )
    print(
        f"발생한 진입 신호: "
        f"{result['signal_count']}회"
    )
    print()

    print(
        f"시작 잔고: "
        f"{result['starting_balance']:,.0f}원"
    )
    print(
        f"종료 잔고: "
        f"{result['ending_balance']:,.0f}원"
    )

    total_return = (
        (
            result["ending_balance"]
            - result["starting_balance"]
        )
        / result["starting_balance"]
        * 100
    )

    print(
        f"총 수익률: "
        f"{total_return:+.3f}%"
    )

    print(
        f"최대 낙폭(MDD): "
        f"-"
        f"{result['maximum_drawdown']:.3f}%"
    )

    print()

    if not trades:
        print(
            "발생한 거래가 없습니다."
        )
        print("=" * 72)
        return

    wins = [
        trade
        for trade in trades
        if trade["profit_amount"] > 0
    ]

    losses = [
        trade
        for trade in trades
        if trade["profit_amount"] <= 0
    ]

    total_trades = len(trades)

    win_rate = (
        len(wins)
        / total_trades
        * 100
    )

    total_profit = sum(
        trade["profit_amount"]
        for trade in trades
    )

    average_trade_percent = (
        sum(
            trade["net_percent"]
            for trade in trades
        )
        / total_trades
    )

    average_win = (
        sum(
            trade["profit_amount"]
            for trade in wins
        )
        / len(wins)
        if wins
        else 0.0
    )

    average_loss = (
        sum(
            trade["profit_amount"]
            for trade in losses
        )
        / len(losses)
        if losses
        else 0.0
    )

    average_entry_score = (
        sum(
            trade["entry_score"]
            for trade in trades
        )
        / total_trades
    )

    long_trades = sum(
        1
        for trade in trades
        if trade["side"] == "LONG"
    )

    short_trades = (
        total_trades
        - long_trades
    )

    print(
        f"총 거래: "
        f"{total_trades}회"
    )
    print(
        f"롱 거래: "
        f"{long_trades}회"
    )
    print(
        f"숏 거래: "
        f"{short_trades}회"
    )
    print(
        f"승리: "
        f"{len(wins)}회"
    )
    print(
        f"손실: "
        f"{len(losses)}회"
    )
    print(
        f"승률: "
        f"{win_rate:.2f}%"
    )
    print(
        f"평균 진입 점수: "
        f"{average_entry_score:.2f}점"
    )

    average_stop_percent = (
        sum(
            trade["stop_percent"]
            for trade in trades
        )
        / total_trades
    )

    average_take_profit_percent = (
        sum(
            trade[
                "take_profit_percent"
            ]
            for trade in trades
        )
        / total_trades
    )

    print(
        f"평균 손절 폭: "
        f"{average_stop_percent:.3f}%"
    )
    print(
        f"평균 익절 폭: "
        f"{average_take_profit_percent:.3f}%"
    )
    print()

    print(
        f"누적 손익: "
        f"{total_profit:+,.0f}원"
    )
    print(
        f"평균 거래 수익률: "
        f"{average_trade_percent:+.3f}%"
    )
    print(
        f"평균 수익금: "
        f"{average_win:+,.0f}원"
    )
    print(
        f"평균 손실금: "
        f"{average_loss:+,.0f}원"
    )

    print(
        "최대 연속 승리: "
        f"{calculate_maximum_streak(trades, True)}회"
    )

    print(
        "최대 연속 손실: "
        f"{calculate_maximum_streak(trades, False)}회"
    )

    print_score_band_report(trades)
    print_exit_reason_report(trades)
    print_reason_combination_report(trades)

    print()
    print("최근 거래 10건")
    print("-" * 72)

    for trade in trades[-10:]:
        entry_text = (
            trade["entry_time"]
            .strftime(
                "%Y-%m-%d %H:%M"
            )
        )

        reasons_text = (
            ", ".join(
                trade[
                    "entry_reasons"
                ]
            )
            or "-"
        )

        print(
            f"{entry_text} | "
            f"{trade['side']:<5} | "
            f"{trade['entry_score']:>3}점 | "
            f"{trade['net_percent']:+.3f}% | "
            f"{trade['profit_amount']:+,.0f}원 | "
            f"{trade['reason']} | "
            f"{reasons_text}"
        )

    print("=" * 72)


# ==================================================
# 프로필 비교
# ==================================================

def set_strategy_profile(profile_name):
    resolved_name, profile = get_strategy_profile(
        profile_name
    )

    strategy_engine.PROFILE_NAME = resolved_name
    strategy_engine.PROFILE = profile

    return resolved_name


def summarize_result(
    profile_name,
    result,
):
    trades = result["trades"]
    total_trades = len(trades)

    wins = [
        trade
        for trade in trades
        if trade["profit_amount"] > 0
    ]

    win_rate = (
        len(wins)
        / total_trades
        * 100
        if total_trades
        else 0.0
    )

    total_return = (
        (
            result["ending_balance"]
            - result["starting_balance"]
        )
        / result["starting_balance"]
        * 100
    )

    return {
        "profile": profile_name,
        "trades": total_trades,
        "wins": len(wins),
        "win_rate": win_rate,
        "return_percent": total_return,
        "maximum_drawdown": (
            result["maximum_drawdown"]
        ),
        "ending_balance": (
            result["ending_balance"]
        ),
    }


def print_profile_comparison(
    summaries,
):
    print()
    print("=" * 88)
    print("전략 프로필 비교 결과")
    print("=" * 88)

    print(
        f"{'프로필':<16}"
        f"{'거래수':>10}"
        f"{'승리':>8}"
        f"{'승률':>12}"
        f"{'수익률':>14}"
        f"{'MDD':>12}"
        f"{'종료잔고':>16}"
    )

    print("-" * 88)

    for summary in summaries:
        print(
            f"{summary['profile']:<16}"
            f"{summary['trades']:>10}"
            f"{summary['wins']:>8}"
            f"{summary['win_rate']:>11.2f}%"
            f"{summary['return_percent']:>+13.3f}%"
            f"{summary['maximum_drawdown']:>11.3f}%"
            f"{summary['ending_balance']:>15,.0f}원"
        )

    if summaries:
        best = max(
            summaries,
            key=lambda item: item[
                "return_percent"
            ],
        )

        print("-" * 88)
        print(
            f"최고 수익률 프로필: "
            f"{best['profile']} "
            f"({best['return_percent']:+.3f}%)"
        )

    print("=" * 88)


def run_profile_comparison(
    dataframe,
):
    summaries = []

    print()
    print(
        "동일한 캔들 데이터로 "
        "전략 프로필을 비교합니다."
    )

    for profile_name in PROFILES:
        resolved_name = set_strategy_profile(
            profile_name
        )

        print()
        print(
            f"[{resolved_name}] "
            "백테스트 실행 중..."
        )

        result = run_backtest(
            dataframe
        )

        summaries.append(
            summarize_result(
                resolved_name,
                result,
            )
        )

    print_profile_comparison(
        summaries
    )



def summarize_exit_result(
    exit_mode,
    result,
):
    summary = summarize_result(
        exit_mode,
        result,
    )

    summary["exit_mode"] = exit_mode

    trades = result["trades"]

    summary["average_stop_percent"] = (
        sum(
            trade["stop_percent"]
            for trade in trades
        )
        / len(trades)
        if trades
        else 0.0
    )

    summary[
        "average_take_profit_percent"
    ] = (
        sum(
            trade[
                "take_profit_percent"
            ]
            for trade in trades
        )
        / len(trades)
        if trades
        else 0.0
    )

    return summary


def print_exit_mode_comparison(
    summaries,
):
    print()
    print("=" * 104)
    print("청산 방식 비교 결과")
    print("=" * 104)

    print(
        f"{'방식':<12}"
        f"{'거래수':>9}"
        f"{'승률':>12}"
        f"{'수익률':>14}"
        f"{'MDD':>12}"
        f"{'평균SL':>12}"
        f"{'평균TP':>12}"
        f"{'종료잔고':>16}"
    )

    print("-" * 104)

    for summary in summaries:
        print(
            f"{summary['exit_mode']:<12}"
            f"{summary['trades']:>9}"
            f"{summary['win_rate']:>11.2f}%"
            f"{summary['return_percent']:>+13.3f}%"
            f"{summary['maximum_drawdown']:>11.3f}%"
            f"{summary['average_stop_percent']:>11.3f}%"
            f"{summary['average_take_profit_percent']:>11.3f}%"
            f"{summary['ending_balance']:>15,.0f}원"
        )

    if summaries:
        best = max(
            summaries,
            key=lambda item: item[
                "return_percent"
            ],
        )

        print("-" * 104)
        print(
            f"최고 수익률 청산 방식: "
            f"{best['exit_mode']} "
            f"({best['return_percent']:+.3f}%)"
        )

    print("=" * 104)


def run_exit_mode_comparison(
    dataframe,
):
    summaries = []

    print()
    print(
        "동일한 진입 전략과 캔들로 "
        "FIXED / ATR 청산을 비교합니다."
    )

    for exit_mode in (
        "FIXED",
        "ATR",
    ):
        print()
        print(
            f"[{exit_mode}] "
            "백테스트 실행 중..."
        )

        result = run_backtest(
            dataframe,
            exit_mode=exit_mode,
        )

        summaries.append(
            summarize_exit_result(
                exit_mode,
                result,
            )
        )

    print_exit_mode_comparison(
        summaries
    )


def summarize_partial_result(
    label,
    result,
):
    summary = summarize_result(
        label,
        result,
    )

    summary["label"] = label

    trades = result["trades"]

    summary["partial_count"] = sum(
        1
        for trade in trades
        if trade.get(
            "partial_taken",
            False,
        )
    )

    return summary


def print_partial_comparison(
    summaries,
):
    print()
    print("=" * 96)
    print("부분익절 + 본절 이동 비교 결과")
    print("=" * 96)

    print(
        f"{'방식':<22}"
        f"{'거래수':>9}"
        f"{'부분익절':>11}"
        f"{'승률':>12}"
        f"{'수익률':>14}"
        f"{'MDD':>12}"
        f"{'종료잔고':>16}"
    )

    print("-" * 96)

    for summary in summaries:
        print(
            f"{summary['label']:<22}"
            f"{summary['trades']:>9}"
            f"{summary['partial_count']:>11}"
            f"{summary['win_rate']:>11.2f}%"
            f"{summary['return_percent']:>+13.3f}%"
            f"{summary['maximum_drawdown']:>11.3f}%"
            f"{summary['ending_balance']:>15,.0f}원"
        )

    if summaries:
        best = max(
            summaries,
            key=lambda item: item[
                "return_percent"
            ],
        )

        print("-" * 96)
        print(
            f"최고 수익률 방식: "
            f"{best['label']} "
            f"({best['return_percent']:+.3f}%)"
        )

    print("=" * 96)


def run_partial_comparison(
    dataframe,
):
    summaries = []

    print()
    print(
        "conservative + FIXED 기준으로 "
        "부분익절 효과를 비교합니다."
    )

    cases = [
        (
            "FULL_EXIT",
            False,
        ),
        (
            "PARTIAL_50_BREAKEVEN",
            True,
        ),
    ]

    for label, enabled in cases:
        print()
        print(
            f"[{label}] "
            "백테스트 실행 중..."
        )

        result = run_backtest(
            dataframe,
            exit_mode="FIXED",
            partial_exit_enabled=enabled,
        )

        summaries.append(
            summarize_partial_result(
                label,
                result,
            )
        )

    print_partial_comparison(
        summaries
    )

def prepare_dataframe():
    candles = (
        download_historical_candles()
    )

    dataframe = (
        candles_to_dataframe(
            candles
        )
    )

    dataframe = (
        add_indicators(
            dataframe
        )
    )

    print(
        f"지표 계산 완료: "
        f"{len(dataframe):,}개 봉",
        flush=True,
    )

    return dataframe


# ==================================================
# 실행
# ==================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "BinanceBot 백테스트"
        )
    )

    parser.add_argument(
        "--compare",
        action="store_true",
        help=(
            "모든 전략 프로필을 "
            "동일 데이터로 비교"
        ),
    )

    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES.keys()),
        help=(
            "단일 백테스트에 사용할 "
            "전략 프로필"
        ),
    )


    parser.add_argument(
        "--compare-exits",
        action="store_true",
        help=(
            "FIXED와 ATR 청산 방식 비교"
        ),
    )

    parser.add_argument(
        "--exit-mode",
        choices=[
            "FIXED",
            "ATR",
        ],
        help=(
            "단일 백테스트에 사용할 "
            "청산 방식"
        ),
    )


    parser.add_argument(
        "--compare-partials",
        action="store_true",
        help=(
            "전량익절과 부분익절+본절이동 비교"
        ),
    )

    args = parser.parse_args()

    compare_flags = sum(
        [
            bool(args.compare),
            bool(args.compare_exits),
            bool(args.compare_partials),
        ]
    )

    if compare_flags > 1:
        parser.error(
            "비교 옵션은 한 번에 하나만 "
            "사용할 수 있습니다."
        )

    try:
        dataframe = prepare_dataframe()

        if args.compare:
            run_profile_comparison(
                dataframe
            )
            return

        selected_profile = (
            args.profile
            or strategy_engine.PROFILE_NAME
        )

        resolved_name = set_strategy_profile(
            selected_profile
        )

        print(
            f"전략 프로필: "
            f"{resolved_name}"
        )

        if args.compare_exits:
            run_exit_mode_comparison(
                dataframe
            )
            return


        if args.compare_partials:
            run_partial_comparison(
                dataframe
            )
            return

        selected_exit_mode = (
            args.exit_mode
            or ACTIVE_EXIT_MODE
        )

        result = run_backtest(
            dataframe,
            exit_mode=selected_exit_mode,
        )

        print_report(
            result,
            dataframe,
        )

    except KeyboardInterrupt:
        print(
            "\n백테스트를 중단했습니다."
        )

    except Exception as error:
        print(
            f"백테스트 오류: "
            f"{repr(error)}"
        )


if __name__ == "__main__":
    main()