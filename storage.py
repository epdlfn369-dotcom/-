import json
import os
from datetime import datetime


STATE_FILE = "state.json"


def save_state(balance, positions):
    data = {
        "balance": balance,
        "positions": {},
        "saved_at": datetime.now().isoformat(),
    }

    for symbol, position in positions.items():
        copied_position = position.copy()

        opened_at = copied_position.get("opened_at")

        if isinstance(opened_at, datetime):
            copied_position["opened_at"] = opened_at.isoformat()

        data["positions"][symbol] = copied_position

    temporary_file = STATE_FILE + ".tmp"

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(temporary_file, STATE_FILE)


def load_state(default_balance):
    if not os.path.exists(STATE_FILE):
        return float(default_balance), {}

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        balance = float(
            data.get("balance", default_balance)
        )

        positions = data.get("positions", {})

        for position in positions.values():
            opened_at = position.get("opened_at")

            if isinstance(opened_at, str):
                position["opened_at"] = datetime.fromisoformat(
                    opened_at
                )

        return balance, positions

    except Exception as error:
        print(f"저장 파일 불러오기 실패: {error}")
        print("새 가상계좌로 시작합니다.")

        return float(default_balance), {}