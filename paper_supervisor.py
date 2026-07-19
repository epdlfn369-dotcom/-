import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(
    __file__
).resolve().parent

MAIN_FILE = (
    PROJECT_ROOT / "main.py"
)

WATCH_FILE = (
    PROJECT_ROOT
    / "paper_report_watch.py"
)

SUPERVISOR_LOG = (
    PROJECT_ROOT
    / "logs"
    / "supervisor.log"
)


def write_log(message):
    SUPERVISOR_LOG.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = (
        datetime.now()
        .strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    line = (
        f"[{timestamp}] "
        f"{message}"
    )

    print(
        line,
        flush=True,
    )

    try:
        with SUPERVISOR_LOG.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                line + "\n"
            )

    except OSError:
        pass


def start_process(
    arguments,
    title,
):
    creation_flags = 0

    if sys.platform == "win32":
        creation_flags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
        )

    write_log(
        f"{title} 시작: "
        + " ".join(arguments)
    )

    return subprocess.Popen(
        arguments,
        cwd=PROJECT_ROOT,
        creationflags=creation_flags,
    )


def stop_process(
    process,
    title,
):
    if process is None:
        return

    if process.poll() is not None:
        return

    write_log(
        f"{title} 종료 요청"
    )

    try:
        process.terminate()
        process.wait(
            timeout=8
        )

    except subprocess.TimeoutExpired:
        write_log(
            f"{title} 강제 종료"
        )

        process.kill()

    except OSError:
        pass


def validate_files(
    with_monitor,
):
    missing = []

    if not MAIN_FILE.exists():
        missing.append(
            str(MAIN_FILE)
        )

    if (
        with_monitor
        and not WATCH_FILE.exists()
    ):
        missing.append(
            str(WATCH_FILE)
        )

    if missing:
        print(
            "필수 파일을 찾지 못했습니다."
        )

        for path in missing:
            print(
                f"- {path}"
            )

        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "BinanceBot 자동 재시작 "
            "통합 실행기"
        )
    )

    parser.add_argument(
        "--restart-delay",
        type=int,
        default=10,
        help=(
            "봇 종료 후 재시작 대기시간. "
            "기본값 10초"
        ),
    )

    parser.add_argument(
        "--monitor-refresh",
        type=int,
        default=60,
        help=(
            "모니터 갱신 주기. "
            "기본값 60초"
        ),
    )

    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help=(
            "리포트 모니터를 실행하지 않음"
        ),
    )

    parser.add_argument(
        "--max-restarts",
        type=int,
        default=0,
        help=(
            "최대 자동 재시작 횟수. "
            "0이면 제한 없음"
        ),
    )

    args = parser.parse_args()

    if args.restart_delay < 3:
        parser.error(
            "--restart-delay는 "
            "최소 3초 이상이어야 합니다."
        )

    if args.monitor_refresh < 5:
        parser.error(
            "--monitor-refresh는 "
            "최소 5초 이상이어야 합니다."
        )

    with_monitor = (
        not args.no_monitor
    )

    validate_files(
        with_monitor
    )

    bot_process = None
    monitor_process = None
    restart_count = 0

    try:
        if with_monitor:
            monitor_process = (
                start_process(
                    [
                        sys.executable,
                        str(WATCH_FILE),
                        "--refresh",
                        str(
                            args.monitor_refresh
                        ),
                    ],
                    "성과 모니터",
                )
            )

        while True:
            bot_process = start_process(
                [
                    sys.executable,
                    "-u",
                    str(MAIN_FILE),
                ],
                "BinanceBot",
            )

            exit_code = (
                bot_process.wait()
            )

            write_log(
                "BinanceBot 종료 감지 | "
                f"종료코드: {exit_code}"
            )

            restart_count += 1

            if (
                args.max_restarts > 0
                and restart_count
                > args.max_restarts
            ):
                write_log(
                    "최대 재시작 횟수 초과. "
                    "통합 실행기를 종료합니다."
                )
                break

            write_log(
                f"{args.restart_delay}초 후 "
                f"자동 재시작 "
                f"({restart_count}회)"
            )

            time.sleep(
                args.restart_delay
            )

            if (
                with_monitor
                and (
                    monitor_process is None
                    or monitor_process.poll()
                    is not None
                )
            ):
                write_log(
                    "성과 모니터 종료 감지. "
                    "다시 시작합니다."
                )

                monitor_process = (
                    start_process(
                        [
                            sys.executable,
                            str(WATCH_FILE),
                            "--refresh",
                            str(
                                args.monitor_refresh
                            ),
                        ],
                        "성과 모니터",
                    )
                )

    except KeyboardInterrupt:
        write_log(
            "사용자 종료 요청 감지"
        )

    finally:
        stop_process(
            bot_process,
            "BinanceBot",
        )

        stop_process(
            monitor_process,
            "성과 모니터",
        )

        write_log(
            "통합 실행기 종료"
        )


if __name__ == "__main__":
    main()
