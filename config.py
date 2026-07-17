import json
import os


BOT_NAME = "BinanceBot v2.2"
SETTINGS_FILE = "settings.json"


DEFAULT_SETTINGS = {
    "stop_loss_percent": 1.0,
    "take_profit_percent": 3.0,
    "max_positions": 3,
    "position_size_percent": 10.0,
    "scan_interval_seconds": 60,
    "minimum_entry_score": 45,
    "round_trip_fee_percent": 0.10,
    "top_volume_symbols": 20,
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
            saved_settings = json.load(file)

        if isinstance(saved_settings, dict):
            settings.update(saved_settings)

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
# 가상 계좌
# ==================================================

STARTING_BALANCE = 1_000_000

POSITION_SIZE_PERCENT = float(
    SETTINGS["position_size_percent"]
)

MAX_POSITIONS = int(
    SETTINGS["max_positions"]
)


# ==================================================
# 손절·익절·수수료
# ==================================================

STOP_LOSS_PERCENT = float(
    SETTINGS["stop_loss_percent"]
)

TAKE_PROFIT_PERCENT = float(
    SETTINGS["take_profit_percent"]
)

ROUND_TRIP_FEE_PERCENT = float(
    SETTINGS["round_trip_fee_percent"]
)


# ==================================================
# 시장 검색
# ==================================================

SCAN_INTERVAL_SECONDS = int(
    SETTINGS["scan_interval_seconds"]
)

MINIMUM_ENTRY_SCORE = int(
    SETTINGS["minimum_entry_score"]
)

TOP_VOLUME_SYMBOLS = int(
    SETTINGS.get(
        "top_volume_symbols",
        20,
    )
)


# ==================================================
# 일일 제한
# ==================================================

DAILY_STOP_LOSS_PERCENT = 5.0
DAILY_TAKE_PROFIT_PERCENT = 10.0


# ==================================================
# 안전장치
# ==================================================

PAPER_TRADING = True


def print_loaded_settings():
    print()
    print("=" * 60)
    print("웹 설정 불러오기 완료")
    print("=" * 60)

    print(
        f"손절: -{STOP_LOSS_PERCENT}%"
    )

    print(
        f"익절: +{TAKE_PROFIT_PERCENT}%"
    )

    print(
        f"최대 포지션: {MAX_POSITIONS}개"
    )

    print(
        f"포지션 투입 비율: "
        f"{POSITION_SIZE_PERCENT}%"
    )

    print(
        f"최소 진입 점수: "
        f"{MINIMUM_ENTRY_SCORE}점"
    )

    print(
        f"시장 스캔 주기: "
        f"{SCAN_INTERVAL_SECONDS}초"
    )

    print(
        f"왕복 수수료 가정: "
        f"{ROUND_TRIP_FEE_PERCENT}%"
    )

    print("=" * 60)


if __name__ == "__main__":
    print_loaded_settings()