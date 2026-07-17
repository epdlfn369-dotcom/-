import config
print("불러온 config 위치:", config.__file__)
import time

import config
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


def main():
    print("=" * 60)
    print(config.BOT_NAME)
    print("=" * 60)

    print("현재 모드: 가상매매")
    print(f"저장된 가상잔고: {balance:,.0f}원")
    print(f"복구된 포지션: {len(positions)}개")
    print(f"최대 포지션: {config.MAX_POSITIONS}개")
    print(f"손절: -{config.STOP_LOSS_PERCENT}%")
    print(f"익절: +{config.TAKE_PROFIT_PERCENT}%")
    print(
        f"왕복 수수료 가정: "
        f"{config.ROUND_TRIP_FEE_PERCENT}%"
    )
    print(
        f"일일 손실 제한: "
        f"-{config.DAILY_STOP_LOSS_PERCENT}%"
    )
    print(
        f"일일 수익 제한: "
        f"+{config.DAILY_TAKE_PROFIT_PERCENT}%"
    )
    print("종료: Ctrl + C")

    print_report()
    print_daily_risk_status()

    while True:
        try:
            # 기존 포지션은 거래 중단 상태여도 계속 감시
            monitor_positions()

            trading_status = get_trading_status()

            if trading_status["can_trade"]:
                print()
                print("시장 스캔을 시작합니다.")

                market_results = scan_market()

                candidates = rank_candidates(
                    market_results
                )

                if candidates:
                    print()
                    print("가상 진입 후보")

                    for candidate in candidates[:5]:
                        print(
                            f"{candidate['symbol']:<12} "
                            f"{candidate['side']:<5} "
                            f"{candidate['score']}점"
                        )

                    open_top_candidates(candidates)

                else:
                    print(
                        "현재 진입 조건을 만족하는 "
                        "후보가 없습니다."
                    )

            else:
                print()
                print("⛔ 신규 시장 진입 중단")
                print(trading_status["reason"])
                print(
                    f"오늘 실현손익: "
                    f"{trading_status['profit_amount']:+,.0f}원"
                )

            print_account_status()
            print_daily_risk_status()

            checks = max(
                1,
                config.SCAN_INTERVAL_SECONDS // 5,
            )

            for _ in range(checks):
                monitor_positions()
                time.sleep(5)

        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            print_report()
            print_daily_risk_status()
            break

        except Exception as error:
            print(f"오류 발생: {repr(error)}")
            time.sleep(10)


if __name__ == "__main__":
    main()