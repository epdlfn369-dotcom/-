import json
import os


BOT_NAME = "BinanceBot v2.3"
SETTINGS_FILE = "settings.json"


DEFAULT_SETTINGS = {
    # 가상계좌
    "starting_balance": 1_000_000,
    "position_size_percent": 10.0,
    "max_positions": 3,

    # 손절·익절 방식
    # FIXED 또는 ATR
    "exit_mode": "FIXED",

    # 고정 손절·익절
    "stop_loss_percent": 1.0,
    "take_profit_percent": 3.0,

    # ATR 손절·익절
    "atr_stop_multiplier": 2.0,
    "atr_take_profit_multiplier": 6.0,

    # ATR 방식에서 허용할 최소·최대 폭
    "minimum_stop_percent": 0.5,
    "maximum_stop_percent": 2.0,
    "minimum_take_profit_percent": 1.5,
    "maximum_take_profit_percent": 6.0,

    # 거래 설정
    "scan_interval_seconds": 60,
    "minimum_entry_score": 45,
    "round_trip_fee_percent": 0.10,
    "top_volume_symbols": 20,

    # 일일 제한
    "daily_stop_loss_percent": 5.0,
    "daily_take_profit_percent": 10.0,
}


def load_settings():
    settings = DEFAULT_SETTINGS.copy()

    if not os.path.exists(SETTINGS_FILE):
        return settings

    try:
        with open(
            SETTINGS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            saved = json.load(file)

        if isinstance(saved, dict):
            settings.update(saved)

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
    ) as error:
        print(
            f"settings.json 불러오기 실패: {error}"
        )
        print("기본 설정으로 실행합니다.")

    return settings


SETTINGS = load_settings()


# ==================================================
# 가상계좌
# ==================================================

STARTING_BALANCE = float(
    SETTINGS["starting_balance"]
)

POSITION_SIZE_PERCENT = float(
    SETTINGS["position_size_percent"]
)

MAX_POSITIONS = int(
    SETTINGS["max_positions"]
)


# ==================================================
# 손절·익절
# ==================================================

EXIT_MODE = str(
    SETTINGS["exit_mode"]
).upper()

if EXIT_MODE not in {
    "FIXED",
    "ATR",
}:
    EXIT_MODE = "FIXED"


STOP_LOSS_PERCENT = float(
    SETTINGS["stop_loss_percent"]
)

TAKE_PROFIT_PERCENT = float(
    SETTINGS["take_profit_percent"]
)


ATR_STOP_MULTIPLIER = float(
    SETTINGS["atr_stop_multiplier"]
)

ATR_TAKE_PROFIT_MULTIPLIER = float(
    SETTINGS["atr_take_profit_multiplier"]
)


MINIMUM_STOP_PERCENT = float(
    SETTINGS["minimum_stop_percent"]
)

MAXIMUM_STOP_PERCENT = float(
    SETTINGS["maximum_stop_percent"]
)

MINIMUM_TAKE_PROFIT_PERCENT = float(
    SETTINGS[
        "minimum_take_profit_percent"
    ]
)

MAXIMUM_TAKE_PROFIT_PERCENT = float(
    SETTINGS[
        "maximum_take_profit_percent"
    ]
)


# ==================================================
# 거래 설정
# ==================================================

SCAN_INTERVAL_SECONDS = int(
    SETTINGS["scan_interval_seconds"]
)

MINIMUM_ENTRY_SCORE = int(
    SETTINGS["minimum_entry_score"]
)

ROUND_TRIP_FEE_PERCENT = float(
    SETTINGS["round_trip_fee_percent"]
)

TOP_VOLUME_SYMBOLS = int(
    SETTINGS["top_volume_symbols"]
)


# ==================================================
# 일일 제한
# ==================================================

DAILY_STOP_LOSS_PERCENT = float(
    SETTINGS["daily_stop_loss_percent"]
)

DAILY_TAKE_PROFIT_PERCENT = float(
    SETTINGS["daily_take_profit_percent"]
)


# ==================================================
# 안전장치
# ==================================================

PAPER_TRADING = True


def print_loaded_settings():
    print()
    print("=" * 65)
    print("BinanceBot 설정")
    print("=" * 65)

    print(
        f"청산 방식: {EXIT_MODE}"
    )

    if EXIT_MODE == "FIXED":
        print(
            f"고정 손절: "
            f"-{STOP_LOSS_PERCENT}%"
        )
        print(
            f"고정 익절: "
            f"+{TAKE_PROFIT_PERCENT}%"
        )

    else:
        print(
            f"ATR 손절 배수: "
            f"{ATR_STOP_MULTIPLIER}"
        )
        print(
            f"ATR 익절 배수: "
            f"{ATR_TAKE_PROFIT_MULTIPLIER}"
        )
        print(
            f"손절 허용 범위: "
            f"{MINIMUM_STOP_PERCENT}%"
            f" ~ {MAXIMUM_STOP_PERCENT}%"
        )
        print(
            f"익절 허용 범위: "
            f"{MINIMUM_TAKE_PROFIT_PERCENT}%"
            f" ~ {MAXIMUM_TAKE_PROFIT_PERCENT}%"
        )

    print(
        f"최대 포지션: "
        f"{MAX_POSITIONS}개"
    )

    print(
        f"포지션당 투입: "
        f"{POSITION_SIZE_PERCENT}%"
    )

    print(
        f"최소 진입 점수: "
        f"{MINIMUM_ENTRY_SCORE}점"
    )

    print(
        f"스캔 주기: "
        f"{SCAN_INTERVAL_SECONDS}초"
    )

    print("=" * 65)


if __name__ == "__main__":
    print_loaded_settings()