import importlib
import json
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

REQUIRED_FILES = [
    PROJECT_ROOT / "main.py",
    PROJECT_ROOT / "config.py",
    PROJECT_ROOT / "settings.json",
    PROJECT_ROOT / "paper_supervisor.py",
    PROJECT_ROOT / "paper_report_v2.py",
    PROJECT_ROOT / "paper_report_watch.py",
    PROJECT_ROOT / "engine" / "scanner.py",
    PROJECT_ROOT / "engine" / "position.py",
    PROJECT_ROOT / "engine" / "strategy.py",
]

REQUIRED_SETTINGS = {
    "strategy_profile": "conservative",
    "minimum_entry_score": 85,
    "max_positions": 1,
    "top_candidate_limit": 1,
    "exit_mode": "FIXED",
    "partial_take_profit_enabled": True,
    "partial_trigger_percent": 1.5,
    "partial_close_ratio": 0.5,
    "move_stop_to_breakeven": True,
    "trailing_stop_enabled": False,
    "adx_filter_enabled": True,
    "minimum_adx": 20.0,
    "higher_timeframe_filter_enabled": True,
    "higher_timeframe_interval": "1h",
    "higher_timeframe_minimum_adx": 30.0,
}

MODULES_TO_IMPORT = [
    "config",
    "engine.strategy",
    "engine.scanner",
    "engine.position",
]


def print_result(
    passed,
    title,
    detail="",
):
    symbol = "PASS" if passed else "FAIL"

    print(
        f"[{symbol}] {title}"
        + (
            f" | {detail}"
            if detail
            else ""
        )
    )


def check_required_files():
    passed = True

    for path in REQUIRED_FILES:
        exists = path.exists()

        print_result(
            exists,
            "필수 파일",
            str(
                path.relative_to(
                    PROJECT_ROOT
                )
            ),
        )

        if not exists:
            passed = False

    return passed


def load_settings():
    path = (
        PROJECT_ROOT
        / "settings.json"
    )

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(
            data,
            dict,
        ):
            raise TypeError(
                "settings.json 최상위가 객체가 아닙니다."
            )

        return data

    except Exception as error:
        print_result(
            False,
            "settings.json 읽기",
            repr(error),
        )

        return None


def values_equal(
    actual,
    expected,
):
    if isinstance(
        expected,
        float,
    ):
        try:
            return (
                abs(
                    float(actual)
                    - expected
                )
                < 1e-9
            )

        except (
            TypeError,
            ValueError,
        ):
            return False

    return actual == expected


def check_settings():
    settings = load_settings()

    if settings is None:
        return False

    passed = True

    for key, expected in (
        REQUIRED_SETTINGS.items()
    ):
        actual = settings.get(
            key,
            "<MISSING>",
        )

        matched = values_equal(
            actual,
            expected,
        )

        print_result(
            matched,
            f"설정 {key}",
            (
                f"현재={actual!r}, "
                f"기대={expected!r}"
            ),
        )

        if not matched:
            passed = False

    return passed


def check_imports():
    passed = True

    for module_name in (
        MODULES_TO_IMPORT
    ):
        try:
            importlib.import_module(
                module_name
            )

            print_result(
                True,
                "모듈 import",
                module_name,
            )

        except Exception as error:
            print_result(
                False,
                "모듈 import",
                (
                    f"{module_name}: "
                    f"{repr(error)}"
                ),
            )

            passed = False

    return passed


def check_disk_space():
    try:
        usage = shutil.disk_usage(
            PROJECT_ROOT
        )

        free_gb = (
            usage.free
            / 1024
            / 1024
            / 1024
        )

        passed = free_gb >= 2.0

        print_result(
            passed,
            "저장공간",
            f"여유 {free_gb:.2f} GB",
        )

        return passed

    except OSError as error:
        print_result(
            False,
            "저장공간 확인",
            repr(error),
        )

        return False


def check_write_permission():
    test_path = (
        PROJECT_ROOT
        / ".healthcheck_write_test"
    )

    try:
        test_path.write_text(
            "ok",
            encoding="utf-8",
        )

        test_path.unlink(
            missing_ok=True
        )

        print_result(
            True,
            "프로젝트 폴더 쓰기 권한",
        )

        return True

    except OSError as error:
        print_result(
            False,
            "프로젝트 폴더 쓰기 권한",
            repr(error),
        )

        return False


def check_runtime_directories():
    passed = True

    for directory_name in (
        "logs",
    ):
        directory = (
            PROJECT_ROOT
            / directory_name
        )

        try:
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            print_result(
                True,
                "실행 폴더",
                directory_name,
            )

        except OSError as error:
            print_result(
                False,
                "실행 폴더",
                (
                    f"{directory_name}: "
                    f"{repr(error)}"
                ),
            )

            passed = False

    return passed


def main():
    print()
    print("=" * 84)
    print(
        "BinanceBot 실행 전 자동 점검"
    )
    print("=" * 84)

    checks = [
        (
            "필수 파일",
            check_required_files,
        ),
        (
            "설정값",
            check_settings,
        ),
        (
            "모듈 import",
            check_imports,
        ),
        (
            "저장공간",
            check_disk_space,
        ),
        (
            "쓰기 권한",
            check_write_permission,
        ),
        (
            "실행 폴더",
            check_runtime_directories,
        ),
    ]

    results = []

    for _, check_function in checks:
        print()

        try:
            results.append(
                bool(
                    check_function()
                )
            )

        except Exception as error:
            print_result(
                False,
                "점검 중 예외",
                repr(error),
            )

            results.append(
                False
            )

    print()
    print("=" * 84)

    if all(results):
        print(
            "점검 통과: supervisor를 실행해도 됩니다."
        )
        print("=" * 84)
        return 0

    print(
        "점검 실패: FAIL 항목을 먼저 수정하세요."
    )
    print("=" * 84)

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
