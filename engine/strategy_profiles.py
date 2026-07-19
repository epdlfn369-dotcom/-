PROFILES = {
    "balanced": {
        "volume_very_strong": 25,
        "volume_strong": 20,
        "volume_increase": 15,
        "volume_low_penalty": 20,
        "ema_trend": 30,
        "move_moderate": 25,
        "move_strong": 10,
        "move_overheat_penalty": 50,
        "rsi_good": 20,
        "rsi_extreme_penalty": 40,
        "rsi_opposite_penalty": 15,
        "change_24h_trend": 10,
        "change_24h_overheat_penalty": 40,
    },
    "conservative": {
        "volume_very_strong": 10,
        "volume_strong": 10,
        "volume_increase": 10,
        "volume_low_penalty": 25,
        "ema_trend": 40,
        "move_moderate": 30,
        "move_strong": 5,
        "move_overheat_penalty": 60,
        "rsi_good": 30,
        "rsi_extreme_penalty": 50,
        "rsi_opposite_penalty": 20,
        "change_24h_trend": 0,
        "change_24h_overheat_penalty": 50,
    },
    "aggressive": {
        "volume_very_strong": 30,
        "volume_strong": 25,
        "volume_increase": 20,
        "volume_low_penalty": 10,
        "ema_trend": 25,
        "move_moderate": 30,
        "move_strong": 20,
        "move_overheat_penalty": 35,
        "rsi_good": 15,
        "rsi_extreme_penalty": 30,
        "rsi_opposite_penalty": 10,
        "change_24h_trend": 15,
        "change_24h_overheat_penalty": 30,
    },
}


def get_strategy_profile(name):
    normalized = str(name).strip().lower()
    if normalized not in PROFILES:
        normalized = "balanced"
    return normalized, PROFILES[normalized]
