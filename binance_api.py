import json
import urllib.parse
import urllib.request


BASE_URL = "https://fapi.binance.com"


def request_json(path, params=None):
    if params is None:
        params = {}

    query = urllib.parse.urlencode(params)
    url = f"{BASE_URL}{path}"

    if query:
        url = f"{url}?{query}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        text = response.read().decode("utf-8")
        return json.loads(text)


def get_current_price(symbol):
    data = request_json(
        "/fapi/v1/ticker/price",
        {"symbol": symbol},
    )

    return float(data["price"])


def get_usdt_perpetual_symbols():
    data = request_json("/fapi/v1/exchangeInfo")

    symbols = []

    for item in data["symbols"]:
        if item.get("status") != "TRADING":
            continue

        if item.get("quoteAsset") != "USDT":
            continue

        if item.get("contractType") != "PERPETUAL":
            continue

        symbols.append(item["symbol"])

    return symbols


if __name__ == "__main__":
    print("프로그램 시작", flush=True)

    print("BTC 가격 요청 중...", flush=True)
    btc_price = get_current_price("BTCUSDT")
    print(f"BTC 선물 현재가: {btc_price:,.2f} USDT", flush=True)

    print("선물 종목 목록 요청 중...", flush=True)
    symbols = get_usdt_perpetual_symbols()

    print(
        f"거래 가능한 USDT 무기한 선물: {len(symbols)}개",
        flush=True,
    )

    print("처음 10개 종목:", flush=True)

    for symbol in symbols[:10]:
        print(symbol, flush=True)