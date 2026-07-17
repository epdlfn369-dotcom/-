import atexit
import json
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
LOCK_FILE = "runner.lock"


# ==================================================
# 시간과 로그
# ==================================================

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


# ==================================================
# 중복 실행 방지
# ==================================================

def is_process_running(pid):
    if not isinstance(pid, int):
        return False

    if pid <= 0:
        return False

    try:
        # Windows에서 PID 존재 여부 확인
        result = subprocess.run(
            [
                "tasklist",
                "/FI",
                f"PID eq {pid}",
                "/NH",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )

        output = result.stdout.strip()

        if not output:
            return False

        if "정보:" in output:
            return False

        if "INFO:" in output:
            return False

        return str(pid) in output

    except Exception:
        return False


def load_lock():
    if not os.path.exists(LOCK_FILE):
        return {}

    try:
        with open(
            LOCK_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def remove_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

    except OSError:
        pass


def acquire_lock():
    existing_lock = load_lock()

    existing_pid = existing_lock.get(
        "pid"
    )

    try:
        existing_pid = int(existing_pid)

    except (
        TypeError,
        ValueError,
    ):
        existing_pid = 0

    if (
        existing_pid
        and existing_pid != os.getpid()
        and is_process_running(existing_pid)
    ):
        print()
        print("=" * 65)
        print("BinanceBot은 이미 실행 중입니다.")
        print("=" * 65)
        print(
            f"실행 중인 관리자 PID: "
            f"{existing_pid}"
        )
        print(
            f"시작 시각: "
            f"{existing_lock.get('started_at', '확인 불가')}"
        )
        print()
        print(
            "중복 실행은 포지션 중복 진입을 "
            "일으킬 수 있어 차단했습니다."
        )
        print("=" * 65)

        return False

    # 종료된 프로그램의 오래된 잠금파일 제거
    remove_lock()

    lock_data = {
        "pid": os.getpid(),
        "started_at": current_time(),
        "runner_file": os.path.abspath(
            __file__
        ),
    }

    temporary_file = LOCK_FILE + ".tmp"

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            lock_data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(
        temporary_file,
        LOCK_FILE,
    )

    atexit.register(
        remove_lock
    )

    return True


# ==================================================
# 자식 프로세스 출력 처리
# ==================================================

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


# ==================================================
# 봇 자동 실행 관리자
# ==================================================

def run_bot():
    if not acquire_lock():
        input(
            "\n엔터를 누르면 창을 닫습니다..."
        )
        return

    fast_crash_count = 0
    process = None

    write_log("=" * 70)
    write_log("BinanceBot 자동 실행 관리자")
    write_log("=" * 70)

    write_log(
        f"관리자 PID: {os.getpid()}"
    )

    write_log(
        f"실행 파일: {BOT_FILE}"
    )

    write_log(
        "중복 실행 방지: 활성화"
    )

    write_log(
        "봇 종료 시 자동으로 재시작합니다."
    )

    write_log(
        "완전히 종료하려면 Ctrl + C"
    )

    write_log("")

    while True:
        started_at = time.time()

        write_log(
            f"[{current_time()}] "
            "BinanceBot을 시작합니다."
        )

        try:
            child_environment = (
                os.environ.copy()
            )

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
                args=(
                    process.stdout,
                    "",
                ),
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

            stdout_thread.join(
                timeout=2
            )

            stderr_thread.join(
                timeout=2
            )

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

        write_log(
            f"종료 코드: {exit_code}"
        )

        write_log(
            f"실행 시간: "
            f"{running_seconds:.1f}초"
        )

        if (
            running_seconds
            < FAST_CRASH_SECONDS
        ):
            fast_crash_count += 1

        else:
            fast_crash_count = 0

        if (
            fast_crash_count
            >= MAX_FAST_CRASHES
        ):
            write_log("")
            write_log(
                "짧은 시간 안에 오류가 "
                f"{MAX_FAST_CRASHES}회 반복됐습니다."
            )

            write_log(
                "무한 재시작을 막기 위해 "
                "실행을 중단합니다."
            )

            write_log(
                "logs 폴더의 최신 로그를 "
                "확인하세요."
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

    remove_lock()


if __name__ == "__main__":
    run_bot()