import time

from binance_api import (
    get_usdt_perpetual_symbols,
    request_json,
)


TOP_COUNT = 20
MOMENTUM_MINUTES = 5
REQUEST_DELAY_SECONDS = 0.08


def get_top_volume_symbols():
    valid_symbols = set(get_usdt_perpetual_symbols())
    tickers = request_json("/fapi/v1/ticker/24hr")

    ranked = []

    for ticker in tickers:
        symbol = ticker.get("symbol")

        if symbol not in valid_symbols:
            continue

        try:
            quote_volume = float(ticker.get("quoteVolume", 0))
            price_change = float(
                ticker.get("priceChangePercent", 0)
            )
        except (TypeError, ValueError):
            continue

        ranked.append(
            {
                "symbol": symbol,
                "quote_volume": quote_volume,
                "price_change_24h": price_change,
            }
        )

    ranked.sort(
        key=lambda item: item["quote_volume"],
        reverse=True,
    )

    return ranked[:TOP_COUNT]


def get_closed_candles(symbol, limit=12):
    candles = request_json(
        "/fapi/v1/klines",
        {
            "symbol": symbol,
            "interval": "1m",
            "limit": limit,
        },
    )

    # 마지막 봉은 진행 중일 수 있으므로 제외
    return candles[:-1]


def calculate_percent_change(old_price, new_price):
    if old_price == 0:
        return 0.0

    return ((new_price - old_price) / old_price) * 100


def calculate_volume_ratio(volumes):
    if len(volumes) < 6:
        return 0.0

    latest_volume = volumes[-1]
    previous_volumes = volumes[-6:-1]
    average_volume = sum(previous_volumes) / len(previous_volumes)

    if average_volume == 0:
        return 0.0

    return latest_volume / average_volume


def analyze_symbol(symbol):
    candles = get_closed_candles(symbol)

    if len(candles) < MOMENTUM_MINUTES + 6:
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
    old_price = closes[-(MOMENTUM_MINUTES + 1)]

    move_5m = calculate_percent_change(
        old_price,
        current_price,
    )

    volume_ratio = calculate_volume_ratio(volumes)

    return {
        "symbol": symbol,
        "current_price": current_price,
        "move_5m": move_5m,
        "volume_ratio": volume_ratio,
    }


def scan_market():
    top_symbols = get_top_volume_symbols()
    results = []

    print(
        f"거래대금 상위 {len(top_symbols)}개 분석 중...\n",
        flush=True,
    )

    for index, item in enumerate(top_symbols, start=1):
        symbol = item["symbol"]

        try:
            result = analyze_symbol(symbol)

            if result is not None:
                result["price_change_24h"] = (
                    item["price_change_24h"]
                )
                results.append(result)

                print(
                    f"{index:>2}/{len(top_symbols)} "
                    f"{symbol} 분석 완료",
                    flush=True,
                )

        except Exception as error:
            print(
                f"{symbol} 분석 실패: {error}",
                flush=True,
            )

        time.sleep(REQUEST_DELAY_SECONDS)

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

    volume_surge = sorted(
        results,
        key=lambda item: item["volume_ratio"],
        reverse=True,
    )

    print("\n최근 5분 상승률 상위")
    print("-" * 55)

    for index, item in enumerate(rising[:5], start=1):
        print(
            f"{index}. {item['symbol']:<12} "
            f"{item['move_5m']:+.3f}% | "
            f"거래량 {item['volume_ratio']:.2f}배"
        )

    print("\n최근 5분 하락률 상위")
    print("-" * 55)

    for index, item in enumerate(falling[:5], start=1):
        print(
            f"{index}. {item['symbol']:<12} "
            f"{item['move_5m']:+.3f}% | "
            f"거래량 {item['volume_ratio']:.2f}배"
        )

    print("\n거래량 급증 상위")
    print("-" * 55)

    for index, item in enumerate(
        volume_surge[:5],
        start=1,
    ):
        print(
            f"{index}. {item['symbol']:<12} "
            f"거래량 {item['volume_ratio']:.2f}배 | "
            f"5분 {item['move_5m']:+.3f}%"
        )


if __name__ == "__main__":
    from strategy import rank_candidates, print_candidates

    market_results = scan_market()

    print_rankings(market_results)

    candidates = rank_candidates(market_results)

    print_candidates(candidates)