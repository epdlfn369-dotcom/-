import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

from binance_api import request_json


# ==================================================
# 백테스트 설정
# ==================================================

SYMBOL = "BTCUSDT"
INTERVAL = "5m"
BACKTEST_DAYS = 30

STARTING_BALANCE = 1_000_000
POSITION_SIZE_PERCENT = 10

STOP_LOSS_PERCENT = 1.0
TAKE_PROFIT_PERCENT = 3.0
ROUND_TRIP_FEE_PERCENT = 0.10

EMA_FAST = 20
EMA_SLOW = 50
RSI_PERIOD = 14

MIN_VOLUME_RATIO = 1.20
MIN_MOVE_PERCENT = 0.15

REQUEST_DELAY_SECONDS = 0.15


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
    start_time = end_time - timedelta(days=BACKTEST_DAYS)

    current_start = datetime_to_milliseconds(start_time)
    final_end = datetime_to_milliseconds(end_time)

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

        last_open_time = int(candles[-1][0])
        next_start = last_open_time + 1

        if next_start <= current_start:
            break

        current_start = next_start

        print(
            f"\r다운로드된 캔들: {len(all_candles):,}개",
            end="",
            flush=True,
        )

        time.sleep(REQUEST_DELAY_SECONDS)

        if len(candles) < 1500:
            break

    print()

    if not all_candles:
        raise RuntimeError("캔들 데이터를 가져오지 못했습니다.")

    # 중복 캔들 제거
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
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
            }
        )

    dataframe = pd.DataFrame(rows)

    # 현재 진행 중일 수 있는 마지막 봉 제외
    if len(dataframe) > 1:
        dataframe = dataframe.iloc[:-1].copy()

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

    # 5분봉 한 개 전 대비 변화율
    dataframe["move_percent"] = (
        dataframe["close"].pct_change() * 100
    )

    # 직전 5개 봉 평균 거래량
    dataframe["previous_volume_average"] = (
        dataframe["volume"]
        .shift(1)
        .rolling(window=5)
        .mean()
    )

    dataframe["volume_ratio"] = (
        dataframe["volume"]
        / dataframe["previous_volume_average"]
    )

    dataframe = dataframe.dropna().reset_index(drop=True)

    return dataframe


# ==================================================
# 진입 신호
# ==================================================

def get_entry_signal(row):
    long_condition = (
        row["ema20"] > row["ema50"]
        and 45 <= row["rsi"] <= 68
        and row["move_percent"] >= MIN_MOVE_PERCENT
        and row["volume_ratio"] >= MIN_VOLUME_RATIO
    )

    short_condition = (
        row["ema20"] < row["ema50"]
        and 32 <= row["rsi"] <= 55
        and row["move_percent"] <= -MIN_MOVE_PERCENT
        and row["volume_ratio"] >= MIN_VOLUME_RATIO
    )

    if long_condition:
        return "LONG"

    if short_condition:
        return "SHORT"

    return None


# ==================================================
# 손절·익절 가격
# ==================================================

def calculate_exit_prices(side, entry_price):
    if side == "LONG":
        stop_price = entry_price * (
            1 - STOP_LOSS_PERCENT / 100
        )

        target_price = entry_price * (
            1 + TAKE_PROFIT_PERCENT / 100
        )

    else:
        stop_price = entry_price * (
            1 + STOP_LOSS_PERCENT / 100
        )

        target_price = entry_price * (
            1 - TAKE_PROFIT_PERCENT / 100
        )

    return stop_price, target_price


def calculate_gross_profit_percent(
    side,
    entry_price,
    exit_price,
):
    if side == "LONG":
        return (
            (exit_price - entry_price)
            / entry_price
            * 100
        )

    return (
        (entry_price - exit_price)
        / entry_price
        * 100
    )


# ==================================================
# 백테스트 실행
# ==================================================

def run_backtest(dataframe):
    balance = float(STARTING_BALANCE)
    peak_balance = balance
    maximum_drawdown = 0.0

    position = None
    trades = []

    for index in range(len(dataframe)):
        row = dataframe.iloc[index]

        # ------------------------------------------
        # 기존 포지션 청산 검사
        # ------------------------------------------

        if position is not None:
            side = position["side"]
            stop_price = position["stop_price"]
            target_price = position["target_price"]

            exit_price = None
            exit_reason = None

            if side == "LONG":
                stop_touched = row["low"] <= stop_price
                target_touched = row["high"] >= target_price

                # 같은 봉에서 둘 다 닿으면 보수적으로 손절 우선
                if stop_touched:
                    exit_price = stop_price
                    exit_reason = "STOP"

                elif target_touched:
                    exit_price = target_price
                    exit_reason = "TAKE_PROFIT"

            else:
                stop_touched = row["high"] >= stop_price
                target_touched = row["low"] <= target_price

                if stop_touched:
                    exit_price = stop_price
                    exit_reason = "STOP"

                elif target_touched:
                    exit_price = target_price
                    exit_reason = "TAKE_PROFIT"

            if exit_price is not None:
                gross_percent = (
                    calculate_gross_profit_percent(
                        side,
                        position["entry_price"],
                        exit_price,
                    )
                )

                net_percent = (
                    gross_percent
                    - ROUND_TRIP_FEE_PERCENT
                )

                profit_amount = (
                    position["investment"]
                    * net_percent
                    / 100
                )

                balance += profit_amount

                trades.append(
                    {
                        "side": side,
                        "entry_time": position["entry_time"],
                        "exit_time": row["time"],
                        "entry_price": position["entry_price"],
                        "exit_price": exit_price,
                        "gross_percent": gross_percent,
                        "net_percent": net_percent,
                        "profit_amount": profit_amount,
                        "reason": exit_reason,
                    }
                )

                peak_balance = max(
                    peak_balance,
                    balance,
                )

                drawdown = (
                    (peak_balance - balance)
                    / peak_balance
                    * 100
                )

                maximum_drawdown = max(
                    maximum_drawdown,
                    drawdown,
                )

                position = None

                # 같은 봉에서 청산 후 재진입하지 않음
                continue

        # ------------------------------------------
        # 신규 진입
        # ------------------------------------------

        if position is None:
            signal = get_entry_signal(row)

            if signal is None:
                continue

            # 신호가 나온 봉 종가에서 진입한다고 가정
            entry_price = row["close"]

            stop_price, target_price = (
                calculate_exit_prices(
                    signal,
                    entry_price,
                )
            )

            investment = (
                balance
                * POSITION_SIZE_PERCENT
                / 100
            )

            position = {
                "side": signal,
                "entry_time": row["time"],
                "entry_price": entry_price,
                "stop_price": stop_price,
                "target_price": target_price,
                "investment": investment,
            }

    # 데이터 종료 시 열린 포지션 강제 청산
    if position is not None:
        last_row = dataframe.iloc[-1]
        exit_price = last_row["close"]

        gross_percent = calculate_gross_profit_percent(
            position["side"],
            position["entry_price"],
            exit_price,
        )

        net_percent = (
            gross_percent
            - ROUND_TRIP_FEE_PERCENT
        )

        profit_amount = (
            position["investment"]
            * net_percent
            / 100
        )

        balance += profit_amount

        trades.append(
            {
                "side": position["side"],
                "entry_time": position["entry_time"],
                "exit_time": last_row["time"],
                "entry_price": position["entry_price"],
                "exit_price": exit_price,
                "gross_percent": gross_percent,
                "net_percent": net_percent,
                "profit_amount": profit_amount,
                "reason": "END_OF_DATA",
            }
        )

    return {
        "starting_balance": STARTING_BALANCE,
        "ending_balance": balance,
        "maximum_drawdown": maximum_drawdown,
        "trades": trades,
    }


# ==================================================
# 결과 출력
# ==================================================

def calculate_maximum_streak(trades, win):
    maximum = 0
    current = 0

    for trade in trades:
        is_win = trade["profit_amount"] > 0

        if is_win == win:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0

    return maximum


def print_report(result, dataframe):
    trades = result["trades"]

    print()
    print("=" * 68)
    print("BinanceBot 백테스트 결과")
    print("=" * 68)

    print(f"종목: {SYMBOL}")
    print(f"봉 간격: {INTERVAL}")
    print(f"분석 기간: {BACKTEST_DAYS}일")
    print(f"캔들 수: {len(dataframe):,}개")
    print()

    print(f"시작 잔고: {result['starting_balance']:,.0f}원")
    print(f"종료 잔고: {result['ending_balance']:,.0f}원")

    total_return = (
        (
            result["ending_balance"]
            - result["starting_balance"]
        )
        / result["starting_balance"]
        * 100
    )

    print(f"총 수익률: {total_return:+.3f}%")
    print(
        f"최대 낙폭(MDD): "
        f"-{result['maximum_drawdown']:.3f}%"
    )
    print()

    if not trades:
        print("발생한 거래가 없습니다.")
        print("=" * 68)
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
    win_rate = len(wins) / total_trades * 100

    total_profit = sum(
        trade["profit_amount"]
        for trade in trades
    )

    average_trade_percent = sum(
        trade["net_percent"]
        for trade in trades
    ) / total_trades

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

    long_trades = sum(
        1
        for trade in trades
        if trade["side"] == "LONG"
    )

    short_trades = total_trades - long_trades

    print(f"총 거래: {total_trades}회")
    print(f"롱 거래: {long_trades}회")
    print(f"숏 거래: {short_trades}회")
    print(f"승리: {len(wins)}회")
    print(f"손실: {len(losses)}회")
    print(f"승률: {win_rate:.2f}%")
    print()

    print(f"누적 손익: {total_profit:+,.0f}원")
    print(
        f"평균 거래 수익률: "
        f"{average_trade_percent:+.3f}%"
    )
    print(f"평균 수익금: {average_win:+,.0f}원")
    print(f"평균 손실금: {average_loss:+,.0f}원")

    print(
        "최대 연속 승리: "
        f"{calculate_maximum_streak(trades, True)}회"
    )

    print(
        "최대 연속 손실: "
        f"{calculate_maximum_streak(trades, False)}회"
    )

    print()
    print("최근 거래 10건")
    print("-" * 68)

    for trade in trades[-10:]:
        entry_text = trade["entry_time"].strftime(
            "%Y-%m-%d %H:%M"
        )

        print(
            f"{entry_text} | "
            f"{trade['side']:<5} | "
            f"{trade['net_percent']:+.3f}% | "
            f"{trade['profit_amount']:+,.0f}원 | "
            f"{trade['reason']}"
        )

    print("=" * 68)


# ==================================================
# 실행
# ==================================================

def main():
    try:
        candles = download_historical_candles()
        dataframe = candles_to_dataframe(candles)
        dataframe = add_indicators(dataframe)

        print(
            f"지표 계산 완료: {len(dataframe):,}개 봉",
            flush=True,
        )

        result = run_backtest(dataframe)
        print_report(result, dataframe)

    except KeyboardInterrupt:
        print("\n백테스트를 중단했습니다.")

    except Exception as error:
        print(f"백테스트 오류: {repr(error)}")


if __name__ == "__main__":
    main()