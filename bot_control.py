import json
import os
from datetime import datetime


CONTROL_FILE = "bot_control.json"


DEFAULT_CONTROL = {
    "trading_enabled": True,
    "updated_at": "",
    "updated_by": "system",
    "reason": "",
}


def now_text():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def load_control():
    control = DEFAULT_CONTROL.copy()

    if not os.path.exists(CONTROL_FILE):
        return control

    try:
        with open(
            CONTROL_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            saved = json.load(file)

        if isinstance(saved, dict):
            control.update(saved)

    except Exception:
        pass

    return control


def save_control(control):
    temporary_file = (
        CONTROL_FILE + ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            control,
            file,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(
        temporary_file,
        CONTROL_FILE,
    )


def enable_trading(
    updated_by="dashboard",
):
    save_control(
        {
            "trading_enabled": True,
            "updated_at": now_text(),
            "updated_by": updated_by,
            "reason": "",
        }
    )


def disable_trading(
    reason="사용자가 신규 진입을 중지함",
    updated_by="dashboard",
):
    save_control(
        {
            "trading_enabled": False,
            "updated_at": now_text(),
            "updated_by": updated_by,
            "reason": reason,
        }
    )


def is_trading_enabled():
    control = load_control()

    return bool(
        control.get(
            "trading_enabled",
            True,
        )
    )


if __name__ == "__main__":
    print(
        json.dumps(
            load_control(),
            ensure_ascii=False,
            indent=2,
        )
    )