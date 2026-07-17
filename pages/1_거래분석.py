import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


TRADE_LOG_FILE = "trade_log.csv"
STARTING_BALANCE = 1_000_000


# ==================================================
# 데이터 불러오기
# ==================================================

def load_trades():
    if not os.path.exists(TRADE_LOG_FILE):
        return pd.DataFrame()

    try:
        dataframe = pd.read_csv(
            TRADE_LOG_FILE,
            encoding="utf-8-sig",
        )

    except Exception as error:
        st.error(
            f"거래 기록을 읽지 못했습니다: {error}"
        )
        return pd.DataFrame()

    required_columns = {
        "진입시간",
        "청산시간",
        "종목",
        "방향",
        "수익률",
        "손익",
        "보유초",
        "청산이유",
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        st.error(
            "거래 기록에 필요한 열이 없습니다: "
            + ", ".join(sorted(missing_columns))
        )
        return pd.DataFrame()

    dataframe["진입시간"] = pd.to_datetime(
        dataframe["진입시간"],
        errors="coerce",
    )

    dataframe["청산시간"] = pd.to_datetime(
        dataframe["청산시간"],
        errors="coerce",
    )

    dataframe["수익률"] = pd.to_numeric(
        dataframe["수익률"],
        errors="coerce",
    ).fillna(0.0)

    dataframe["손익"] = pd.to_numeric(
        dataframe["손익"],
        errors="coerce",
    ).fillna(0.0)

    dataframe["보유초"] = pd.to_numeric(
        dataframe["보유초"],
        errors="coerce",
    ).fillna(0).astype(int)

    dataframe = dataframe.dropna(
        subset=[
            "진입시간",
            "청산시간",
        ]
    ).copy()

    dataframe["결과분류"] = dataframe["손익"].apply(
        lambda value: (
            "승리"
            if value > 0
            else "손실"
            if value < 0
            else "무승부"
        )
    )

    dataframe["요일번호"] = (
        dataframe["진입시간"].dt.weekday
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

    dataframe["요일"] = dataframe[
        "요일번호"
    ].map(weekday_names)

    dataframe["진입시각"] = (
        dataframe["진입시간"].dt.hour
    )

    dataframe["시간대"] = dataframe[
        "진입시각"
    ].apply(classify_time_period)

    dataframe["누적손익"] = (
        dataframe["손익"].cumsum()
    )

    dataframe["추정잔고"] = (
        STARTING_BALANCE
        + dataframe["누적손익"]
    )

    return dataframe


def classify_time_period(hour):
    if 0 <= hour < 6:
        return "새벽"

    if 6 <= hour < 12:
        return "오전"

    if 12 <= hour < 18:
        return "오후"

    return "저녁"


# ==================================================
# 통계 계산
# ==================================================

def calculate_profit_factor(dataframe):
    gross_profit = dataframe.loc[
        dataframe["손익"] > 0,
        "손익",
    ].sum()

    gross_loss = abs(
        dataframe.loc[
            dataframe["손익"] < 0,
            "손익",
        ].sum()
    )

    if gross_loss == 0:
        if gross_profit > 0:
            return float("inf")

        return 0.0

    return gross_profit / gross_loss


def calculate_max_streak(
    dataframe,
    target_result,
):
    maximum = 0
    current = 0

    for result in dataframe["결과분류"]:
        if result == target_result:
            current += 1
            maximum = max(
                maximum,
                current,
            )
        else:
            current = 0

    return maximum


def calculate_max_drawdown(dataframe):
    if dataframe.empty:
        return 0.0

    equity = dataframe["추정잔고"]
    running_peak = equity.cummax()

    drawdown = (
        (equity - running_peak)
        / running_peak
        * 100
    )

    return abs(float(drawdown.min()))


def create_group_statistics(
    dataframe,
    group_column,
):
    rows = []

    for name, group in dataframe.groupby(
        group_column
    ):
        trade_count = len(group)

        wins = int(
            (group["손익"] > 0).sum()
        )

        losses = int(
            (group["손익"] < 0).sum()
        )

        win_rate = (
            wins / trade_count * 100
            if trade_count > 0
            else 0.0
        )

        rows.append(
            {
                group_column: name,
                "거래수": trade_count,
                "승리": wins,
                "손실": losses,
                "승률": win_rate,
                "누적손익": float(
                    group["손익"].sum()
                ),
                "평균손익": float(
                    group["손익"].mean()
                ),
                "평균수익률": float(
                    group["수익률"].mean()
                ),
                "Profit Factor": (
                    calculate_profit_factor(
                        group
                    )
                ),
            }
        )

    result = pd.DataFrame(rows)

    if result.empty:
        return result

    return result.sort_values(
        "누적손익",
        ascending=False,
    ).reset_index(drop=True)


def format_holding_time(seconds):
    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (
        seconds % 3600
    ) // 60

    remaining_seconds = seconds % 60

    if hours > 0:
        return (
            f"{hours}시간 "
            f"{minutes}분"
        )

    if minutes > 0:
        return (
            f"{minutes}분 "
            f"{remaining_seconds}초"
        )

    return f"{remaining_seconds}초"


# ==================================================
# 차트
# ==================================================

def create_equity_chart(dataframe):
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=dataframe["청산시간"],
            y=dataframe["추정잔고"],
            mode="lines+markers",
            name="추정잔고",
        )
    )

    figure.add_hline(
        y=STARTING_BALANCE,
        line_dash="dash",
        annotation_text="시작 잔고",
    )

    figure.update_layout(
        title="가상잔고 변화",
        xaxis_title="청산시간",
        yaxis_title="잔고(원)",
        height=450,
        hovermode="x unified",
    )

    return figure


def create_drawdown_chart(dataframe):
    equity = dataframe["추정잔고"]
    running_peak = equity.cummax()

    drawdown = (
        (equity - running_peak)
        / running_peak
        * 100
    )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=dataframe["청산시간"],
            y=drawdown,
            mode="lines",
            fill="tozeroy",
            name="Drawdown",
        )
    )

    figure.update_layout(
        title="낙폭(Drawdown)",
        xaxis_title="청산시간",
        yaxis_title="낙폭(%)",
        height=350,
        hovermode="x unified",
    )

    return figure


# ==================================================
# 화면 구성
# ==================================================

def show_summary(dataframe):
    total_trades = len(dataframe)

    wins = int(
        (dataframe["손익"] > 0).sum()
    )

    losses = int(
        (dataframe["손익"] < 0).sum()
    )

    win_rate = (
        wins / total_trades * 100
        if total_trades > 0
        else 0.0
    )

    total_profit = float(
        dataframe["손익"].sum()
    )

    profit_factor = (
        calculate_profit_factor(
            dataframe
        )
    )

    maximum_drawdown = (
        calculate_max_drawdown(
            dataframe
        )
    )

    first, second, third, fourth = st.columns(
        4
    )

    with first:
        st.metric(
            "총 거래",
            f"{total_trades}회",
            f"승 {wins} / 패 {losses}",
        )

    with second:
        st.metric(
            "승률",
            f"{win_rate:.2f}%",
        )

    with third:
        st.metric(
            "누적 손익",
            f"{total_profit:+,.0f}원",
        )

    with fourth:
        profit_factor_text = (
            "∞"
            if profit_factor
            == float("inf")
            else f"{profit_factor:.2f}"
        )

        st.metric(
            "Profit Factor",
            profit_factor_text,
        )

    first, second, third, fourth = st.columns(
        4
    )

    with first:
        st.metric(
            "최대 낙폭",
            f"-{maximum_drawdown:.3f}%",
        )

    with second:
        st.metric(
            "최대 연승",
            (
                f"{calculate_max_streak(dataframe, '승리')}회"
            ),
        )

    with third:
        st.metric(
            "최대 연패",
            (
                f"{calculate_max_streak(dataframe, '손실')}회"
            ),
        )

    with fourth:
        average_holding = int(
            dataframe["보유초"].mean()
        )

        st.metric(
            "평균 보유시간",
            format_holding_time(
                average_holding
            ),
        )


def show_group_section(
    dataframe,
    group_column,
    title,
):
    statistics = create_group_statistics(
        dataframe,
        group_column,
    )

    st.subheader(title)

    if statistics.empty:
        st.info("분석할 데이터가 없습니다.")
        return

    first, second = st.columns(
        [1.2, 1]
    )

    with first:
        st.dataframe(
            statistics,
            use_container_width=True,
            hide_index=True,
            column_config={
                "승률": (
                    st.column_config.NumberColumn(
                        format="%.2f%%"
                    )
                ),
                "누적손익": (
                    st.column_config.NumberColumn(
                        format="%+,.0f원"
                    )
                ),
                "평균손익": (
                    st.column_config.NumberColumn(
                        format="%+,.0f원"
                    )
                ),
                "평균수익률": (
                    st.column_config.NumberColumn(
                        format="%+.3f%%"
                    )
                ),
                "Profit Factor": (
                    st.column_config.NumberColumn(
                        format="%.2f"
                    )
                ),
            },
        )

    with second:
        chart = px.bar(
            statistics,
            x=group_column,
            y="누적손익",
            title=f"{title} 누적손익",
            text_auto=".3s",
        )

        chart.update_layout(
            height=420
        )

        st.plotly_chart(
            chart,
            use_container_width=True,
        )


def main():
    st.set_page_config(
        page_title="BinanceBot 거래 분석",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 BinanceBot 거래 분석")

    st.caption(
        "trade_log.csv에 쌓인 "
        "실시간 가상매매 성적 분석"
    )

    dataframe = load_trades()

    if dataframe.empty:
        st.info(
            "아직 분석할 청산 거래가 없습니다. "
            "runner.py를 계속 실행해 거래를 쌓아주세요."
        )
        return

    with st.sidebar:
        st.header("분석 필터")

        minimum_date = (
            dataframe["진입시간"]
            .min()
            .date()
        )

        maximum_date = (
            dataframe["진입시간"]
            .max()
            .date()
        )

        date_range = st.date_input(
            "분석 기간",
            value=(
                minimum_date,
                maximum_date,
            ),
            min_value=minimum_date,
            max_value=maximum_date,
        )

        available_symbols = sorted(
            dataframe["종목"]
            .dropna()
            .unique()
            .tolist()
        )

        selected_symbols = st.multiselect(
            "종목",
            available_symbols,
            default=available_symbols,
        )

        selected_sides = st.multiselect(
            "방향",
            ["LONG", "SHORT"],
            default=["LONG", "SHORT"],
        )

    filtered = dataframe.copy()

    if (
        isinstance(date_range, tuple)
        and len(date_range) == 2
    ):
        start_date, end_date = date_range

        filtered = filtered[
            (
                filtered[
                    "진입시간"
                ].dt.date
                >= start_date
            )
            & (
                filtered[
                    "진입시간"
                ].dt.date
                <= end_date
            )
        ]

    filtered = filtered[
        filtered["종목"].isin(
            selected_symbols
        )
    ]

    filtered = filtered[
        filtered["방향"].isin(
            selected_sides
        )
    ]

    if filtered.empty:
        st.warning(
            "선택한 조건에 해당하는 "
            "거래가 없습니다."
        )
        return

    show_summary(filtered)

    st.divider()

    curve_tab, breakdown_tab, records_tab = (
        st.tabs(
            [
                "잔고와 낙폭",
                "세부 분석",
                "거래 내역",
            ]
        )
    )

    with curve_tab:
        st.plotly_chart(
            create_equity_chart(filtered),
            use_container_width=True,
        )

        st.plotly_chart(
            create_drawdown_chart(filtered),
            use_container_width=True,
        )

    with breakdown_tab:
        show_group_section(
            filtered,
            "방향",
            "LONG / SHORT별 성과",
        )

        show_group_section(
            filtered,
            "종목",
            "코인별 성과",
        )

        show_group_section(
            filtered,
            "요일",
            "요일별 성과",
        )

        show_group_section(
            filtered,
            "시간대",
            "시간대별 성과",
        )

        show_group_section(
            filtered,
            "청산이유",
            "청산 이유별 성과",
        )

    with records_tab:
        st.dataframe(
            filtered.iloc[::-1],
            use_container_width=True,
            hide_index=True,
            column_config={
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
                "추정잔고": (
                    st.column_config.NumberColumn(
                        format="%,.0f원"
                    )
                ),
            },
        )


if __name__ == "__main__":
    main()