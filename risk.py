import csv
import os
from datetime import datetime

import config


TRADE_LOG_FILE = "trade_log.csv"


def get_today_realized_profit():
    """
    오늘 청산된 거래들의 실현손익을 합산한다.
    """

    if not os.path.exists(TRADE_LOG_FILE):
        return 0.0

    today_text = datetime.now().strftime("%Y-%m-%d")
    total_profit = 0.0

    try:
        with open(
            TRADE_LOG_FILE,
            "r",
            encoding="utf-8-sig",
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                closed_at = row.get("청산시간", "")
                profit_text = row.get("손익", "0")

                if not closed_at.startswith(today_text):
                    continue

                try:
                    total_profit += float(profit_text)
                except (TypeError, ValueError):
                    continue

    except OSError as error:
        print(f"일일 손익 확인 오류: {error}")
        return 0.0

    return total_profit


def get_today_profit_percent():
    """
    시작 가상잔고 대비 오늘 실현손익 비율.
    """

    profit = get_today_realized_profit()

    if config.STARTING_BALANCE <= 0:
        return 0.0

    return (
        profit
        / config.STARTING_BALANCE
        * 100
    )


def get_trading_status():
    """
    신규 거래 가능 여부와 사유를 반환한다.
    기존 포지션의 손절·익절 감시는 계속한다.
    """

    profit_amount = get_today_realized_profit()
    profit_percent = get_today_profit_percent()

    if profit_percent <= -config.DAILY_STOP_LOSS_PERCENT:
        return {
            "can_trade": False,
            "profit_amount": profit_amount,
            "profit_percent": profit_percent,
            "reason": (
                f"일일 손실 제한 "
                f"-{config.DAILY_STOP_LOSS_PERCENT}% 도달"
            ),
        }

    if profit_percent >= config.DAILY_TAKE_PROFIT_PERCENT:
        return {
            "can_trade": False,
            "profit_amount": profit_amount,
            "profit_percent": profit_percent,
            "reason": (
                f"일일 수익 목표 "
                f"+{config.DAILY_TAKE_PROFIT_PERCENT}% 도달"
            ),
        }

    return {
        "can_trade": True,
        "profit_amount": profit_amount,
        "profit_percent": profit_percent,
        "reason": "신규 거래 가능",
    }


def print_daily_risk_status():
    status = get_trading_status()

    print()
    print("-" * 60)
    print(
        f"오늘 실현손익: "
        f"{status['profit_amount']:+,.0f}원 "
        f"({status['profit_percent']:+.3f}%)"
    )

    if status["can_trade"]:
        print("신규 거래 상태: 가능")
    else:
        print(f"신규 거래 상태: 중단")
        print(f"중단 사유: {status['reason']}")

    print("-" * 60)