import csv
import os
from datetime import datetime


TRADE_LOG_FILE = "trade_log.csv"


def save_trade(
    symbol,
    side,
    entry_price,
    exit_price,
    investment,
    profit_percent,
    profit_amount,
    reason,
    opened_at,
):
    file_exists = os.path.exists(TRADE_LOG_FILE)

    closed_at = datetime.now()

    if isinstance(opened_at, datetime):
        opened_at_text = opened_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    else:
        opened_at_text = str(opened_at)

    holding_seconds = 0

    if isinstance(opened_at, datetime):
        holding_seconds = int(
            (closed_at - opened_at).total_seconds()
        )

    result = "WIN" if profit_amount > 0 else "LOSS"

    if profit_amount == 0:
        result = "DRAW"

    with open(
        TRADE_LOG_FILE,
        "a",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(
                [
                    "진입시간",
                    "청산시간",
                    "종목",
                    "방향",
                    "진입가",
                    "청산가",
                    "투입금",
                    "수익률",
                    "손익",
                    "결과",
                    "보유초",
                    "청산이유",
                ]
            )

        writer.writerow(
            [
                opened_at_text,
                closed_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                symbol,
                side,
                f"{entry_price:.8f}",
                f"{exit_price:.8f}",
                f"{investment:.2f}",
                f"{profit_percent:.4f}",
                f"{profit_amount:.2f}",
                result,
                holding_seconds,
                reason,
            ]
        )

    print(
        f"거래 기록 저장 완료: {TRADE_LOG_FILE}"
    )