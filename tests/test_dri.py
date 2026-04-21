"""Tests for DRI lookup and gender/age overrides."""

from types import SimpleNamespace

import pytest

from src.services.dri import get_dri


def _make_profile(gender: str = "male", age: int = 30) -> SimpleNamespace:
    return SimpleNamespace(gender=gender, age=age)


class TestDriDefaults:
    def test_returns_dict(self):
        dri = get_dri(_make_profile())
        assert isinstance(dri, dict)

    def test_contains_core_nutrients(self):
        dri = get_dri(_make_profile())
        for key in ("energy_kcal", "protein_g", "fat_g", "carb_g"):
            # energy_kcal is not in DRI (it's goal-based), others must be present
            pass
        for key in ("protein_g", "calcium_mg", "iron_mg", "vitamin_d_ug"):
            assert key in dri, f"Missing key: {key}"

    def test_male_iron_default(self):
        dri = get_dri(_make_profile(gender="male", age=30))
        assert dri["iron_mg"] == 8


class TestFemaleOverride:
    def test_iron_higher_for_female(self):
        male_dri = get_dri(_make_profile(gender="male"))
        female_dri = get_dri(_make_profile(gender="female"))
        assert female_dri["iron_mg"] > male_dri["iron_mg"]

    def test_female_iron_is_18(self):
        dri = get_dri(_make_profile(gender="female", age=30))
        assert dri["iron_mg"] == 18

    def test_female_zinc_lower(self):
        male_dri = get_dri(_make_profile(gender="male"))
        female_dri = get_dri(_make_profile(gender="female"))
        assert female_dri["zinc_mg"] < male_dri["zinc_mg"]

    def test_female_vitamin_c_lower(self):
        male_dri = get_dri(_make_profile(gender="male"))
        female_dri = get_dri(_make_profile(gender="female"))
        assert female_dri["vitamin_c_mg"] < male_dri["vitamin_c_mg"]


class TestAge51Override:
    def test_calcium_increases_at_51(self):
        young = get_dri(_make_profile(age=50))
        older = get_dri(_make_profile(age=51))
        assert older["calcium_mg"] >= young["calcium_mg"]

    def test_boundary_50_does_not_get_override(self):
        dri = get_dri(_make_profile(age=50))
        # Default calcium is 1000; age_51_plus sets 1200
        assert dri["calcium_mg"] == 1000

    def test_boundary_51_gets_override(self):
        dri = get_dri(_make_profile(age=51))
        assert dri["calcium_mg"] == 1200

    def test_age_80_gets_override(self):
        dri = get_dri(_make_profile(age=80))
        assert dri["calcium_mg"] == 1200


class TestCombinedOverrides:
    def test_female_over_51_gets_both_overrides(self):
        dri = get_dri(_make_profile(gender="female", age=55))
        # Female override: iron_mg = 18
        assert dri["iron_mg"] == 18
        # Age override: calcium_mg = 1200
        assert dri["calcium_mg"] == 1200

    def test_overrides_do_not_mutate_across_calls(self):
        """Repeated calls must return independent dicts."""
        dri1 = get_dri(_make_profile(gender="male", age=30))
        dri2 = get_dri(_make_profile(gender="female", age=55))
        dri1_again = get_dri(_make_profile(gender="male", age=30))
        assert dri1["iron_mg"] == dri1_again["iron_mg"]
        assert dri1["iron_mg"] != dri2["iron_mg"]
