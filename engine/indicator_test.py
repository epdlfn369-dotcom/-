import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

from binance_api import request_json


def get_candle_dataframe(symbol="BTCUSDT", interval="5m", limit=100):
    candles = request_json(
        "/fapi/v1/klines",
        {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        },
    )

    rows = []

    for candle in candles:
        rows.append(
            {
                "time": pd.to_datetime(
                    candle[0],
                    unit="ms",
                ),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
            }
        )

    return pd.DataFrame(rows)


def add_indicators(dataframe):
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

    return dataframe


def main():
    print("BTCUSDT 캔들 요청 중...", flush=True)

    dataframe = get_candle_dataframe()
    dataframe = add_indicators(dataframe)

    latest = dataframe.iloc[-1]

    print()
    print("=" * 50)
    print("기술지표 계산 결과")
    print("=" * 50)
    print(f"시간: {latest['time']}")
    print(f"현재가: {latest['close']:,.2f} USDT")
    print(f"EMA20: {latest['ema20']:,.2f}")
    print(f"EMA50: {latest['ema50']:,.2f}")
    print(f"RSI14: {latest['rsi']:.2f}")

    if latest["ema20"] > latest["ema50"]:
        print("큰 추세: 상승")
    else:
        print("큰 추세: 하락")

    if latest["rsi"] >= 70:
        print("RSI 상태: 과매수")
    elif latest["rsi"] <= 30:
        print("RSI 상태: 과매도")
    else:
        print("RSI 상태: 중립")


if __name__ == "__main__":
    main()