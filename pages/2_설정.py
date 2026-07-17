import json
import os

import streamlit as st


SETTINGS_FILE = "settings.json"


DEFAULT_SETTINGS = {
    "stop_loss_percent": 1.0,
    "take_profit_percent": 3.0,
    "max_positions": 3,
    "position_size_percent": 10.0,
    "scan_interval_seconds": 60,
    "minimum_entry_score": 45,
    "round_trip_fee_percent": 0.10,
}


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()

    try:
        with open(
            SETTINGS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            saved = json.load(file)

        settings = DEFAULT_SETTINGS.copy()
        settings.update(saved)

        return settings

    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    temporary_file = SETTINGS_FILE + ".tmp"

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

    st.caption(
        "가상매매 봇의 주요 설정을 브라우저에서 관리합니다."
    )

    settings = load_settings()

    with st.form("settings_form"):
        first, second = st.columns(2)

        with first:
            stop_loss_percent = st.number_input(
                "손절률(%)",
                min_value=0.1,
                max_value=20.0,
                value=float(
                    settings["stop_loss_percent"]
                ),
                step=0.1,
            )

            take_profit_percent = st.number_input(
                "익절률(%)",
                min_value=0.1,
                max_value=50.0,
                value=float(
                    settings["take_profit_percent"]
                ),
                step=0.1,
            )

            max_positions = st.number_input(
                "최대 동시 포지션",
                min_value=1,
                max_value=20,
                value=int(
                    settings["max_positions"]
                ),
                step=1,
            )

            position_size_percent = st.number_input(
                "포지션당 잔고 사용 비율(%)",
                min_value=1.0,
                max_value=100.0,
                value=float(
                    settings["position_size_percent"]
                ),
                step=1.0,
            )

        with second:
            scan_interval_seconds = st.number_input(
                "시장 스캔 주기(초)",
                min_value=10,
                max_value=3600,
                value=int(
                    settings["scan_interval_seconds"]
                ),
                step=10,
            )

            minimum_entry_score = st.number_input(
                "최소 진입 점수",
                min_value=0,
                max_value=200,
                value=int(
                    settings["minimum_entry_score"]
                ),
                step=5,
            )

            round_trip_fee_percent = st.number_input(
                "왕복 수수료 가정(%)",
                min_value=0.0,
                max_value=5.0,
                value=float(
                    settings["round_trip_fee_percent"]
                ),
                step=0.01,
            )

        submitted = st.form_submit_button(
            "💾 설정 저장",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        new_settings = {
            "stop_loss_percent": float(
                stop_loss_percent
            ),
            "take_profit_percent": float(
                take_profit_percent
            ),
            "max_positions": int(
                max_positions
            ),
            "position_size_percent": float(
                position_size_percent
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
        }

        save_settings(new_settings)

        st.success(
            "설정을 저장했습니다. "
            "현재 봇에는 다음 재시작부터 적용됩니다."
        )

    st.divider()

    st.subheader("현재 저장된 설정")

    st.json(
        load_settings()
    )

    st.warning(
        "아직 main.py가 settings.json을 읽도록 연결되지 않았습니다. "
        "다음 단계에서 봇 실행 설정과 연결합니다."
    )


if __name__ == "__main__":
    main()