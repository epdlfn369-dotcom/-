def calculate_score(item):
    """
    scanner.py가 만든 분석 결과에 점수를 준다.

    필요한 값:
    symbol
    move_5m
    volume_ratio
    price_change_24h
    """

    move_5m = item["move_5m"]
    volume_ratio = item["volume_ratio"]
    change_24h = item["price_change_24h"]

    long_score = 0
    short_score = 0
    reasons = []

    # 거래량 점수
    if volume_ratio >= 3.0:
        long_score += 25
        short_score += 25
        reasons.append("거래량 매우 강함")

    elif volume_ratio >= 2.0:
        long_score += 20
        short_score += 20
        reasons.append("거래량 강함")

    elif volume_ratio >= 1.5:
        long_score += 15
        short_score += 15
        reasons.append("거래량 증가")

    elif volume_ratio < 0.8:
        long_score -= 20
        short_score -= 20
        reasons.append("거래량 부족")

    # 최근 5분 상승 점수
    if 0.3 <= move_5m < 1.0:
        long_score += 30
        reasons.append("적당한 단기 상승")

    elif 1.0 <= move_5m < 2.0:
        long_score += 20
        reasons.append("강한 단기 상승")

    elif 2.0 <= move_5m < 3.0:
        long_score += 5
        reasons.append("상승 과열 주의")

    elif move_5m >= 3.0:
        long_score -= 50
        reasons.append("급등 과열 제외")

    # 최근 5분 하락 점수
    if -1.0 < move_5m <= -0.3:
        short_score += 30
        reasons.append("적당한 단기 하락")

    elif -2.0 < move_5m <= -1.0:
        short_score += 20
        reasons.append("강한 단기 하락")

    elif -3.0 < move_5m <= -2.0:
        short_score += 5
        reasons.append("하락 과열 주의")

    elif move_5m <= -3.0:
        short_score -= 50
        reasons.append("급락 과열 제외")

    # 24시간 추세 보조점수
    if 1.0 <= change_24h <= 10.0:
        long_score += 15
        reasons.append("24시간 상승 추세")

    elif -10.0 <= change_24h <= -1.0:
        short_score += 15
        reasons.append("24시간 하락 추세")

    # 지나치게 오른 코인 감점
    if change_24h >= 20.0:
        long_score -= 40
        reasons.append("24시간 급등 과열")

    # 지나치게 떨어진 코인 감점
    if change_24h <= -20.0:
        short_score -= 40
        reasons.append("24시간 급락 과열")

    if long_score > short_score:
        side = "LONG"
        final_score = long_score

    elif short_score > long_score:
        side = "SHORT"
        final_score = short_score

    else:
        side = "NONE"
        final_score = max(long_score, short_score)

    # 최소 진입 점수
    if final_score < 30:
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
    print("\n매매 후보 순위")
    print("=" * 70)

    if not candidates:
        print("현재 진입 조건을 만족하는 코인이 없습니다.")
        return

    for index, item in enumerate(candidates[:10], start=1):
        print(
            f"{index:>2}. "
            f"{item['symbol']:<12} "
            f"{item['side']:<5} "
            f"{item['score']:>3}점 | "
            f"5분 {item['move_5m']:+.3f}% | "
            f"거래량 {item['volume_ratio']:.2f}배 | "
            f"24시간 {item['price_change_24h']:+.2f}%"
        )