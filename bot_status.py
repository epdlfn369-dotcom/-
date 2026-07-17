import json
import os
from datetime import datetime


STATUS_FILE = "bot_status.json"


def now_text():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def load_status():
    default_status = {
        "running": False,
        "started_at": "",
        "stopped_at": "",
        "last_heartbeat": "",
        "last_scan_started": "",
        "last_scan_completed": "",
        "last_error": "",
        "message": "상태 기록 없음",
    }

    if not os.path.exists(STATUS_FILE):
        return default_status

    try:
        with open(
            STATUS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            saved_status = json.load(file)

        if isinstance(saved_status, dict):
            default_status.update(
                saved_status
            )

    except Exception:
        pass

    return default_status


def save_status(**updates):
    status = load_status()
    status.update(updates)

    temporary_file = (
        STATUS_FILE + ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            status,
            file,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(
        temporary_file,
        STATUS_FILE,
    )


def mark_started():
    current_time = now_text()

    save_status(
        running=True,
        started_at=current_time,
        stopped_at="",
        last_heartbeat=current_time,
        last_error="",
        message="봇 실행 중",
    )


def mark_heartbeat(message="정상 작동 중"):
    save_status(
        running=True,
        last_heartbeat=now_text(),
        message=message,
    )


def mark_scan_started():
    current_time = now_text()

    save_status(
        running=True,
        last_heartbeat=current_time,
        last_scan_started=current_time,
        message="시장 스캔 중",
    )


def mark_scan_completed():
    current_time = now_text()

    save_status(
        running=True,
        last_heartbeat=current_time,
        last_scan_completed=current_time,
        message="시장 스캔 완료",
    )


def mark_error(error):
    save_status(
        running=True,
        last_heartbeat=now_text(),
        last_error=repr(error),
        message="오류 발생 후 재시도 중",
    )


def mark_stopped(message="사용자가 봇을 종료함"):
    current_time = now_text()

    save_status(
        running=False,
        stopped_at=current_time,
        last_heartbeat=current_time,
        message=message,
    )


if __name__ == "__main__":
    print(
        json.dumps(
            load_status(),
            ensure_ascii=False,
            indent=2,
        )
    )