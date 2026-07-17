import streamlit as st

from bot_control import (
    disable_trading,
    enable_trading,
    load_control,
)


def main():
    st.set_page_config(
        page_title="BinanceBot 봇 제어",
        page_icon="🎛️",
        layout="wide",
    )

    st.title("🎛️ BinanceBot 봇 제어")

    st.caption(
        "신규 포지션 진입만 중지하거나 "
        "다시 활성화합니다."
    )

    control = load_control()

    trading_enabled = bool(
        control.get(
            "trading_enabled",
            True,
        )
    )

    first, second, third = st.columns(3)

    with first:
        st.metric(
            "신규 진입 상태",
            (
                "활성화"
                if trading_enabled
                else "일시정지"
            ),
        )

    with second:
        st.metric(
            "마지막 변경",
            control.get(
                "updated_at",
                "",
            )
            or "기록 없음",
        )

    with third:
        st.metric(
            "변경 주체",
            control.get(
                "updated_by",
                "",
            )
            or "기록 없음",
        )

    if trading_enabled:
        st.success(
            "현재 신규 포지션 진입이 "
            "활성화되어 있습니다."
        )
    else:
        st.warning(
            "현재 신규 포지션 진입이 "
            "일시정지 상태입니다."
        )

        reason = control.get(
            "reason",
            "",
        )

        if reason:
            st.write(
                f"**정지 사유:** {reason}"
            )

    st.divider()

    reason_text = st.text_input(
        "정지 사유",
        value="사용자가 대시보드에서 일시정지",
    )

    first, second = st.columns(2)

    with first:
        if st.button(
            "⏸ 신규 진입 일시정지",
            type="secondary",
            use_container_width=True,
        ):
            disable_trading(
                reason=reason_text,
                updated_by="dashboard",
            )

            st.success(
                "신규 진입을 일시정지했습니다."
            )

            st.rerun()

    with second:
        if st.button(
            "▶ 신규 진입 재개",
            type="primary",
            use_container_width=True,
        ):
            enable_trading(
                updated_by="dashboard",
            )

            st.success(
                "신규 진입을 다시 활성화했습니다."
            )

            st.rerun()

    st.divider()

    st.info(
        "일시정지 상태에서도 기존 포지션의 "
        "가격 감시와 손절·익절은 계속됩니다."
    )


if __name__ == "__main__":
    main()