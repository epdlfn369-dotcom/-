import time

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

import config
from binance_api import (
    get_usdt_perpetual_symbols,
    request_json,
)


MOMENTUM_MINUTES = 5
REQUEST_DELAY_SECONDS = 0.08


def get_top_volume_symbols():
    valid_symbols = set(
        get_usdt_perpetual_symbols()
    )

    tickers = request_json(
        "/fapi/v1/ticker/24hr"
    )

    ranked = []

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

    return ranked[
        :config.TOP_VOLUME_SYMBOLS
    ]


def get_closed_candles(
    symbol,
    limit=100,
):
    candles = request_json(
        "/fapi/v1/klines",
        {
            "symbol": symbol,
            "interval": "1m",
            "limit": limit,
        },
    )

    # 진행 중인 마지막 1분봉 제외
    return candles[:-1]


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


def calculate_volume_ratio(volumes):
    if len(volumes) < 6:
        return 0.0

    latest_volume = volumes[-1]

    previous_volumes = volumes[
        -6:-1
    ]

    average_volume = (
        sum(previous_volumes)
        / len(previous_volumes)
    )

    if average_volume == 0:
        return 0.0

    return (
        latest_volume
        / average_volume
    )


def calculate_indicators(closes):
    dataframe = pd.DataFrame(
        {
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

    latest = dataframe.iloc[-1]

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
    }


def analyze_symbol(symbol):
    candles = get_closed_candles(
        symbol=symbol,
        limit=100,
    )

    if len(candles) < 60:
        return None

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

    indicators = calculate_indicators(
        closes
    )

    return {
        "symbol": symbol,
        "current_price": current_price,
        "move_5m": move_5m,
        "volume_ratio": volume_ratio,
        "ema20": indicators["ema20"],
        "ema50": indicators["ema50"],
        "rsi": indicators["rsi"],
    }


def scan_market():
    top_symbols = get_top_volume_symbols()
    results = []

    print()
    print(
        f"거래대금 상위 "
        f"{len(top_symbols)}개 분석 중..."
    )

    print(
        f"웹 설정 최소 진입 점수: "
        f"{config.MINIMUM_ENTRY_SCORE}"
    )

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

            if result is not None:
                result[
                    "price_change_24h"
                ] = item[
                    "price_change_24h"
                ]

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
                    f"{symbol:<12} "
                    f"{trend} | "
                    f"5분 "
                    f"{result['move_5m']:+.3f}% | "
                    f"RSI "
                    f"{result['rsi']:.1f}",
                    flush=True,
                )

        except Exception as error:
            print(
                f"{symbol} 분석 실패: "
                f"{error}",
                flush=True,
            )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    return results


def print_rankings(results):
    rising = sorted(
        results,
        key=lambda item: item["move_5m"],
        reverse=True,
    )

    falling = sorted(
        results,
        key=lambda item: item["move_5m"],
    )

    print()
    print("최근 5분 상승률 상위")
    print("-" * 75)

    for item in rising[:5]:
        print(
            f"{item['symbol']:<12} "
            f"{item['move_5m']:+.3f}% | "
            f"거래량 "
            f"{item['volume_ratio']:.2f}배 | "
            f"RSI {item['rsi']:.1f}"
        )

    print()
    print("최근 5분 하락률 상위")
    print("-" * 75)

    for item in falling[:5]:
        print(
            f"{item['symbol']:<12} "
            f"{item['move_5m']:+.3f}% | "
            f"거래량 "
            f"{item['volume_ratio']:.2f}배 | "
            f"RSI {item['rsi']:.1f}"
        )


if __name__ == "__main__":
    from strategy import (
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