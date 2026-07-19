import config
from engine.strategy_profiles import get_strategy_profile


PROFILE_NAME, PROFILE = get_strategy_profile(
    config.STRATEGY_PROFILE
)


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

    if volume_ratio >= 3.0:
        score = PROFILE["volume_very_strong"]
        long_score += score
        short_score += score
        long_reasons.append("거래량 매우 강함")
        short_reasons.append("거래량 매우 강함")
    elif volume_ratio >= 2.0:
        score = PROFILE["volume_strong"]
        long_score += score
        short_score += score
        long_reasons.append("거래량 강함")
        short_reasons.append("거래량 강함")
    elif volume_ratio >= 1.5:
        score = PROFILE["volume_increase"]
        long_score += score
        short_score += score
        long_reasons.append("거래량 증가")
        short_reasons.append("거래량 증가")
    elif volume_ratio < 0.8:
        penalty = PROFILE["volume_low_penalty"]
        long_score -= penalty
        short_score -= penalty

    if ema20 > ema50:
        score = PROFILE["ema_trend"]
        long_score += score
        short_score -= score
        long_reasons.append("EMA 상승추세")
    elif ema20 < ema50:
        score = PROFILE["ema_trend"]
        short_score += score
        long_score -= score
        short_reasons.append("EMA 하락추세")

    if 0.3 <= move_5m < 1.5:
        long_score += PROFILE["move_moderate"]
        long_reasons.append("적당한 단기 상승")
    elif 1.5 <= move_5m < 3.0:
        long_score += PROFILE["move_strong"]
        long_reasons.append("강한 단기 상승")
    elif move_5m >= 3.0:
        long_score -= PROFILE["move_overheat_penalty"]
        long_reasons.append("급등 과열")

    if -1.5 < move_5m <= -0.3:
        short_score += PROFILE["move_moderate"]
        short_reasons.append("적당한 단기 하락")
    elif -3.0 < move_5m <= -1.5:
        short_score += PROFILE["move_strong"]
        short_reasons.append("강한 단기 하락")
    elif move_5m <= -3.0:
        short_score -= PROFILE["move_overheat_penalty"]
        short_reasons.append("급락 과열")

    if 45 <= rsi <= 68:
        long_score += PROFILE["rsi_good"]
        long_reasons.append("롱 RSI 적정")
    elif rsi >= 75:
        long_score -= PROFILE["rsi_extreme_penalty"]
        long_reasons.append("RSI 과매수")
    elif rsi <= 30:
        long_score -= PROFILE["rsi_opposite_penalty"]

    if 32 <= rsi <= 55:
        short_score += PROFILE["rsi_good"]
        short_reasons.append("숏 RSI 적정")
    elif rsi <= 25:
        short_score -= PROFILE["rsi_extreme_penalty"]
        short_reasons.append("RSI 과매도")
    elif rsi >= 70:
        short_score -= PROFILE["rsi_opposite_penalty"]

    if 1.0 <= change_24h <= 12.0:
        long_score += PROFILE["change_24h_trend"]
        long_reasons.append("24시간 상승 추세")
    elif -12.0 <= change_24h <= -1.0:
        short_score += PROFILE["change_24h_trend"]
        short_reasons.append("24시간 하락 추세")

    if change_24h >= 20.0:
        long_score -= PROFILE["change_24h_overheat_penalty"]
        long_reasons.append("24시간 급등 과열")
    if change_24h <= -20.0:
        short_score -= PROFILE["change_24h_overheat_penalty"]
        short_reasons.append("24시간 급락 과열")

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
        final_score = max(long_score, short_score)
        reasons = []

    if final_score < config.MINIMUM_ENTRY_SCORE:
        side = "NONE"
        reasons = []

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
        "strategy_profile": PROFILE_NAME,
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
    print("=" * 95)
    print(
        f"현재 최소 진입 점수: "
        f"{config.MINIMUM_ENTRY_SCORE}점"
    )
    print(
        f"현재 전략 프로필: "
        f"{PROFILE_NAME}"
    )

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
        reason_text = ", ".join(item["reasons"])
        print(
            f"{index:>2}. "
            f"{item['symbol']:<12} "
            f"{item['side']:<5} "
            f"{item['score']:>3}점 | "
            f"5분 {item['move_5m']:+.3f}% | "
            f"거래량 {item['volume_ratio']:.2f}배 | "
            f"RSI {item['rsi']:.1f}"
        )
        print(f"    이유: {reason_text}")
