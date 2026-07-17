import json
import os
import time
from datetime import datetime


COOLDOWN_FILE = "cooldown.json"

# 청산 후 같은 코인 재진입 대기시간
REENTRY_COOLDOWN_SECONDS = 30 * 60


def load_cooldowns():
    if not os.path.exists(COOLDOWN_FILE):
        return {}

    try:
        with open(
            COOLDOWN_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return {}

        return {
            symbol: float(exit_time)
            for symbol, exit_time in data.items()
        }

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        return {}


def save_cooldowns(cooldowns):
    temporary_file = COOLDOWN_FILE + ".tmp"

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            cooldowns,
            file,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(
        temporary_file,
        COOLDOWN_FILE,
    )


def clean_expired_cooldowns():
    cooldowns = load_cooldowns()
    current_time = time.time()

    active_cooldowns = {
        symbol: exit_time
        for symbol, exit_time in cooldowns.items()
        if (
            current_time - exit_time
            < REENTRY_COOLDOWN_SECONDS
        )
    }

    if active_cooldowns != cooldowns:
        save_cooldowns(active_cooldowns)

    return active_cooldowns


def start_cooldown(symbol):
    cooldowns = clean_expired_cooldowns()

    cooldowns[symbol] = time.time()

    save_cooldowns(cooldowns)


def get_remaining_seconds(symbol):
    cooldowns = clean_expired_cooldowns()

    if symbol not in cooldowns:
        return 0

    elapsed_seconds = (
        time.time()
        - cooldowns[symbol]
    )

    remaining_seconds = (
        REENTRY_COOLDOWN_SECONDS
        - elapsed_seconds
    )

    return max(
        0,
        int(remaining_seconds),
    )


def is_in_cooldown(symbol):
    return get_remaining_seconds(symbol) > 0


def format_remaining_time(seconds):
    minutes = seconds // 60
    remaining_seconds = seconds % 60

    if minutes > 0:
        return (
            f"{minutes}분 "
            f"{remaining_seconds}초"
        )

    return f"{remaining_seconds}초"


def print_cooldown_status():
    cooldowns = clean_expired_cooldowns()

    print()
    print("=" * 60)
    print("재진입 대기 종목")
    print("=" * 60)

    if not cooldowns:
        print("현재 재진입 대기 종목이 없습니다.")
        return

    for symbol in cooldowns:
        remaining = get_remaining_seconds(
            symbol
        )

        print(
            f"{symbol:<15} "
            f"{format_remaining_time(remaining)} 남음"
        )


if __name__ == "__main__":
    print_cooldown_status()