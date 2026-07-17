import csv
import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st


STATE_FILE = "state.json"
TRADE_LOG_FILE = "trade_log.csv"
STARTING_BALANCE = 1_000_000


def load_state():
    if not os.path.exists(STATE_FILE):
        return STARTING_BALANCE, {}

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        balance = float(
            data.get("balance", STARTING_BALANCE)
        )

        positions = data.get("positions", {})

        return balance, positions

    except Exception:
        return STARTING_BALANCE, {}


def load_trades():
    if not os.path.exists(TRADE_LOG_FILE):
        return pd.DataFrame()

    try:
        return pd.read_csv(
            TRADE_LOG_FILE,
            encoding="utf-8-sig",
        )

    except Exception:
        return pd.DataFrame()


def calculate_statistics(trades):
    if trades.empty:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_profit": 0.0,
        }

    profit_column = pd.to_numeric(
        trades["손익"],
        errors="coerce",
    ).fillna(0)

    wins = int((profit_column > 0).sum())
    losses = int((profit_column <= 0).sum())
    total_trades = len(trades)

    win_rate = (
        wins / total_trades * 100
        if total_trades > 0
        else 0.0
    )

    total_profit = float(profit_column.sum())

    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_profit": total_profit,
    }


def create_positions_dataframe(positions):
    rows = []

    for symbol, position in positions.items():
        rows.append(
            {
                "종목": symbol,
                "방향": position.get("side", ""),
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


def main():
    st.set_page_config(
        page_title="BinanceBot Dashboard",
        page_icon="📈",
        layout="wide",
    )

    balance, positions = load_state()
    trades = load_trades()
    stats = calculate_statistics(trades)

    st.title("📈 BinanceBot Dashboard")
    st.caption(
        f"마지막 새로고침: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    if st.button("🔄 새로고침"):
        st.rerun()

    first, second, third, fourth = st.columns(4)

    with first:
        st.metric(
            "가상잔고",
            f"{balance:,.0f}원",
            f"{balance - STARTING_BALANCE:+,.0f}원",
        )

    with second:
        st.metric(
            "누적 실현손익",
            f"{stats['total_profit']:+,.0f}원",
        )

    with third:
        st.metric(
            "승률",
            f"{stats['win_rate']:.2f}%",
        )

    with fourth:
        st.metric(
            "보유 포지션",
            f"{len(positions)}개",
        )

    positions_tab, trades_tab, status_tab = st.tabs(
        [
            "현재 포지션",
            "거래 기록",
            "시스템 상태",
        ]
    )

    with positions_tab:
        st.subheader("현재 가상 포지션")

        positions_dataframe = (
            create_positions_dataframe(positions)
        )

        if positions_dataframe.empty:
            st.info("현재 보유 중인 포지션이 없습니다.")

        else:
            st.dataframe(
                positions_dataframe,
                use_container_width=True,
                hide_index=True,
            )

    with trades_tab:
        st.subheader("최근 거래 기록")

        if trades.empty:
            st.info("아직 청산된 거래가 없습니다.")

        else:
            st.dataframe(
                trades.tail(30).iloc[::-1],
                use_container_width=True,
                hide_index=True,
            )

            st.write(
                f"총 거래: {stats['total_trades']}회"
            )

            st.write(
                f"승리 {stats['wins']}회 / "
                f"손실 {stats['losses']}회"
            )

    with status_tab:
        st.subheader("시스템 상태")

        st.success("대시보드 정상 작동 중")
        st.write("현재 모드: 가상매매")
        st.write(f"`state.json`: {'있음' if os.path.exists(STATE_FILE) else '없음'}")
        st.write(
            f"`trade_log.csv`: "
            f"{'있음' if os.path.exists(TRADE_LOG_FILE) else '없음'}"
        )

        st.warning(
            "이 화면은 상태 조회용입니다. "
            "현재는 봇 시작·중지 기능이 없습니다."
        )


if __name__ == "__main__":
    main()