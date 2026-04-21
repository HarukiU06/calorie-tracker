"""Tests for BMR/TDEE/calorie target calculations."""

from types import SimpleNamespace

import pytest

from src.db.models import ActivityLevel, Goal
from src.services.bmr import ACTIVITY_FACTORS, calc_bmr, calc_calorie_target, calc_tdee


def _make_profile(**kwargs) -> SimpleNamespace:
    defaults = dict(
        gender="male",
        age=30,
        height_cm=175.0,
        weight_kg=70.0,
        body_fat_pct=None,
        activity_level=ActivityLevel.SEDENTARY,
        goal=Goal.MAINTAIN,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestMifflinStJeor:
    def test_male(self):
        p = _make_profile(gender="male", weight_kg=70, height_cm=175, age=30)
        expected = 10 * 70 + 6.25 * 175 - 5 * 30 + 5  # 1648.75
        assert calc_bmr(p) == pytest.approx(expected)

    def test_female(self):
        p = _make_profile(gender="female", weight_kg=60, height_cm=165, age=25)
        expected = 10 * 60 + 6.25 * 165 - 5 * 25 - 161  # 1400.25
        assert calc_bmr(p) == pytest.approx(expected)

    def test_used_when_no_body_fat(self):
        p = _make_profile(body_fat_pct=None)
        bmr = calc_bmr(p)
        mifflin = 10 * 70 + 6.25 * 175 - 5 * 30 + 5
        assert bmr == pytest.approx(mifflin)


class TestKatchMcArdle:
    def test_switches_when_body_fat_set(self):
        p = _make_profile(weight_kg=70, body_fat_pct=20.0)
        lean_mass = 70 * (1 - 20.0 / 100)  # 56 kg
        expected = 370 + 21.6 * lean_mass   # 1579.6
        assert calc_bmr(p) == pytest.approx(expected)

    def test_higher_body_fat_gives_lower_bmr(self):
        p_lean = _make_profile(weight_kg=70, body_fat_pct=10.0)
        p_fat = _make_profile(weight_kg=70, body_fat_pct=30.0)
        assert calc_bmr(p_lean) > calc_bmr(p_fat)

    def test_zero_body_fat_not_used(self):
        """body_fat_pct=None should use Mifflin, not Katch-McArdle."""
        p = _make_profile(weight_kg=70, body_fat_pct=None)
        mifflin = 10 * 70 + 6.25 * 175 - 5 * 30 + 5
        assert calc_bmr(p) == pytest.approx(mifflin)


class TestTDEE:
    @pytest.mark.parametrize("level,factor", list(ACTIVITY_FACTORS.items()))
    def test_activity_factors(self, level, factor):
        p = _make_profile(activity_level=level)
        assert calc_tdee(p) == pytest.approx(calc_bmr(p) * factor)

    def test_sedentary_is_lowest(self):
        base = _make_profile()
        tdees = [
            calc_tdee(_make_profile(activity_level=lvl))
            for lvl in ActivityLevel
        ]
        assert calc_tdee(base) == min(tdees)


class TestCalorieTarget:
    def test_maintain(self):
        p = _make_profile(goal=Goal.MAINTAIN)
        assert calc_calorie_target(p) == pytest.approx(calc_tdee(p))

    def test_lose_is_tdee_minus_500(self):
        p = _make_profile(goal=Goal.LOSE)
        assert calc_calorie_target(p) == pytest.approx(calc_tdee(p) - 500)

    def test_gain_is_tdee_plus_300(self):
        p = _make_profile(goal=Goal.GAIN)
        assert calc_calorie_target(p) == pytest.approx(calc_tdee(p) + 300)

    def test_lose_less_than_maintain_less_than_gain(self):
        lose = calc_calorie_target(_make_profile(goal=Goal.LOSE))
        maintain = calc_calorie_target(_make_profile(goal=Goal.MAINTAIN))
        gain = calc_calorie_target(_make_profile(goal=Goal.GAIN))
        assert lose < maintain < gain
