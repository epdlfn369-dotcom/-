import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

from binance_api import request_json


# ==================================================
# 기본 설정
# ==================================================

STARTING_BALANCE = 1_000_000
POSITION_SIZE_PERCENT = 10
ROUND_TRIP_FEE_PERCENT = 0.10


# ==================================================
# 데이터 다운로드
# ==================================================

def datetime_to_milliseconds(value):
    return int(value.timestamp() * 1000)


def download_candles(
    symbol,
    interval,
    backtest_days,
):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(
        days=backtest_days
    )

    current_start = datetime_to_milliseconds(
        start_time
    )
    final_end = datetime_to_milliseconds(
        end_time
    )

    all_candles = []

    progress_text = st.empty()
    progress_bar = st.progress(0)

    while current_start < final_end:
        candles = request_json(
            "/fapi/v1/klines",
            {
                "symbol": symbol,
                "interval": interval,
                "startTime": current_start,
                "endTime": final_end,
                "limit": 1500,
            },
        )

        if not candles:
            break

        all_candles.extend(candles)

        last_open_time = int(candles[-1][0])
        current_start = last_open_time + 1

        progress = min(
            current_start / final_end,
            1.0,
        )

        progress_bar.progress(progress)

        progress_text.write(
            f"다운로드된 캔들: "
            f"{len(all_candles):,}개"
        )

        if len(candles) < 1500:
            break

        time.sleep(0.15)

    progress_bar.progress(1.0)
    progress_text.write(
        f"다운로드 완료: "
        f"{len(all_candles):,}개"
    )

    unique_candles = {
        int(candle[0]): candle
        for candle in all_candles
    }

    return [
        unique_candles[key]
        for key in sorted(unique_candles)
    ]


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

    if len(dataframe) > 1:
        dataframe = dataframe.iloc[:-1].copy()

    return dataframe


# ==================================================
# 지표 계산
# ==================================================

def add_indicators(
    dataframe,
    ema_fast,
    ema_slow,
    rsi_period,
):
    dataframe = dataframe.copy()

    dataframe["ema_fast"] = EMAIndicator(
        close=dataframe["close"],
        window=ema_fast,
    ).ema_indicator()

    dataframe["ema_slow"] = EMAIndicator(
        close=dataframe["close"],
        window=ema_slow,
    ).ema_indicator()

    dataframe["rsi"] = RSIIndicator(
        close=dataframe["close"],
        window=rsi_period,
    ).rsi()

    dataframe["move_percent"] = (
        dataframe["close"].pct_change()
        * 100
    )

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

    return dataframe.dropna().reset_index(
        drop=True
    )


# ==================================================
# 매매 신호
# ==================================================

def get_entry_signal(
    row,
    minimum_move,
    minimum_volume_ratio,
    long_rsi_min,
    long_rsi_max,
    short_rsi_min,
    short_rsi_max,
):
    long_condition = (
        row["ema_fast"] > row["ema_slow"]
        and long_rsi_min
        <= row["rsi"]
        <= long_rsi_max
        and row["move_percent"]
        >= minimum_move
        and row["volume_ratio"]
        >= minimum_volume_ratio
    )

    short_condition = (
        row["ema_fast"] < row["ema_slow"]
        and short_rsi_min
        <= row["rsi"]
        <= short_rsi_max
        and row["move_percent"]
        <= -minimum_move
        and row["volume_ratio"]
        >= minimum_volume_ratio
    )

    if long_condition:
        return "LONG"

    if short_condition:
        return "SHORT"

    return None


def calculate_exit_prices(
    side,
    entry_price,
    stop_loss_percent,
    take_profit_percent,
):
    if side == "LONG":
        stop_price = entry_price * (
            1 - stop_loss_percent / 100
        )

        target_price = entry_price * (
            1 + take_profit_percent / 100
        )

    else:
        stop_price = entry_price * (
            1 + stop_loss_percent / 100
        )

        target_price = entry_price * (
            1 - take_profit_percent / 100
        )

    return stop_price, target_price


def calculate_profit_percent(
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
# 백테스트
# ==================================================

def run_backtest(
    dataframe,
    stop_loss_percent,
    take_profit_percent,
    minimum_move,
    minimum_volume_ratio,
    long_rsi_min,
    long_rsi_max,
    short_rsi_min,
    short_rsi_max,
):
    balance = float(STARTING_BALANCE)
    peak_balance = balance
    maximum_drawdown = 0.0

    position = None
    trades = []

    equity_rows = [
        {
            "time": dataframe.iloc[0]["time"],
            "balance": balance,
        }
    ]

    for _, row in dataframe.iterrows():
        if position is not None:
            side = position["side"]
            stop_price = position["stop_price"]
            target_price = position[
                "target_price"
            ]

            exit_price = None
            exit_reason = None

            if side == "LONG":
                if row["low"] <= stop_price:
                    exit_price = stop_price
                    exit_reason = "손절"

                elif row["high"] >= target_price:
                    exit_price = target_price
                    exit_reason = "익절"

            else:
                if row["high"] >= stop_price:
                    exit_price = stop_price
                    exit_reason = "손절"

                elif row["low"] <= target_price:
                    exit_price = target_price
                    exit_reason = "익절"

            if exit_price is not None:
                gross_percent = (
                    calculate_profit_percent(
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
                        "진입시간": position[
                            "entry_time"
                        ],
                        "청산시간": row["time"],
                        "방향": side,
                        "진입가": position[
                            "entry_price"
                        ],
                        "청산가": exit_price,
                        "수익률": net_percent,
                        "손익": profit_amount,
                        "청산이유": exit_reason,
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

                equity_rows.append(
                    {
                        "time": row["time"],
                        "balance": balance,
                    }
                )

                position = None
                continue

        if position is None:
            signal = get_entry_signal(
                row=row,
                minimum_move=minimum_move,
                minimum_volume_ratio=(
                    minimum_volume_ratio
                ),
                long_rsi_min=long_rsi_min,
                long_rsi_max=long_rsi_max,
                short_rsi_min=short_rsi_min,
                short_rsi_max=short_rsi_max,
            )

            if signal is None:
                continue

            entry_price = row["close"]

            stop_price, target_price = (
                calculate_exit_prices(
                    side=signal,
                    entry_price=entry_price,
                    stop_loss_percent=(
                        stop_loss_percent
                    ),
                    take_profit_percent=(
                        take_profit_percent
                    ),
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

    if position is not None:
        last_row = dataframe.iloc[-1]

        gross_percent = calculate_profit_percent(
            position["side"],
            position["entry_price"],
            last_row["close"],
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
                "진입시간": position[
                    "entry_time"
                ],
                "청산시간": last_row["time"],
                "방향": position["side"],
                "진입가": position[
                    "entry_price"
                ],
                "청산가": last_row["close"],
                "수익률": net_percent,
                "손익": profit_amount,
                "청산이유": "기간 종료",
            }
        )

        equity_rows.append(
            {
                "time": last_row["time"],
                "balance": balance,
            }
        )

    return {
        "ending_balance": balance,
        "maximum_drawdown": (
            maximum_drawdown
        ),
        "trades": pd.DataFrame(trades),
        "equity": pd.DataFrame(equity_rows),
    }


# ==================================================
# 결과 출력
# ==================================================

def show_backtest_result(
    result,
    symbol,
):
    trades = result["trades"]

    total_return = (
        (
            result["ending_balance"]
            - STARTING_BALANCE
        )
        / STARTING_BALANCE
        * 100
    )

    if trades.empty:
        wins = 0
        losses = 0
        win_rate = 0.0
        total_profit = 0.0

    else:
        wins = int(
            (trades["손익"] > 0).sum()
        )

        losses = int(
            (trades["손익"] <= 0).sum()
        )

        win_rate = (
            wins / len(trades) * 100
        )

        total_profit = float(
            trades["손익"].sum()
        )

    first, second, third, fourth = (
        st.columns(4)
    )

    with first:
        st.metric(
            "종료 잔고",
            f"{result['ending_balance']:,.0f}원",
            f"{total_profit:+,.0f}원",
        )

    with second:
        st.metric(
            "총 수익률",
            f"{total_return:+.3f}%",
        )

    with third:
        st.metric(
            "승률",
            f"{win_rate:.2f}%",
            f"{len(trades)}회 거래",
        )

    with fourth:
        st.metric(
            "최대 낙폭",
            f"-{result['maximum_drawdown']:.3f}%",
        )

    st.subheader("잔고 변화")

    equity = result["equity"]

    if not equity.empty:
        figure = go.Figure()

        figure.add_trace(
            go.Scatter(
                x=equity["time"],
                y=equity["balance"],
                mode="lines",
                name="가상잔고",
            )
        )

        figure.update_layout(
            title=f"{symbol} 백테스트 잔고 곡선",
            xaxis_title="시간",
            yaxis_title="잔고(원)",
            height=450,
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )

    st.subheader("거래 결과")

    first, second, third = st.columns(3)

    with first:
        st.metric(
            "승리",
            f"{wins}회",
        )

    with second:
        st.metric(
            "손실",
            f"{losses}회",
        )

    with third:
        st.metric(
            "누적 손익",
            f"{total_profit:+,.0f}원",
        )

    if trades.empty:
        st.info(
            "설정 조건에서 발생한 거래가 없습니다."
        )

    else:
        display_trades = trades.copy()

        display_trades["진입시간"] = (
            display_trades[
                "진입시간"
            ].astype(str)
        )

        display_trades["청산시간"] = (
            display_trades[
                "청산시간"
            ].astype(str)
        )

        st.dataframe(
            display_trades.iloc[::-1],
            use_container_width=True,
            hide_index=True,
            column_config={
                "진입가": (
                    st.column_config.NumberColumn(
                        format="%.8f"
                    )
                ),
                "청산가": (
                    st.column_config.NumberColumn(
                        format="%.8f"
                    )
                ),
                "수익률": (
                    st.column_config.NumberColumn(
                        format="%+.3f%%"
                    )
                ),
                "손익": (
                    st.column_config.NumberColumn(
                        format="%+,.0f원"
                    )
                ),
            },
        )


# ==================================================
# 메인 화면
# ==================================================

def main():
    st.set_page_config(
        page_title="BinanceBot Backtest",
        page_icon="🧪",
        layout="wide",
    )

    st.title("🧪 BinanceBot 백테스트 연구실")

    st.caption(
        "실제 바이낸스 선물 과거 데이터를 "
        "사용하는 가상 백테스트"
    )

    with st.form("backtest_settings"):
        first, second, third = st.columns(3)

        with first:
            symbol = st.selectbox(
                "종목",
                [
                    "BTCUSDT",
                    "ETHUSDT",
                    "SOLUSDT",
                    "XRPUSDT",
                    "DOGEUSDT",
                    "SUIUSDT",
                    "BNBUSDT",
                ],
            )

            interval = st.selectbox(
                "봉 간격",
                [
                    "1m",
                    "3m",
                    "5m",
                    "15m",
                    "1h",
                ],
                index=2,
            )

            backtest_days = st.number_input(
                "분석 기간(일)",
                min_value=1,
                max_value=365,
                value=30,
                step=1,
            )

        with second:
            ema_fast = st.number_input(
                "빠른 EMA",
                min_value=2,
                max_value=200,
                value=20,
                step=1,
            )

            ema_slow = st.number_input(
                "느린 EMA",
                min_value=3,
                max_value=300,
                value=50,
                step=1,
            )

            rsi_period = st.number_input(
                "RSI 기간",
                min_value=2,
                max_value=100,
                value=14,
                step=1,
            )

        with third:
            stop_loss = st.number_input(
                "손절률(%)",
                min_value=0.1,
                max_value=20.0,
                value=1.0,
                step=0.1,
            )

            take_profit = st.number_input(
                "익절률(%)",
                min_value=0.1,
                max_value=50.0,
                value=3.0,
                step=0.1,
            )

            minimum_move = st.number_input(
                "최소 봉 변동률(%)",
                min_value=0.01,
                max_value=10.0,
                value=0.15,
                step=0.01,
            )

        st.subheader("추가 진입 조건")

        first, second, third = st.columns(3)

        with first:
            minimum_volume_ratio = (
                st.number_input(
                    "최소 거래량 배수",
                    min_value=0.1,
                    max_value=20.0,
                    value=1.2,
                    step=0.1,
                )
            )

        with second:
            long_rsi_min = st.number_input(
                "롱 RSI 최소",
                min_value=0,
                max_value=100,
                value=45,
                step=1,
            )

            long_rsi_max = st.number_input(
                "롱 RSI 최대",
                min_value=0,
                max_value=100,
                value=68,
                step=1,
            )

        with third:
            short_rsi_min = st.number_input(
                "숏 RSI 최소",
                min_value=0,
                max_value=100,
                value=32,
                step=1,
            )

            short_rsi_max = st.number_input(
                "숏 RSI 최대",
                min_value=0,
                max_value=100,
                value=55,
                step=1,
            )

        submitted = st.form_submit_button(
            "🚀 백테스트 실행",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if ema_fast >= ema_slow:
            st.error(
                "빠른 EMA는 느린 EMA보다 "
                "작아야 합니다."
            )
            return

        if long_rsi_min > long_rsi_max:
            st.error(
                "롱 RSI 최소값이 최대값보다 "
                "클 수 없습니다."
            )
            return

        if short_rsi_min > short_rsi_max:
            st.error(
                "숏 RSI 최소값이 최대값보다 "
                "클 수 없습니다."
            )
            return

        with st.spinner(
            "과거 데이터를 받고 "
            "백테스트를 실행 중입니다..."
        ):
            try:
                candles = download_candles(
                    symbol=symbol,
                    interval=interval,
                    backtest_days=(
                        int(backtest_days)
                    ),
                )

                if not candles:
                    st.error(
                        "캔들 데이터를 받지 "
                        "못했습니다."
                    )
                    return

                dataframe = candles_to_dataframe(
                    candles
                )

                dataframe = add_indicators(
                    dataframe=dataframe,
                    ema_fast=int(ema_fast),
                    ema_slow=int(ema_slow),
                    rsi_period=int(rsi_period),
                )

                if dataframe.empty:
                    st.error(
                        "지표 계산 후 사용할 "
                        "데이터가 없습니다."
                    )
                    return

                result = run_backtest(
                    dataframe=dataframe,
                    stop_loss_percent=float(
                        stop_loss
                    ),
                    take_profit_percent=float(
                        take_profit
                    ),
                    minimum_move=float(
                        minimum_move
                    ),
                    minimum_volume_ratio=float(
                        minimum_volume_ratio
                    ),
                    long_rsi_min=float(
                        long_rsi_min
                    ),
                    long_rsi_max=float(
                        long_rsi_max
                    ),
                    short_rsi_min=float(
                        short_rsi_min
                    ),
                    short_rsi_max=float(
                        short_rsi_max
                    ),
                )

                st.success(
                    f"{symbol} 백테스트 완료 — "
                    f"{len(dataframe):,}개 봉 분석"
                )

                show_backtest_result(
                    result,
                    symbol,
                )

            except Exception as error:
                st.error(
                    f"백테스트 오류: "
                    f"{repr(error)}"
                )


if __name__ == "__main__":
    main()