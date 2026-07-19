import time
from datetime import datetime, timezone

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator, EMAIndicator
from ta.volatility import AverageTrueRange

import config
from binance_api import request_json


MOMENTUM_MINUTES = 5
REQUEST_DELAY_SECONDS = 0.08

MIN_LISTING_DAYS = 30
MAX_ABSOLUTE_24H_CHANGE = 20.0


EXCLUDED_BASE_ASSETS = {
    "USDC",
    "FDUSD",
    "TUSD",
    "USDP",
    "DAI",
    "USDS",
    "EUR",
    "TRY",
    "BRL",
    "GBP",
    "AUD",
    "JPY",
}


# ==================================================
# 종목 정보
# ==================================================

def get_symbol_information():
    data = request_json(
        "/fapi/v1/exchangeInfo"
    )

    current_time_ms = int(
        datetime.now(
            timezone.utc
        ).timestamp() * 1000
    )

    minimum_age_ms = (
        MIN_LISTING_DAYS
        * 24
        * 60
        * 60
        * 1000
    )

    symbols = {}

    for item in data.get(
        "symbols",
        [],
    ):
        if item.get("status") != "TRADING":
            continue

        if item.get("quoteAsset") != "USDT":
            continue

        if item.get("contractType") != "PERPETUAL":
            continue

        symbol = item.get("symbol")

        base_asset = item.get(
            "baseAsset",
            "",
        )

        if not symbol:
            continue

        if base_asset in EXCLUDED_BASE_ASSETS:
            continue

        try:
            onboard_date = int(
                item.get(
                    "onboardDate",
                    0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            onboard_date = 0

        if onboard_date > 0:
            listing_age = (
                current_time_ms
                - onboard_date
            )

            if listing_age < minimum_age_ms:
                continue

        symbols[symbol] = {
            "symbol": symbol,
            "base_asset": base_asset,
            "onboard_date": onboard_date,
        }

    return symbols


# ==================================================
# 거래대금 상위 종목
# ==================================================

def get_top_volume_symbols():
    valid_symbols = (
        get_symbol_information()
    )

    tickers = request_json(
        "/fapi/v1/ticker/24hr"
    )

    ranked = []

    excluded_extreme = 0
    excluded_low_volume = 0

    for ticker in tickers:
        symbol = ticker.get("symbol")

        if symbol not in valid_symbols:
            continue

        try:
            quote_volume = float(
                ticker.get(
                    "quoteVolume",
                    0,
                )
            )

            price_change = float(
                ticker.get(
                    "priceChangePercent",
                    0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if (
            abs(price_change)
            >= MAX_ABSOLUTE_24H_CHANGE
        ):
            excluded_extreme += 1
            continue

        if (
            config.VOLUME_FILTER_ENABLED
            and quote_volume
            < config.MINIMUM_24H_QUOTE_VOLUME
        ):
            excluded_low_volume += 1
            continue

        ranked.append(
            {
                "symbol": symbol,
                "quote_volume": quote_volume,
                "price_change_24h": price_change,
            }
        )

    ranked.sort(
        key=lambda item: item[
            "quote_volume"
        ],
        reverse=True,
    )

    selected = ranked[
        :config.TOP_VOLUME_SYMBOLS
    ]

    print(
        f"안전 필터 통과: "
        f"{len(ranked)}개"
    )

    print(
        f"급등락 제외: "
        f"{excluded_extreme}개"
    )

    if config.VOLUME_FILTER_ENABLED:
        print(
            f"거래대금 부족 제외: "
            f"{excluded_low_volume}개"
        )

        print(
            "최소 24시간 거래대금: "
            f"{config.MINIMUM_24H_QUOTE_VOLUME:,.0f} "
            "USDT"
        )

    print(
        f"분석 대상: "
        f"{len(selected)}개"
    )

    return selected


# ==================================================
# 캔들
# ==================================================

def get_closed_candles(
    symbol,
    limit=120,
    interval="1m",
):
    candles = request_json(
        "/fapi/v1/klines",
        {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        },
    )

    # 진행 중인 마지막 봉 제외
    return candles[:-1]


# ==================================================
# 계산
# ==================================================

def calculate_percent_change(
    old_price,
    new_price,
):
    if old_price == 0:
        return 0.0

    return (
        (new_price - old_price)
        / old_price
        * 100
    )


def calculate_volume_ratio(
    volumes,
):
    if len(volumes) < 6:
        return 0.0

    latest_volume = float(
        volumes[-1]
    )

    previous_volumes = volumes[
        -6:-1
    ]

    average_volume = (
        sum(previous_volumes)
        / len(previous_volumes)
    )

    if average_volume <= 0:
        return 0.0

    return (
        latest_volume
        / average_volume
    )


def calculate_indicators(
    highs,
    lows,
    closes,
):
    dataframe = pd.DataFrame(
        {
            "high": highs,
            "low": lows,
            "close": closes,
        }
    )

    dataframe["ema20"] = EMAIndicator(
        close=dataframe["close"],
        window=20,
    ).ema_indicator()

    dataframe["ema50"] = EMAIndicator(
        close=dataframe["close"],
        window=50,
    ).ema_indicator()

    dataframe["rsi"] = RSIIndicator(
        close=dataframe["close"],
        window=14,
    ).rsi()

    dataframe["atr"] = AverageTrueRange(
        high=dataframe["high"],
        low=dataframe["low"],
        close=dataframe["close"],
        window=14,
    ).average_true_range()

    dataframe["adx"] = ADXIndicator(
        high=dataframe["high"],
        low=dataframe["low"],
        close=dataframe["close"],
        window=14,
    ).adx()

    latest = dataframe.iloc[-1]

    close_price = float(
        latest["close"]
    )

    atr_value = float(
        latest["atr"]
    )

    if close_price <= 0:
        atr_percent = 0.0
    else:
        atr_percent = (
            atr_value
            / close_price
            * 100
        )

    return {
        "ema20": float(
            latest["ema20"]
        ),
        "ema50": float(
            latest["ema50"]
        ),
        "rsi": float(
            latest["rsi"]
        ),
        "atr": atr_value,
        "atr_percent": atr_percent,
        "adx": float(
            latest["adx"]
        ),
    }



def calculate_higher_timeframe_indicators(
    symbol,
):
    candles = get_closed_candles(
        symbol=symbol,
        limit=120,
        interval=(
            config.HIGHER_TIMEFRAME_INTERVAL
        ),
    )

    if len(candles) < 60:
        return None

    highs = [
        float(candle[2])
        for candle in candles
    ]

    lows = [
        float(candle[3])
        for candle in candles
    ]

    closes = [
        float(candle[4])
        for candle in candles
    ]

    indicators = calculate_indicators(
        highs,
        lows,
        closes,
    )

    if (
        indicators["ema20"]
        > indicators["ema50"]
    ):
        side = "LONG"
    elif (
        indicators["ema20"]
        < indicators["ema50"]
    ):
        side = "SHORT"
    else:
        side = "NONE"

    return {
        "side": side,
        "ema20": indicators["ema20"],
        "ema50": indicators["ema50"],
        "adx": indicators["adx"],
    }


# ==================================================
# 개별 종목 분석
# ==================================================

def analyze_symbol(symbol):
    candles = get_closed_candles(
        symbol=symbol,
        limit=120,
    )

    if len(candles) < 60:
        return None

    highs = [
        float(candle[2])
        for candle in candles
    ]

    lows = [
        float(candle[3])
        for candle in candles
    ]

    closes = [
        float(candle[4])
        for candle in candles
    ]

    volumes = [
        float(candle[5])
        for candle in candles
    ]

    current_price = closes[-1]

    old_price = closes[
        -(MOMENTUM_MINUTES + 1)
    ]

    move_5m = (
        calculate_percent_change(
            old_price,
            current_price,
        )
    )

    volume_ratio = (
        calculate_volume_ratio(
            volumes
        )
    )

    indicators = (
        calculate_indicators(
            highs,
            lows,
            closes,
        )
    )

    higher_timeframe = (
        calculate_higher_timeframe_indicators(
            symbol
        )
    )

    if higher_timeframe is None:
        return None

    return {
        "symbol": symbol,
        "current_price": current_price,
        "move_5m": move_5m,
        "volume_ratio": volume_ratio,
        "ema20": indicators["ema20"],
        "ema50": indicators["ema50"],
        "rsi": indicators["rsi"],
        "atr": indicators["atr"],
        "atr_percent": (
            indicators["atr_percent"]
        ),
        "adx": indicators["adx"],
        "higher_timeframe_side": (
            higher_timeframe["side"]
        ),
        "higher_timeframe_adx": (
            higher_timeframe["adx"]
        ),
        "higher_timeframe_ema20": (
            higher_timeframe["ema20"]
        ),
        "higher_timeframe_ema50": (
            higher_timeframe["ema50"]
        ),
    }


# ==================================================
# 거래량 필터
# ==================================================

def passes_recent_volume_filter(
    result,
):
    if not config.VOLUME_FILTER_ENABLED:
        return True

    volume_ratio = float(
        result.get(
            "volume_ratio",
            0,
        )
    )

    return (
        volume_ratio
        >= config.MINIMUM_VOLUME_RATIO
    )


def passes_adx_filter(
    result,
):
    if not config.ADX_FILTER_ENABLED:
        return True

    adx = float(
        result.get(
            "adx",
            0,
        )
    )

    return (
        adx
        >= config.MINIMUM_ADX
    )



def passes_higher_timeframe_filter(
    result,
):
    if not config.HIGHER_TIMEFRAME_FILTER_ENABLED:
        return True

    higher_side = result.get(
        "higher_timeframe_side",
        "NONE",
    )

    higher_adx = float(
        result.get(
            "higher_timeframe_adx",
            0,
        )
    )

    ema20 = float(
        result.get(
            "ema20",
            0,
        )
    )

    ema50 = float(
        result.get(
            "ema50",
            0,
        )
    )

    if ema20 > ema50:
        current_side = "LONG"
    elif ema20 < ema50:
        current_side = "SHORT"
    else:
        current_side = "NONE"

    return (
        current_side != "NONE"
        and current_side == higher_side
        and higher_adx
        >= config.HIGHER_TIMEFRAME_MINIMUM_ADX
    )


# ==================================================
# 시장 스캔
# ==================================================

def scan_market():
    print()
    print("=" * 80)
    print("EMA + RSI + ATR 시장 스캔")
    print("=" * 80)

    print(
        f"청산 방식: "
        f"{config.EXIT_MODE}"
    )

    print(
        f"최소 진입 점수: "
        f"{config.MINIMUM_ENTRY_SCORE}"
    )

    print(
        "거래량 필터: "
        + (
            "활성화"
            if config.VOLUME_FILTER_ENABLED
            else "비활성화"
        )
    )

    if config.VOLUME_FILTER_ENABLED:
        print(
            "최근 거래량 최소 비율: "
            f"{config.MINIMUM_VOLUME_RATIO:.2f}배"
        )

    print(
        "ADX 필터: "
        + (
            "활성화"
            if config.ADX_FILTER_ENABLED
            else "비활성화"
        )
    )

    if config.ADX_FILTER_ENABLED:
        print(
            f"최소 ADX: "
            f"{config.MINIMUM_ADX:.1f}"
        )

    print(
        "1시간 추세 필터: "
        + (
            "활성화"
            if config.HIGHER_TIMEFRAME_FILTER_ENABLED
            else "비활성화"
        )
    )

    if config.HIGHER_TIMEFRAME_FILTER_ENABLED:
        print(
            f"1시간 최소 ADX: "
            f"{config.HIGHER_TIMEFRAME_MINIMUM_ADX:.1f}"
        )

    top_symbols = (
        get_top_volume_symbols()
    )

    results = []

    excluded_recent_volume = 0
    excluded_adx = 0
    excluded_higher_timeframe = 0

    print()

    for index, item in enumerate(
        top_symbols,
        start=1,
    ):
        symbol = item["symbol"]

        try:
            result = analyze_symbol(
                symbol
            )

            if result is None:
                continue

            result[
                "price_change_24h"
            ] = item[
                "price_change_24h"
            ]

            result[
                "quote_volume"
            ] = item[
                "quote_volume"
            ]

            if not passes_recent_volume_filter(
                result
            ):
                excluded_recent_volume += 1

                print(
                    f"{index:>2}/"
                    f"{len(top_symbols)} "
                    f"{symbol:<14} "
                    f"거래량 부족 제외 | "
                    f"{result['volume_ratio']:.2f}배 "
                    f"< "
                    f"{config.MINIMUM_VOLUME_RATIO:.2f}배",
                    flush=True,
                )

                continue

            if not passes_adx_filter(
                result
            ):
                excluded_adx += 1

                print(
                    f"{index:>2}/"
                    f"{len(top_symbols)} "
                    f"{symbol:<14} "
                    f"ADX 부족 제외 | "
                    f"{result['adx']:.1f} "
                    f"< "
                    f"{config.MINIMUM_ADX:.1f}",
                    flush=True,
                )

                continue

            if not passes_higher_timeframe_filter(
                result
            ):
                excluded_higher_timeframe += 1

                print(
                    f"{index:>2}/"
                    f"{len(top_symbols)} "
                    f"{symbol:<14} "
                    f"1시간 추세 제외 | "
                    f"방향 "
                    f"{result['higher_timeframe_side']} | "
                    f"ADX "
                    f"{result['higher_timeframe_adx']:.1f}",
                    flush=True,
                )

                continue

            results.append(result)

            trend = (
                "상승"
                if result["ema20"]
                > result["ema50"]
                else "하락"
            )

            print(
                f"{index:>2}/"
                f"{len(top_symbols)} "
                f"{symbol:<14} "
                f"{trend} | "
                f"5분 "
                f"{result['move_5m']:+.3f}% | "
                f"거래량 "
                f"{result['volume_ratio']:.2f}배 | "
                f"RSI "
                f"{result['rsi']:.1f} | "
                f"ATR "
                f"{result['atr_percent']:.3f}% | "
                f"ADX "
                f"{result['adx']:.1f} | "
                f"1H "
                f"{result['higher_timeframe_side']} "
                f"ADX "
                f"{result['higher_timeframe_adx']:.1f}",
                flush=True,
            )

        except Exception as error:
            print(
                f"{symbol} 분석 실패: "
                f"{repr(error)}",
                flush=True,
            )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    if config.VOLUME_FILTER_ENABLED:
        print()
        print(
            "최근 거래량 부족 제외: "
            f"{excluded_recent_volume}개"
        )

        print(
            "최종 전략 분석 대상: "
            f"{len(results)}개"
        )

    if config.ADX_FILTER_ENABLED:
        print(
            "ADX 부족 제외: "
            f"{excluded_adx}개"
        )

    if config.HIGHER_TIMEFRAME_FILTER_ENABLED:
        print(
            "1시간 추세·ADX 제외: "
            f"{excluded_higher_timeframe}개"
        )

    return results


def print_rankings(results):
    rising = sorted(
        results,
        key=lambda item: item[
            "move_5m"
        ],
        reverse=True,
    )

    falling = sorted(
        results,
        key=lambda item: item[
            "move_5m"
        ],
    )

    print()
    print("최근 5분 상승률 상위")
    print("-" * 85)

    for item in rising[:5]:
        print(
            f"{item['symbol']:<14} "
            f"{item['move_5m']:+.3f}% | "
            f"거래량 "
            f"{item['volume_ratio']:.2f}배 | "
            f"RSI {item['rsi']:.1f} | "
            f"ATR "
            f"{item['atr_percent']:.3f}% | "
            f"ADX {item['adx']:.1f}"
        )

    print()
    print("최근 5분 하락률 상위")
    print("-" * 85)

    for item in falling[:5]:
        print(
            f"{item['symbol']:<14} "
            f"{item['move_5m']:+.3f}% | "
            f"거래량 "
            f"{item['volume_ratio']:.2f}배 | "
            f"RSI {item['rsi']:.1f} | "
            f"ATR "
            f"{item['atr_percent']:.3f}% | "
            f"ADX {item['adx']:.1f}"
        )


if __name__ == "__main__":
    from engine.strategy import (
        print_candidates,
        rank_candidates,
    )

    market_results = scan_market()

    print_rankings(
        market_results
    )

    candidates = rank_candidates(
        market_results
    )

    print_candidates(
        candidates
    )