import os
import subprocess
import sys
import threading
import time
from datetime import datetime


BOT_FILE = "main.py"

RESTART_DELAY_SECONDS = 10
MAX_FAST_CRASHES = 5
FAST_CRASH_SECONDS = 30

LOG_DIRECTORY = "logs"


def current_time():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def get_log_file_path():
    os.makedirs(
        LOG_DIRECTORY,
        exist_ok=True,
    )

    filename = (
        datetime.now().strftime("%Y-%m-%d")
        + ".log"
    )

    return os.path.join(
        LOG_DIRECTORY,
        filename,
    )


def write_log(message):
    text = str(message)

    print(
        text,
        flush=True,
    )

    try:
        with open(
            get_log_file_path(),
            "a",
            encoding="utf-8-sig",
        ) as file:
            file.write(text + "\n")

    except OSError as error:
        print(
            f"로그 저장 실패: {error}",
            flush=True,
        )


def read_process_output(
    pipe,
    prefix="",
):
    try:
        for line in iter(
            pipe.readline,
            "",
        ):
            clean_line = line.rstrip()

            if not clean_line:
                continue

            write_log(
                f"{prefix}{clean_line}"
            )

    finally:
        pipe.close()


def run_bot():
    fast_crash_count = 0
    process = None

    write_log("=" * 70)
    write_log("BinanceBot 자동 실행 관리자")
    write_log("=" * 70)
    write_log(f"실행 파일: {BOT_FILE}")
    write_log("봇 종료 시 자동으로 재시작합니다.")
    write_log("완전히 종료하려면 Ctrl + C")
    write_log("")

    while True:
        started_at = time.time()

        write_log(
            f"[{current_time()}] "
            "BinanceBot을 시작합니다."
        )

        try:
            child_environment = os.environ.copy()

            # main.py 출력 인코딩을 UTF-8로 강제
            child_environment[
                "PYTHONIOENCODING"
            ] = "utf-8"

            child_environment[
                "PYTHONUTF8"
            ] = "1"

            process = subprocess.Popen(
                [
                    sys.executable,
                    "-u",
                    BOT_FILE,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=child_environment,
            )

            stdout_thread = threading.Thread(
                target=read_process_output,
                args=(process.stdout, ""),
                daemon=True,
            )

            stderr_thread = threading.Thread(
                target=read_process_output,
                args=(
                    process.stderr,
                    "[오류] ",
                ),
                daemon=True,
            )

            stdout_thread.start()
            stderr_thread.start()

            exit_code = process.wait()

            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)

        except KeyboardInterrupt:
            write_log("")
            write_log(
                f"[{current_time()}] "
                "사용자가 실행을 종료했습니다."
            )

            if (
                process is not None
                and process.poll() is None
            ):
                try:
                    process.terminate()
                    process.wait(timeout=5)

                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass

            break

        except Exception as error:
            exit_code = -1

            write_log(
                f"[{current_time()}] "
                f"실행 관리자 오류: "
                f"{repr(error)}"
            )

        running_seconds = (
            time.time() - started_at
        )

        write_log("")
        write_log(
            f"[{current_time()}] "
            "봇이 종료됐습니다."
        )
        write_log(f"종료 코드: {exit_code}")
        write_log(
            f"실행 시간: "
            f"{running_seconds:.1f}초"
        )

        if running_seconds < FAST_CRASH_SECONDS:
            fast_crash_count += 1
        else:
            fast_crash_count = 0

        if fast_crash_count >= MAX_FAST_CRASHES:
            write_log("")
            write_log(
                "짧은 시간 안에 오류가 "
                f"{MAX_FAST_CRASHES}회 반복됐습니다."
            )
            write_log(
                "무한 재시작을 막기 위해 "
                "실행을 중단합니다."
            )
            break

        write_log(
            f"{RESTART_DELAY_SECONDS}초 후 "
            "자동으로 다시 시작합니다."
        )

        try:
            time.sleep(
                RESTART_DELAY_SECONDS
            )

        except KeyboardInterrupt:
            write_log(
                "자동 재시작을 취소했습니다."
            )
            break


if __name__ == "__main__":
    run_bot()