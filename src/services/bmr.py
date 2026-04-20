from src.db.models import ActivityLevel, Goal, Profile

ACTIVITY_FACTORS: dict[str, float] = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHTLY_ACTIVE: 1.375,
    ActivityLevel.MODERATELY_ACTIVE: 1.55,
    ActivityLevel.VERY_ACTIVE: 1.725,
    ActivityLevel.EXTRA_ACTIVE: 1.9,
}

GOAL_ADJUSTMENTS: dict[str, int] = {
    Goal.LOSE: -500,
    Goal.MAINTAIN: 0,
    Goal.GAIN: 300,
}


def calc_bmr(profile: Profile) -> float:
    """体脂肪率があれば Katch-McArdle、なければ Mifflin-St Jeor で BMR を計算する。"""
    if profile.body_fat_pct is not None:
        lean_mass = profile.weight_kg * (1 - profile.body_fat_pct / 100)
        return 370 + 21.6 * lean_mass
    else:
        if profile.gender == "male":
            return 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + 5
        else:
            return 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age - 161


def calc_tdee(profile: Profile) -> float:
    return calc_bmr(profile) * ACTIVITY_FACTORS[profile.activity_level]


def calc_calorie_target(profile: Profile) -> float:
    return calc_tdee(profile) + GOAL_ADJUSTMENTS[profile.goal]
