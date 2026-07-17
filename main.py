import time

import config
from bot_control import (
    is_trading_enabled,
    load_control,
)
from bot_status import (
    mark_error,
    mark_heartbeat,
    mark_scan_completed,
    mark_scan_started,
    mark_started,
    mark_stopped,
)
from position import (
    balance,
    positions,
    monitor_positions,
    open_top_candidates,
    print_account_status,
)
from report import print_report
from risk import (
    get_trading_status,
    print_daily_risk_status,
)
from scanner import scan_market
from strategy import rank_candidates


POSITION_CHECK_SECONDS = 5


def print_startup_information():
    print("=" * 70)
    print(config.BOT_NAME)
    print("=" * 70)

    print("현재 모드: 가상매매")

    print(
        f"저장된 가상잔고: "
        f"{balance:,.0f}원"
    )

    print(
        f"복구된 포지션: "
        f"{len(positions)}개"
    )

    print(
        f"최대 포지션: "
        f"{config.MAX_POSITIONS}개"
    )

    print(
        f"포지션당 투입 비율: "
        f"{config.POSITION_SIZE_PERCENT}%"
    )

    print(
        f"최소 진입 점수: "
        f"{config.MINIMUM_ENTRY_SCORE}점"
    )

    print(
        f"손절: "
        f"-{config.STOP_LOSS_PERCENT}%"
    )

    print(
        f"익절: "
        f"+{config.TAKE_PROFIT_PERCENT}%"
    )

    print(
        f"스캔 주기: "
        f"{config.SCAN_INTERVAL_SECONDS}초"
    )

    control = load_control()

    print(
        "신규 진입 상태: "
        + (
            "활성화"
            if control["trading_enabled"]
            else "일시정지"
        )
    )

    print("종료: Ctrl + C")


def wait_until_next_scan():
    checks = max(
        1,
        config.SCAN_INTERVAL_SECONDS
        // POSITION_CHECK_SECONDS,
    )

    for check_number in range(checks):
        monitor_positions()

        mark_heartbeat(
            message=(
                "포지션 감시 중 "
                f"({check_number + 1}/{checks})"
            )
        )

        time.sleep(
            POSITION_CHECK_SECONDS
        )


def run_market_scan():
    if not is_trading_enabled():
        control = load_control()

        print()
        print(
            "⏸ 신규 포지션 진입이 "
            "일시정지 상태입니다."
        )

        reason = control.get(
            "reason",
            "",
        )

        if reason:
            print(
                f"정지 사유: {reason}"
            )

        print(
            "기존 포지션의 손절·익절 감시는 "
            "계속 진행합니다."
        )

        mark_heartbeat(
            "사용자 설정으로 신규 진입 일시정지"
        )

        return

    trading_status = (
        get_trading_status()
    )

    if not trading_status["can_trade"]:
        print()
        print("⛔ 신규 시장 진입 중단")
        print(
            trading_status["reason"]
        )

        print(
            f"오늘 실현손익: "
            f"{trading_status['profit_amount']:+,.0f}원"
        )

        mark_heartbeat(
            "일일 제한으로 신규 진입 중단"
        )

        return

    print()
    print("시장 스캔을 시작합니다.")

    mark_scan_started()

    market_results = scan_market()

    candidates = rank_candidates(
        market_results
    )

    if candidates:
        print()
        print("가상 진입 후보")

        for candidate in candidates[:5]:
            print(
                f"{candidate['symbol']:<14} "
                f"{candidate['side']:<5} "
                f"{candidate['score']}점"
            )

        open_top_candidates(
            candidates
        )

    else:
        print(
            "현재 진입 조건을 만족하는 "
            "후보가 없습니다."
        )

    mark_scan_completed()


def main():
    mark_started()

    try:
        print_startup_information()

        print_report()
        print_daily_risk_status()

        while True:
            try:
                mark_heartbeat(
                    "포지션 확인 시작"
                )

                monitor_positions()

                run_market_scan()

                print_account_status()
                print_daily_risk_status()

                wait_until_next_scan()

            except KeyboardInterrupt:
                raise

            except Exception as error:
                print(
                    f"오류 발생: "
                    f"{repr(error)}"
                )

                mark_error(error)

                time.sleep(10)

    except KeyboardInterrupt:
        print()
        print("프로그램을 종료합니다.")

        mark_stopped(
            "사용자가 Ctrl + C로 종료"
        )

        print_report()
        print_daily_risk_status()

    except Exception as error:
        mark_error(error)

        mark_stopped(
            "치명적 오류로 봇 종료"
        )

        raise

    finally:
        mark_stopped(
            "프로그램 실행 종료"
        )


if __name__ == "__main__":
    main()