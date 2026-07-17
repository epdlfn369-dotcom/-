import json
import os
from datetime import datetime

import streamlit as st


STATUS_FILE = "bot_status.json"
LOG_DIRECTORY = "logs"


def load_status():
    if not os.path.exists(STATUS_FILE):
        return {}

    try:
        with open(
            STATUS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except Exception as error:
        st.error(
            f"상태 파일 읽기 오류: {error}"
        )
        return {}


def parse_datetime(value):
    if not value:
        return None

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d %H:%M:%S",
        )

    except ValueError:
        return None


def calculate_heartbeat_age(
    heartbeat_text,
):
    heartbeat_time = parse_datetime(
        heartbeat_text
    )

    if heartbeat_time is None:
        return None

    return int(
        (
            datetime.now()
            - heartbeat_time
        ).total_seconds()
    )


def format_age(seconds):
    if seconds is None:
        return "확인 불가"

    if seconds < 60:
        return f"{seconds}초 전"

    minutes = seconds // 60

    if minutes < 60:
        return f"{minutes}분 전"

    hours = minutes // 60
    remaining_minutes = (
        minutes % 60
    )

    return (
        f"{hours}시간 "
        f"{remaining_minutes}분 전"
    )


def get_latest_log_file():
    if not os.path.exists(
        LOG_DIRECTORY
    ):
        return None

    log_files = [
        filename
        for filename in os.listdir(
            LOG_DIRECTORY
        )
        if filename.endswith(".log")
    ]

    if not log_files:
        return None

    log_files.sort(
        reverse=True
    )

    return os.path.join(
        LOG_DIRECTORY,
        log_files[0],
    )


def read_latest_log_lines(
    line_count=100,
):
    log_file = get_latest_log_file()

    if log_file is None:
        return ""

    try:
        with open(
            log_file,
            "r",
            encoding="utf-8-sig",
        ) as file:
            lines = file.readlines()

        return "".join(
            lines[-line_count:]
        )

    except Exception as error:
        return (
            f"로그 읽기 실패: {error}"
        )


@st.fragment(run_every="5s")
def show_live_status():
    status = load_status()

    if not status:
        st.warning(
            "bot_status.json이 없습니다. "
            "runner.py를 실행하세요."
        )
        return

    running_flag = bool(
        status.get(
            "running",
            False,
        )
    )

    heartbeat_text = status.get(
        "last_heartbeat",
        "",
    )

    heartbeat_age = (
        calculate_heartbeat_age(
            heartbeat_text
        )
    )

    # 30초 이상 하트비트가 없으면
    # 파일에 running=True여도 정지 의심
    if (
        running_flag
        and heartbeat_age is not None
        and heartbeat_age <= 30
    ):
        display_status = "정상 실행 중"
        status_type = "success"

    elif running_flag:
        display_status = (
            "응답 지연 또는 정지 의심"
        )
        status_type = "warning"

    else:
        display_status = "중지됨"
        status_type = "error"

    first, second, third, fourth = (
        st.columns(4)
    )

    with first:
        st.metric(
            "봇 상태",
            display_status,
        )

    with second:
        st.metric(
            "마지막 응답",
            format_age(
                heartbeat_age
            ),
        )

    with third:
        st.metric(
            "마지막 스캔",
            status.get(
                "last_scan_completed",
                "기록 없음",
            )
            or "기록 없음",
        )

    with fourth:
        st.metric(
            "실행 시작",
            status.get(
                "started_at",
                "기록 없음",
            )
            or "기록 없음",
        )

    message = status.get(
        "message",
        "",
    )

    if status_type == "success":
        st.success(
            f"현재 상태: {message}"
        )

    elif status_type == "warning":
        st.warning(
            f"현재 상태: {message}"
        )

    else:
        st.error(
            f"현재 상태: {message}"
        )

    st.write(
        "**최근 스캔 시작:**",
        status.get(
            "last_scan_started",
            "기록 없음",
        )
        or "기록 없음",
    )

    st.write(
        "**최근 스캔 완료:**",
        status.get(
            "last_scan_completed",
            "기록 없음",
        )
        or "기록 없음",
    )

    last_error = status.get(
        "last_error",
        "",
    )

    if last_error:
        st.error(
            f"마지막 오류: {last_error}"
        )
    else:
        st.info(
            "기록된 최근 오류가 없습니다."
        )


def main():
    st.set_page_config(
        page_title="BinanceBot 시스템 상태",
        page_icon="🖥️",
        layout="wide",
    )

    st.title(
        "🖥️ BinanceBot 시스템 상태"
    )

    st.caption(
        "봇 상태는 5초마다 자동으로 갱신됩니다."
    )

    show_live_status()

    st.divider()

    st.subheader(
        "최근 시스템 로그"
    )

    line_count = st.slider(
        "표시할 로그 줄 수",
        min_value=20,
        max_value=500,
        value=100,
        step=20,
    )

    log_text = read_latest_log_lines(
        line_count
    )

    if log_text:
        st.code(
            log_text,
            language="text",
        )
    else:
        st.info(
            "저장된 시스템 로그가 없습니다."
        )


if __name__ == "__main__":
    main()