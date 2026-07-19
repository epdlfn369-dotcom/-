import argparse
import os
import time
from datetime import datetime

import paper_report_v2


def clear_console():
    os.system(
        "cls"
        if os.name == "nt"
        else "clear"
    )


def print_header(
    refresh_seconds,
):
    print(
        "BinanceBot 실시간 가상매매 모니터"
    )
    print(
        f"자동 갱신: "
        f"{refresh_seconds}초"
    )
    print(
        "종료: Ctrl + C"
    )
    print()


def main():
    parser = argparse.ArgumentParser(
        description=(
            "BinanceBot 가상매매 "
            "실시간 모니터"
        )
    )

    parser.add_argument(
        "--refresh",
        type=int,
        default=60,
        help=(
            "화면 갱신 주기(초). "
            "기본값 60"
        ),
    )

    args = parser.parse_args()

    if args.refresh < 5:
        parser.error(
            "--refresh는 최소 5초 이상이어야 합니다."
        )

    try:
        while True:
            clear_console()

            print_header(
                args.refresh
            )

            try:
                paper_report_v2.main()

            except Exception as error:
                print()
                print(
                    "리포트 생성 오류: "
                    f"{repr(error)}"
                )

            print()
            print(
                "다음 갱신 예정: "
                + (
                    datetime.now()
                    .strftime(
                        "%H:%M:%S"
                    )
                )
                + f" + {args.refresh}초"
            )

            time.sleep(
                args.refresh
            )

    except KeyboardInterrupt:
        print()
        print(
            "실시간 모니터를 종료했습니다."
        )


if __name__ == "__main__":
    main()
