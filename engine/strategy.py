import config
from engine.strategy_profiles import get_strategy_profile


PROFILE_NAME, PROFILE = get_strategy_profile(
    config.STRATEGY_PROFILE
)


def calculate_score(item):
    move_5m = float(
        item["move_5m"]
    )
    volume_ratio = float(
        item["volume_ratio"]
    )
    change_24h = float(
        item["price_change_24h"]
    )
    ema20 = float(
        item["ema20"]
    )
    ema50 = float(
        item["ema50"]
    )
    rsi = float(
        item["rsi"]
    )

    long_score = 0
    short_score = 0

    long_reasons = []
    short_reasons = []

    long_components = {}
    short_components = {}

    def add_component(
        components,
        reasons,
        key,
        value,
        reason=None,
    ):
        components[key] = (
            components.get(
                key,
                0,
            )
            + value
        )

        if reason:
            reasons.append(
                reason
            )

        return value

    # ==================================================
    # 거래량
    # ==================================================
    if volume_ratio >= 3.0:
        value = PROFILE[
            "volume_very_strong"
        ]

        long_score += add_component(
            long_components,
            long_reasons,
            "volume",
            value,
            "거래량 매우 강함",
        )

        short_score += add_component(
            short_components,
            short_reasons,
            "volume",
            value,
            "거래량 매우 강함",
        )

    elif volume_ratio >= 2.0:
        value = PROFILE[
            "volume_strong"
        ]

        long_score += add_component(
            long_components,
            long_reasons,
            "volume",
            value,
            "거래량 강함",
        )

        short_score += add_component(
            short_components,
            short_reasons,
            "volume",
            value,
            "거래량 강함",
        )

    elif volume_ratio >= 1.5:
        value = PROFILE[
            "volume_increase"
        ]

        long_score += add_component(
            long_components,
            long_reasons,
            "volume",
            value,
            "거래량 증가",
        )

        short_score += add_component(
            short_components,
            short_reasons,
            "volume",
            value,
            "거래량 증가",
        )

    elif volume_ratio < 0.8:
        value = -PROFILE[
            "volume_low_penalty"
        ]

        long_score += add_component(
            long_components,
            long_reasons,
            "volume",
            value,
            "거래량 부족",
        )

        short_score += add_component(
            short_components,
            short_reasons,
            "volume",
            value,
            "거래량 부족",
        )

    # ==================================================
    # EMA
    # ==================================================
    if ema20 > ema50:
        value = PROFILE[
            "ema_trend"
        ]

        long_score += add_component(
            long_components,
            long_reasons,
            "ema_trend",
            value,
            "EMA 상승추세",
        )

        short_score += add_component(
            short_components,
            short_reasons,
            "ema_trend",
            -value,
            "EMA 역방향",
        )

    elif ema20 < ema50:
        value = PROFILE[
            "ema_trend"
        ]

        short_score += add_component(
            short_components,
            short_reasons,
            "ema_trend",
            value,
            "EMA 하락추세",
        )

        long_score += add_component(
            long_components,
            long_reasons,
            "ema_trend",
            -value,
            "EMA 역방향",
        )

    # ==================================================
    # 최근 5분 움직임
    # ==================================================
    if 0.3 <= move_5m < 1.5:
        value = PROFILE[
            "move_moderate"
        ]

        long_score += add_component(
            long_components,
            long_reasons,
            "move_5m",
            value,
            "적당한 단기 상승",
        )

    elif 1.5 <= move_5m < 3.0:
        value = PROFILE[
            "move_strong"
        ]

        long_score += add_component(
            long_components,
            long_reasons,
            "move_5m",
            value,
            "강한 단기 상승",
        )

    elif move_5m >= 3.0:
        value = -PROFILE[
            "move_overheat_penalty"
        ]

        long_score += add_component(
            long_components,
            long_reasons,
            "move_5m",
            value,
            "급등 과열",
        )

    if -1.5 < move_5m <= -0.3:
        value = PROFILE[
            "move_moderate"
        ]

        short_score += add_component(
            short_components,
            short_reasons,
            "move_5m",
            value,
            "적당한 단기 하락",
        )

    elif -3.0 < move_5m <= -1.5:
        value = PROFILE[
            "move_strong"
        ]

        short_score += add_component(
            short_components,
            short_reasons,
            "move_5m",
            value,
            "강한 단기 하락",
        )

    elif move_5m <= -3.0:
        value = -PROFILE[
            "move_overheat_penalty"
        ]

        short_score += add_component(
            short_components,
            short_reasons,
            "move_5m",
            value,
            "급락 과열",
        )

    # ==================================================
    # RSI
    # ==================================================
    if 45 <= rsi <= 68:
        value = PROFILE[
            "rsi_good"
        ]

        long_score += add_component(
            long_components,
            long_reasons,
            "rsi",
            value,
            "롱 RSI 적정",
        )

    elif rsi >= 75:
        value = -PROFILE[
            "rsi_extreme_penalty"
        ]

        long_score += add_component(
            long_components,
            long_reasons,
            "rsi",
            value,
            "RSI 과매수",
        )

    elif rsi <= 30:
        value = -PROFILE[
            "rsi_opposite_penalty"
        ]

        long_score += add_component(
            long_components,
            long_reasons,
            "rsi",
            value,
            "롱 RSI 불리",
        )

    if 32 <= rsi <= 55:
        value = PROFILE[
            "rsi_good"
        ]

        short_score += add_component(
            short_components,
            short_reasons,
            "rsi",
            value,
            "숏 RSI 적정",
        )

    elif rsi <= 25:
        value = -PROFILE[
            "rsi_extreme_penalty"
        ]

        short_score += add_component(
            short_components,
            short_reasons,
            "rsi",
            value,
            "RSI 과매도",
        )

    elif rsi >= 70:
        value = -PROFILE[
            "rsi_opposite_penalty"
        ]

        short_score += add_component(
            short_components,
            short_reasons,
            "rsi",
            value,
            "숏 RSI 불리",
        )

    # ==================================================
    # 24시간 추세
    # ==================================================
    if 1.0 <= change_24h <= 12.0:
        value = PROFILE[
            "change_24h_trend"
        ]

        long_score += add_component(
            long_components,
            long_reasons,
            "change_24h",
            value,
            "24시간 상승 추세",
        )

    elif -12.0 <= change_24h <= -1.0:
        value = PROFILE[
            "change_24h_trend"
        ]

        short_score += add_component(
            short_components,
            short_reasons,
            "change_24h",
            value,
            "24시간 하락 추세",
        )

    if change_24h >= 20.0:
        value = -PROFILE[
            "change_24h_overheat_penalty"
        ]

        long_score += add_component(
            long_components,
            long_reasons,
            "change_24h_overheat",
            value,
            "24시간 급등 과열",
        )

    if change_24h <= -20.0:
        value = -PROFILE[
            "change_24h_overheat_penalty"
        ]

        short_score += add_component(
            short_components,
            short_reasons,
            "change_24h_overheat",
            value,
            "24시간 급락 과열",
        )

    # ==================================================
    # 최종 방향
    # ==================================================
    if long_score > short_score:
        side = "LONG"
        final_score = long_score
        reasons = long_reasons
        score_components = (
            long_components
        )

    elif short_score > long_score:
        side = "SHORT"
        final_score = short_score
        reasons = short_reasons
        score_components = (
            short_components
        )

    else:
        side = "NONE"
        final_score = max(
            long_score,
            short_score,
        )
        reasons = []
        score_components = {}

    if (
        final_score
        < config.MINIMUM_ENTRY_SCORE
    ):
        side = "NONE"
        reasons = []

    result = dict(item)

    result.update(
        {
            "symbol": item["symbol"],
            "side": side,
            "score": final_score,
            "long_score": long_score,
            "short_score": short_score,
            "move_5m": move_5m,
            "volume_ratio": volume_ratio,
            "price_change_24h": (
                change_24h
            ),
            "ema20": ema20,
            "ema50": ema50,
            "rsi": rsi,
            "reasons": reasons,
            "score_components": (
                score_components
            ),
            "long_score_components": (
                long_components
            ),
            "short_score_components": (
                short_components
            ),
            "strategy_profile": (
                PROFILE_NAME
            ),
        }
    )

    return result


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