MIN_ENTRY_SCORE = 45


def calculate_score(item):
    move_5m = item["move_5m"]
    volume_ratio = item["volume_ratio"]
    change_24h = item["price_change_24h"]

    ema20 = item["ema20"]
    ema50 = item["ema50"]
    rsi = item["rsi"]

    long_score = 0
    short_score = 0

    long_reasons = []
    short_reasons = []

    # 거래량 점수
    if volume_ratio >= 3.0:
        long_score += 25
        short_score += 25

    elif volume_ratio >= 2.0:
        long_score += 20
        short_score += 20

    elif volume_ratio >= 1.5:
        long_score += 15
        short_score += 15

    elif volume_ratio < 0.8:
        long_score -= 20
        short_score -= 20

    # EMA 추세
    if ema20 > ema50:
        long_score += 30
        short_score -= 30
        long_reasons.append("EMA 상승추세")

    elif ema20 < ema50:
        short_score += 30
        long_score -= 30
        short_reasons.append("EMA 하락추세")

    # 최근 5분 움직임
    if 0.3 <= move_5m < 1.5:
        long_score += 25
        long_reasons.append("단기 상승")

    elif move_5m >= 3.0:
        long_score -= 50
        long_reasons.append("급등 과열")

    if -1.5 < move_5m <= -0.3:
        short_score += 25
        short_reasons.append("단기 하락")

    elif move_5m <= -3.0:
        short_score -= 50
        short_reasons.append("급락 과열")

    # RSI 롱 조건
    if 45 <= rsi <= 68:
        long_score += 20
        long_reasons.append("롱 RSI 적정")

    elif rsi >= 75:
        long_score -= 40
        long_reasons.append("RSI 과매수")

    elif rsi <= 30:
        long_score -= 15

    # RSI 숏 조건
    if 32 <= rsi <= 55:
        short_score += 20
        short_reasons.append("숏 RSI 적정")

    elif rsi <= 25:
        short_score -= 40
        short_reasons.append("RSI 과매도")

    elif rsi >= 70:
        short_score -= 15

    # 24시간 추세
    if 1.0 <= change_24h <= 12.0:
        long_score += 10

    elif -12.0 <= change_24h <= -1.0:
        short_score += 10

    # 장기 과열 제외
    if change_24h >= 20:
        long_score -= 40

    if change_24h <= -20:
        short_score -= 40

    if long_score > short_score:
        side = "LONG"
        final_score = long_score
        reasons = long_reasons

    elif short_score > long_score:
        side = "SHORT"
        final_score = short_score
        reasons = short_reasons

    else:
        side = "NONE"
        final_score = max(
            long_score,
            short_score,
        )
        reasons = []

    if final_score < MIN_ENTRY_SCORE:
        side = "NONE"

    return {
        "symbol": item["symbol"],
        "side": side,
        "score": final_score,
        "long_score": long_score,
        "short_score": short_score,
        "move_5m": move_5m,
        "volume_ratio": volume_ratio,
        "price_change_24h": change_24h,
        "ema20": ema20,
        "ema50": ema50,
        "rsi": rsi,
        "reasons": reasons,
    }


def rank_candidates(market_results):
    candidates = []

    for item in market_results:
        result = calculate_score(item)

        if result["side"] != "NONE":
            candidates.append(result)

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return candidates


def print_candidates(candidates):
    print()
    print("매매 후보 순위")
    print("=" * 90)

    if not candidates:
        print(
            "현재 진입 조건을 만족하는 "
            "코인이 없습니다."
        )
        return

    for index, item in enumerate(
        candidates[:10],
        start=1,
    ):
        print(
            f"{index:>2}. "
            f"{item['symbol']:<12} "
            f"{item['side']:<5} "
            f"{item['score']:>3}점 | "
            f"5분 {item['move_5m']:+.3f}% | "
            f"거래량 {item['volume_ratio']:.2f}배 | "
            f"RSI {item['rsi']:.1f}"
        )