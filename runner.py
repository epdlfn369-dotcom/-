import subprocess
import sys
import time
from datetime import datetime


BOT_FILE = "main.py"

RESTART_DELAY_SECONDS = 10
MAX_FAST_CRASHES = 5
FAST_CRASH_SECONDS = 30


def current_time():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def run_bot():
    fast_crash_count = 0

    print("=" * 60)
    print("BinanceBot 자동 실행 관리자")
    print("=" * 60)
    print(f"실행 파일: {BOT_FILE}")
    print("봇 종료 시 자동으로 재시작합니다.")
    print("완전히 종료하려면 Ctrl + C")
    print()

    while True:
        started_at = time.time()

        print(
            f"[{current_time()}] "
            "BinanceBot을 시작합니다."
        )

        try:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-u",
                    BOT_FILE,
                ]
            )

            exit_code = process.wait()

        except KeyboardInterrupt:
            print()
            print(
                f"[{current_time()}] "
                "사용자가 실행을 종료했습니다."
            )

            try:
                process.terminate()
            except Exception:
                pass

            break

        except Exception as error:
            exit_code = -1

            print(
                f"[{current_time()}] "
                f"실행 관리자 오류: {repr(error)}"
            )

        running_seconds = (
            time.time() - started_at
        )

        print()
        print(
            f"[{current_time()}] "
            f"봇이 종료됐습니다."
        )

        print(
            f"종료 코드: {exit_code}"
        )

        print(
            f"실행 시간: "
            f"{running_seconds:.1f}초"
        )

        if running_seconds < FAST_CRASH_SECONDS:
            fast_crash_count += 1
        else:
            fast_crash_count = 0

        if fast_crash_count >= MAX_FAST_CRASHES:
            print()
            print(
                "짧은 시간 안에 오류가 "
                f"{MAX_FAST_CRASHES}회 반복됐습니다."
            )

            print(
                "무한 재시작을 막기 위해 "
                "실행을 중단합니다."
            )

            print(
                "터미널의 마지막 오류 내용을 "
                "확인하세요."
            )

            break

        print(
            f"{RESTART_DELAY_SECONDS}초 후 "
            "자동으로 다시 시작합니다."
        )

        try:
            time.sleep(
                RESTART_DELAY_SECONDS
            )

        except KeyboardInterrupt:
            print()
            print("자동 재시작을 취소했습니다.")
            break


if __name__ == "__main__":
    run_bot()