"""Tests for USDA utility functions (no API calls)."""

import pytest

from src.services.usda import _extract_portions, scale_nutrients


class TestScaleNutrients:
    def test_100g_unchanged(self):
        n = {"energy_kcal": 200.0, "protein_g": 10.0}
        assert scale_nutrients(n, 100) == {"energy_kcal": 200.0, "protein_g": 10.0}

    def test_half_portion(self):
        n = {"energy_kcal": 200.0, "protein_g": 10.0}
        result = scale_nutrients(n, 50)
        assert result["energy_kcal"] == pytest.approx(100.0)
        assert result["protein_g"] == pytest.approx(5.0)

    def test_double_portion(self):
        n = {"energy_kcal": 100.0, "fat_g": 4.0}
        result = scale_nutrients(n, 200)
        assert result["energy_kcal"] == pytest.approx(200.0)
        assert result["fat_g"] == pytest.approx(8.0)

    def test_zero_grams_returns_zeros(self):
        n = {"energy_kcal": 200.0}
        result = scale_nutrients(n, 0)
        assert result["energy_kcal"] == 0.0

    def test_empty_nutrients(self):
        assert scale_nutrients({}, 100) == {}

    def test_result_is_rounded(self):
        n = {"protein_g": 10.123456}
        result = scale_nutrients(n, 33)
        assert len(str(result["protein_g"]).split(".")[-1]) <= 4


class TestExtractPortions:
    def _data(self, portions=None, serving_size=None, serving_unit="g"):
        return {
            "foodPortions": portions or [],
            "servingSize": serving_size,
            "servingSizeUnit": serving_unit,
        }

    def test_empty_data_returns_empty(self):
        assert _extract_portions(self._data()) == []

    def test_volume_units_excluded(self):
        data = self._data(portions=[
            {"gramWeight": 14, "modifier": "tablespoon", "amount": 1},
            {"gramWeight": 5, "modifier": "teaspoon", "amount": 1},
        ])
        assert _extract_portions(data) == []

    def test_piece_keywords_included(self):
        data = self._data(portions=[
            {"gramWeight": 50, "modifier": "large", "amount": 1},
        ])
        result = _extract_portions(data)
        assert len(result) == 1
        assert result[0]["grams"] == 50

    def test_piece_portions_sorted_first(self):
        data = self._data(portions=[
            {"gramWeight": 240, "modifier": "cup", "amount": 1},       # volume — excluded
            {"gramWeight": 44, "modifier": "medium", "amount": 1},     # piece
            {"gramWeight": 50, "modifier": "large", "amount": 1},      # piece
        ])
        result = _extract_portions(data)
        # cup excluded; large and medium remain, sorted by gram weight desc
        assert result[0]["grams"] == 50
        assert result[1]["grams"] == 44

    def test_branded_serving_size_fallback(self):
        data = self._data(serving_size=30, serving_unit="g")
        result = _extract_portions(data)
        assert len(result) == 1
        assert result[0]["grams"] == pytest.approx(30)

    def test_branded_ml_converts_to_grams(self):
        data = self._data(serving_size=1, serving_unit="ml")
        result = _extract_portions(data)
        assert result[0]["grams"] == pytest.approx(29.5735, rel=1e-3)

    def test_label_contains_gram_weight(self):
        data = self._data(portions=[
            {"gramWeight": 50, "modifier": "large", "amount": 1},
        ])
        result = _extract_portions(data)
        assert "50g" in result[0]["label"]
