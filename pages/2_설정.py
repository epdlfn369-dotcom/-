import json
import os

import streamlit as st


SETTINGS_FILE = "settings.json"


DEFAULT_SETTINGS = {
    "starting_balance": 1_000_000,
    "position_size_percent": 10.0,
    "max_positions": 3,

    "exit_mode": "FIXED",

    "stop_loss_percent": 1.0,
    "take_profit_percent": 3.0,

    "atr_stop_multiplier": 2.0,
    "atr_take_profit_multiplier": 6.0,

    "minimum_stop_percent": 0.5,
    "maximum_stop_percent": 2.0,

    "minimum_take_profit_percent": 1.5,
    "maximum_take_profit_percent": 6.0,

    "scan_interval_seconds": 60,
    "minimum_entry_score": 45,
    "round_trip_fee_percent": 0.10,
    "top_volume_symbols": 20,

    "daily_stop_loss_percent": 5.0,
    "daily_take_profit_percent": 10.0,
}


def load_settings():
    settings = DEFAULT_SETTINGS.copy()

    if not os.path.exists(
        SETTINGS_FILE
    ):
        return settings

    try:
        with open(
            SETTINGS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            saved = json.load(file)

        if isinstance(saved, dict):
            settings.update(saved)

    except Exception:
        pass

    return settings


def save_settings(settings):
    temporary_file = (
        SETTINGS_FILE + ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            settings,
            file,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(
        temporary_file,
        SETTINGS_FILE,
    )


def main():
    st.set_page_config(
        page_title="BinanceBot 설정",
        page_icon="⚙️",
        layout="wide",
    )

    st.title("⚙️ BinanceBot 설정")

    settings = load_settings()

    with st.form(
        "settings_form"
    ):
        st.subheader(
            "기본 거래 설정"
        )

        first, second, third = (
            st.columns(3)
        )

        with first:
            position_size_percent = (
                st.number_input(
                    "포지션당 잔고 사용 비율(%)",
                    min_value=1.0,
                    max_value=100.0,
                    value=float(
                        settings[
                            "position_size_percent"
                        ]
                    ),
                    step=1.0,
                )
            )

            max_positions = (
                st.number_input(
                    "최대 동시 포지션",
                    min_value=1,
                    max_value=20,
                    value=int(
                        settings[
                            "max_positions"
                        ]
                    ),
                    step=1,
                )
            )

        with second:
            minimum_entry_score = (
                st.number_input(
                    "최소 진입 점수",
                    min_value=0,
                    max_value=200,
                    value=int(
                        settings[
                            "minimum_entry_score"
                        ]
                    ),
                    step=5,
                )
            )

            top_volume_symbols = (
                st.number_input(
                    "분석할 거래대금 상위 종목",
                    min_value=5,
                    max_value=200,
                    value=int(
                        settings[
                            "top_volume_symbols"
                        ]
                    ),
                    step=5,
                )
            )

        with third:
            scan_interval_seconds = (
                st.number_input(
                    "시장 스캔 주기(초)",
                    min_value=10,
                    max_value=3600,
                    value=int(
                        settings[
                            "scan_interval_seconds"
                        ]
                    ),
                    step=10,
                )
            )

            round_trip_fee_percent = (
                st.number_input(
                    "왕복 수수료 가정(%)",
                    min_value=0.0,
                    max_value=5.0,
                    value=float(
                        settings[
                            "round_trip_fee_percent"
                        ]
                    ),
                    step=0.01,
                )
            )

        st.divider()

        st.subheader(
            "손절·익절 방식"
        )

        exit_mode = st.radio(
            "청산 방식 선택",
            options=[
                "FIXED",
                "ATR",
            ],
            index=(
                0
                if settings[
                    "exit_mode"
                ] == "FIXED"
                else 1
            ),
            format_func=lambda value: (
                "고정 손절·익절"
                if value == "FIXED"
                else "ATR 변동성 기반"
            ),
            horizontal=True,
        )

        fixed_tab, atr_tab = st.tabs(
            [
                "고정 방식 설정",
                "ATR 방식 설정",
            ]
        )

        with fixed_tab:
            first, second = (
                st.columns(2)
            )

            with first:
                stop_loss_percent = (
                    st.number_input(
                        "고정 손절률(%)",
                        min_value=0.1,
                        max_value=20.0,
                        value=float(
                            settings[
                                "stop_loss_percent"
                            ]
                        ),
                        step=0.1,
                    )
                )

            with second:
                take_profit_percent = (
                    st.number_input(
                        "고정 익절률(%)",
                        min_value=0.1,
                        max_value=50.0,
                        value=float(
                            settings[
                                "take_profit_percent"
                            ]
                        ),
                        step=0.1,
                    )
                )

        with atr_tab:
            first, second = (
                st.columns(2)
            )

            with first:
                atr_stop_multiplier = (
                    st.number_input(
                        "ATR 손절 배수",
                        min_value=0.1,
                        max_value=20.0,
                        value=float(
                            settings[
                                "atr_stop_multiplier"
                            ]
                        ),
                        step=0.1,
                    )
                )

                minimum_stop_percent = (
                    st.number_input(
                        "최소 손절폭(%)",
                        min_value=0.1,
                        max_value=20.0,
                        value=float(
                            settings[
                                "minimum_stop_percent"
                            ]
                        ),
                        step=0.1,
                    )
                )

                maximum_stop_percent = (
                    st.number_input(
                        "최대 손절폭(%)",
                        min_value=0.1,
                        max_value=20.0,
                        value=float(
                            settings[
                                "maximum_stop_percent"
                            ]
                        ),
                        step=0.1,
                    )
                )

            with second:
                atr_take_profit_multiplier = (
                    st.number_input(
                        "ATR 익절 배수",
                        min_value=0.1,
                        max_value=50.0,
                        value=float(
                            settings[
                                "atr_take_profit_multiplier"
                            ]
                        ),
                        step=0.1,
                    )
                )

                minimum_take_profit_percent = (
                    st.number_input(
                        "최소 익절폭(%)",
                        min_value=0.1,
                        max_value=50.0,
                        value=float(
                            settings[
                                "minimum_take_profit_percent"
                            ]
                        ),
                        step=0.1,
                    )
                )

                maximum_take_profit_percent = (
                    st.number_input(
                        "최대 익절폭(%)",
                        min_value=0.1,
                        max_value=50.0,
                        value=float(
                            settings[
                                "maximum_take_profit_percent"
                            ]
                        ),
                        step=0.1,
                    )
                )

        st.divider()

        st.subheader(
            "일일 거래 제한"
        )

        first, second = st.columns(2)

        with first:
            daily_stop_loss_percent = (
                st.number_input(
                    "일일 최대 손실(%)",
                    min_value=0.1,
                    max_value=100.0,
                    value=float(
                        settings[
                            "daily_stop_loss_percent"
                        ]
                    ),
                    step=0.5,
                )
            )

        with second:
            daily_take_profit_percent = (
                st.number_input(
                    "일일 목표 수익(%)",
                    min_value=0.1,
                    max_value=100.0,
                    value=float(
                        settings[
                            "daily_take_profit_percent"
                        ]
                    ),
                    step=0.5,
                )
            )

        submitted = (
            st.form_submit_button(
                "💾 설정 저장",
                type="primary",
                use_container_width=True,
            )
        )

    if submitted:
        if (
            minimum_stop_percent
            > maximum_stop_percent
        ):
            st.error(
                "최소 손절폭은 최대 손절폭보다 "
                "클 수 없습니다."
            )
            return

        if (
            minimum_take_profit_percent
            > maximum_take_profit_percent
        ):
            st.error(
                "최소 익절폭은 최대 익절폭보다 "
                "클 수 없습니다."
            )
            return

        new_settings = {
            "starting_balance": int(
                settings[
                    "starting_balance"
                ]
            ),

            "position_size_percent": float(
                position_size_percent
            ),

            "max_positions": int(
                max_positions
            ),

            "exit_mode": exit_mode,

            "stop_loss_percent": float(
                stop_loss_percent
            ),

            "take_profit_percent": float(
                take_profit_percent
            ),

            "atr_stop_multiplier": float(
                atr_stop_multiplier
            ),

            "atr_take_profit_multiplier": float(
                atr_take_profit_multiplier
            ),

            "minimum_stop_percent": float(
                minimum_stop_percent
            ),

            "maximum_stop_percent": float(
                maximum_stop_percent
            ),

            "minimum_take_profit_percent": float(
                minimum_take_profit_percent
            ),

            "maximum_take_profit_percent": float(
                maximum_take_profit_percent
            ),

            "scan_interval_seconds": int(
                scan_interval_seconds
            ),

            "minimum_entry_score": int(
                minimum_entry_score
            ),

            "round_trip_fee_percent": float(
                round_trip_fee_percent
            ),

            "top_volume_symbols": int(
                top_volume_symbols
            ),

            "daily_stop_loss_percent": float(
                daily_stop_loss_percent
            ),

            "daily_take_profit_percent": float(
                daily_take_profit_percent
            ),
        }

        save_settings(
            new_settings
        )

        st.success(
            "설정을 저장했습니다. "
            "봇을 재시작하면 적용됩니다."
        )

    st.divider()

    st.subheader(
        "현재 저장된 설정"
    )

    st.json(
        load_settings()
    )


if __name__ == "__main__":
    main()