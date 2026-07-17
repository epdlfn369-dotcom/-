import json
import os
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from binance_api import request_json
from scanner import scan_market
from strategy import rank_candidates


# ==================================================
# 설정
# ==================================================

STATE_FILE = "state.json"
TRADE_LOG_FILE = "trade_log.csv"
STARTING_BALANCE = 1_000_000

CHART_SYMBOL = "BTCUSDT"
CHART_INTERVAL = "1m"
CHART_CANDLE_COUNT = 100


# ==================================================
# 파일 읽기
# ==================================================

def load_state():
    if not os.path.exists(STATE_FILE):
        return float(STARTING_BALANCE), {}

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        balance = float(
            data.get(
                "balance",
                STARTING_BALANCE,
            )
        )

        positions = data.get(
            "positions",
            {},
        )

        return balance, positions

    except Exception as error:
        st.error(
            f"state.json 읽기 오류: {error}"
        )

        return float(STARTING_BALANCE), {}


def load_trades():
    if not os.path.exists(TRADE_LOG_FILE):
        return pd.DataFrame()

    try:
        return pd.read_csv(
            TRADE_LOG_FILE,
            encoding="utf-8-sig",
        )

    except Exception as error:
        st.error(
            f"trade_log.csv 읽기 오류: {error}"
        )

        return pd.DataFrame()


# ==================================================
# 거래 통계
# ==================================================

def calculate_statistics(trades):
    if trades.empty or "손익" not in trades.columns:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_profit": 0.0,
        }

    profit_values = pd.to_numeric(
        trades["손익"],
        errors="coerce",
    ).fillna(0.0)

    wins = int(
        (profit_values > 0).sum()
    )

    losses = int(
        (profit_values <= 0).sum()
    )

    total_trades = len(profit_values)

    win_rate = (
        wins / total_trades * 100
        if total_trades
        else 0.0
    )

    total_profit = float(
        profit_values.sum()
    )

    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_profit": total_profit,
    }


# ==================================================
# 바이낸스 차트 데이터
# ==================================================

def get_chart_data(
    symbol=CHART_SYMBOL,
    interval=CHART_INTERVAL,
    limit=CHART_CANDLE_COUNT,
):
    candles = request_json(
        "/fapi/v1/klines",
        {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        },
    )

    rows = []

    for candle in candles:
        rows.append(
            {
                "time": pd.to_datetime(
                    int(candle[0]),
                    unit="ms",
                ),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
            }
        )

    return pd.DataFrame(rows)


def create_candlestick_chart(dataframe, symbol):
    figure = go.Figure(
        data=[
            go.Candlestick(
                x=dataframe["time"],
                open=dataframe["open"],
                high=dataframe["high"],
                low=dataframe["low"],
                close=dataframe["close"],
                name=symbol,
            )
        ]
    )

    figure.update_layout(
        title=f"{symbol} 실시간 {CHART_INTERVAL} 차트",
        xaxis_title="시간",
        yaxis_title="가격(USDT)",
        xaxis_rangeslider_visible=False,
        height=520,
        margin={
            "l": 20,
            "r": 20,
            "t": 50,
            "b": 20,
        },
    )

    return figure


# ==================================================
# 현재 포지션 표
# ==================================================

def create_positions_dataframe(positions):
    rows = []

    for symbol, position in positions.items():
        rows.append(
            {
                "종목": symbol,
                "방향": position.get(
                    "side",
                    "",
                ),
                "진입가": position.get(
                    "entry_price",
                    0,
                ),
                "투입금": position.get(
                    "investment",
                    0,
                ),
                "점수": position.get(
                    "score",
                    0,
                ),
                "진입시간": position.get(
                    "opened_at",
                    "",
                ),
            }
        )

    return pd.DataFrame(rows)


# ==================================================
# 후보 시장 분석
# ==================================================

def analyze_market_candidates():
    market_results = scan_market()
    candidates = rank_candidates(
        market_results
    )

    rows = []

    for candidate in candidates[:10]:
        rows.append(
            {
                "종목": candidate["symbol"],
                "방향": candidate["side"],
                "점수": candidate["score"],
                "5분 변동률": (
                    candidate["move_5m"]
                ),
                "거래량 배수": (
                    candidate["volume_ratio"]
                ),
                "RSI": candidate.get(
                    "rsi",
                    0,
                ),
                "24시간 변동률": (
                    candidate["price_change_24h"]
                ),
            }
        )

    return market_results, candidates, pd.DataFrame(rows)


def calculate_market_direction(
    market_results,
    candidates,
):
    long_count = sum(
        1
        for item in candidates
        if item["side"] == "LONG"
    )

    short_count = sum(
        1
        for item in candidates
        if item["side"] == "SHORT"
    )

    neutral_count = max(
        0,
        len(market_results)
        - long_count
        - short_count,
    )

    if long_count > short_count:
        direction = "LONG 우세"

    elif short_count > long_count:
        direction = "SHORT 우세"

    else:
        direction = "중립"

    return {
        "direction": direction,
        "long_count": long_count,
        "short_count": short_count,
        "neutral_count": neutral_count,
    }


# ==================================================
# 실시간 영역
# ==================================================

@st.fragment(run_every="5s")
def live_chart_section():
    try:
        dataframe = get_chart_data()

        if dataframe.empty:
            st.warning(
                "차트 데이터를 가져오지 못했습니다."
            )
            return

        latest_price = float(
            dataframe.iloc[-1]["close"]
        )

        previous_price = float(
            dataframe.iloc[-2]["close"]
        )

        change_percent = (
            (latest_price - previous_price)
            / previous_price
            * 100
        )

        price_column, time_column = st.columns(
            [1, 2]
        )

        with price_column:
            st.metric(
                f"{CHART_SYMBOL} 현재가",
                f"{latest_price:,.2f} USDT",
                f"{change_percent:+.3f}%",
            )

        with time_column:
            st.info(
                "5초마다 자동 갱신 중\n\n"
                f"갱신 시각: "
                f"{datetime.now().strftime('%H:%M:%S')}"
            )

        figure = create_candlestick_chart(
            dataframe,
            CHART_SYMBOL,
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )

    except Exception as error:
        st.error(
            f"실시간 차트 오류: {error}"
        )


# ==================================================
# 메인 화면
# ==================================================

def main():
    st.set_page_config(
        page_title="BinanceBot Dashboard",
        page_icon="📈",
        layout="wide",
    )

    st.title("📈 BinanceBot Dashboard")

    st.caption(
        "실제 바이낸스 선물 시세를 사용하는 "
        "가상매매 대시보드"
    )

    balance, positions = load_state()
    trades = load_trades()
    stats = calculate_statistics(trades)

    balance_column, profit_column, win_column, position_column = (
        st.columns(4)
    )

    with balance_column:
        st.metric(
            "가상잔고",
            f"{balance:,.0f}원",
            f"{balance - STARTING_BALANCE:+,.0f}원",
        )

    with profit_column:
        st.metric(
            "누적 실현손익",
            f"{stats['total_profit']:+,.0f}원",
        )

    with win_column:
        st.metric(
            "승률",
            f"{stats['win_rate']:.2f}%",
            f"{stats['total_trades']}회 거래",
        )

    with position_column:
        st.metric(
            "현재 포지션",
            f"{len(positions)}개",
        )

    st.divider()

    dashboard_tab, market_tab, position_tab, trade_tab = (
        st.tabs(
            [
                "실시간 차트",
                "시장 후보",
                "현재 포지션",
                "거래 기록",
            ]
        )
    )

    # ----------------------------------------------
    # 실시간 차트
    # ----------------------------------------------

    with dashboard_tab:
        live_chart_section()

    # ----------------------------------------------
    # 시장 후보
    # ----------------------------------------------

    with market_tab:
        st.subheader("전체 시장 후보 분석")

        st.warning(
            "전체 시장 스캔은 여러 코인의 캔들을 "
            "조회하므로 버튼을 눌렀을 때만 실행합니다."
        )

        if st.button(
            "🔍 지금 시장 스캔",
            type="primary",
        ):
            with st.spinner(
                "거래대금 상위 코인을 분석 중입니다..."
            ):
                try:
                    (
                        market_results,
                        candidates,
                        candidate_dataframe,
                    ) = analyze_market_candidates()

                    market_direction = (
                        calculate_market_direction(
                            market_results,
                            candidates,
                        )
                    )

                    st.session_state[
                        "market_results"
                    ] = market_results

                    st.session_state[
                        "candidates"
                    ] = candidates

                    st.session_state[
                        "candidate_dataframe"
                    ] = candidate_dataframe

                    st.session_state[
                        "market_direction"
                    ] = market_direction

                except Exception as error:
                    st.error(
                        f"시장 스캔 오류: {error}"
                    )

        if "market_direction" in st.session_state:
            direction = st.session_state[
                "market_direction"
            ]

            first, second, third, fourth = (
                st.columns(4)
            )

            with first:
                st.metric(
                    "시장 판단",
                    direction["direction"],
                )

            with second:
                st.metric(
                    "LONG 후보",
                    f"{direction['long_count']}개",
                )

            with third:
                st.metric(
                    "SHORT 후보",
                    f"{direction['short_count']}개",
                )

            with fourth:
                st.metric(
                    "중립·제외",
                    f"{direction['neutral_count']}개",
                )

            candidate_dataframe = (
                st.session_state[
                    "candidate_dataframe"
                ]
            )

            st.subheader("매매 후보 TOP10")

            if candidate_dataframe.empty:
                st.info(
                    "현재 진입 조건을 만족하는 "
                    "후보가 없습니다."
                )

            else:
                st.dataframe(
                    candidate_dataframe,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "5분 변동률": st.column_config.NumberColumn(
                            format="%+.3f%%"
                        ),
                        "거래량 배수": st.column_config.NumberColumn(
                            format="%.2f배"
                        ),
                        "RSI": st.column_config.NumberColumn(
                            format="%.1f"
                        ),
                        "24시간 변동률": st.column_config.NumberColumn(
                            format="%+.2f%%"
                        ),
                    },
                )

    # ----------------------------------------------
    # 현재 포지션
    # ----------------------------------------------

    with position_tab:
        st.subheader("현재 가상 포지션")

        positions_dataframe = (
            create_positions_dataframe(
                positions
            )
        )

        if positions_dataframe.empty:
            st.info(
                "현재 보유 중인 포지션이 없습니다."
            )

        else:
            st.dataframe(
                positions_dataframe,
                use_container_width=True,
                hide_index=True,
            )

        st.caption(
            "포지션 데이터는 state.json에서 "
            "불러옵니다."
        )

    # ----------------------------------------------
    # 거래 기록
    # ----------------------------------------------

    with trade_tab:
        st.subheader("최근 거래 기록")

        if trades.empty:
            st.info(
                "아직 청산된 거래 기록이 없습니다."
            )

        else:
            st.dataframe(
                trades.tail(50).iloc[::-1],
                use_container_width=True,
                hide_index=True,
            )

            first, second, third = st.columns(3)

            with first:
                st.metric(
                    "총 거래",
                    f"{stats['total_trades']}회",
                )

            with second:
                st.metric(
                    "승리 / 손실",
                    (
                        f"{stats['wins']} / "
                        f"{stats['losses']}"
                    ),
                )

            with third:
                st.metric(
                    "누적 손익",
                    f"{stats['total_profit']:+,.0f}원",
                )


if __name__ == "__main__":
    main()