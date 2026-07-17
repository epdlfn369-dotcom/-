import json
import os


BOT_NAME = "BinanceBot v2.4"
SETTINGS_FILE = "settings.json"


DEFAULT_SETTINGS = {
    # ==================================================
    # 가상계좌
    # ==================================================
    "starting_balance": 1_000_000,
    "position_size_percent": 10.0,
    "max_positions": 3,

    # ==================================================
    # 손절·익절 방식
    # ==================================================
    "exit_mode": "FIXED",

    # 고정 손절·익절
    "stop_loss_percent": 1.0,
    "take_profit_percent": 3.0,

    # ATR 손절·익절
    "atr_stop_multiplier": 2.0,
    "atr_take_profit_multiplier": 6.0,
    "minimum_stop_percent": 0.5,
    "maximum_stop_percent": 2.0,
    "minimum_take_profit_percent": 1.5,
    "maximum_take_profit_percent": 6.0,

    # ==================================================
    # 트레일링 스톱
    # ==================================================
    "trailing_stop_enabled": True,
    "trailing_activation_percent": 1.0,
    "trailing_distance_percent": 0.5,

    # ==================================================
    # 최대 보유시간
    # ==================================================
    # 0으로 설정하면 시간 초과 청산 기능 비활성화
    "max_holding_minutes": 240,

    # ==================================================
    # 거래 설정
    # ==================================================
    "scan_interval_seconds": 60,
    "minimum_entry_score": 45,
    "round_trip_fee_percent": 0.10,
    "top_volume_symbols": 20,

    # ==================================================
    # 일일 제한
    # ==================================================
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
    SETTINGS["minimum_take_profit_percent"]
)

MAXIMUM_TAKE_PROFIT_PERCENT = float(
    SETTINGS["maximum_take_profit_percent"]
)


# ==================================================
# 트레일링 스톱
# ==================================================
TRAILING_STOP_ENABLED = bool(
    SETTINGS["trailing_stop_enabled"]
)

TRAILING_ACTIVATION_PERCENT = float(
    SETTINGS["trailing_activation_percent"]
)

TRAILING_DISTANCE_PERCENT = float(
    SETTINGS["trailing_distance_percent"]
)


# ==================================================
# 최대 보유시간
# ==================================================
MAX_HOLDING_MINUTES = max(
    0,
    int(SETTINGS["max_holding_minutes"]),
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
    print("=" * 70)
    print("BinanceBot 설정")
    print("=" * 70)

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

    print()
    print(
        "트레일링 스톱: "
        + (
            "활성화"
            if TRAILING_STOP_ENABLED
            else "비활성화"
        )
    )

    if TRAILING_STOP_ENABLED:
        print(
            f"트레일링 시작 수익률: "
            f"+{TRAILING_ACTIVATION_PERCENT}%"
        )
        print(
            f"최고·최저가 추적 거리: "
            f"{TRAILING_DISTANCE_PERCENT}%"
        )

    print()

    if MAX_HOLDING_MINUTES > 0:
        print(
            f"최대 보유시간: "
            f"{MAX_HOLDING_MINUTES}분"
        )
    else:
        print(
            "최대 보유시간 청산: 비활성화"
        )

    print()
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
    print("=" * 70)


if __name__ == "__main__":
    print_loaded_settings()