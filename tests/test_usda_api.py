"""Tests for USDA API client functions (HTTP calls mocked)."""

from unittest.mock import MagicMock, patch

import pytest

from src.services.usda import get_food_detail, search_foods


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    if status_code >= 400:
        from requests import HTTPError
        mock.raise_for_status.side_effect = HTTPError(response=mock)
    else:
        mock.raise_for_status.return_value = None
    return mock


SEARCH_RESPONSE = {
    "foods": [
        {"fdcId": 748967, "description": "Egg, whole, raw", "dataType": "SR Legacy"},
        {"fdcId": 748968, "description": "Egg, whole, raw", "dataType": "Foundation"},  # duplicate
        {"fdcId": 173424, "description": "Egg, white, raw", "dataType": "SR Legacy"},
    ]
}

FOOD_DETAIL_FOUNDATION = {
    "fdcId": 748967,
    "description": "Egg, whole, raw",
    "foodNutrients": [
        {"nutrient": {"id": 1008}, "amount": 143.0},  # energy_kcal
        {"nutrient": {"id": 1003}, "amount": 12.6},   # protein_g
        {"nutrient": {"id": 1004}, "amount": 9.51},   # fat_g
        {"nutrient": {"id": 1005}, "amount": 0.72},   # carb_g
    ],
    "foodPortions": [
        {"gramWeight": 50, "modifier": "large", "amount": 1},
        {"gramWeight": 44, "modifier": "medium", "amount": 1},
        {"gramWeight": 14, "modifier": "tablespoon", "amount": 1},
    ],
}

FOOD_DETAIL_BRANDED = {
    "fdcId": 999999,
    "description": "Greek Yogurt",
    "servingSize": 150,
    "servingSizeUnit": "g",
    "foodNutrients": [
        {"nutrientId": 1008, "value": 100.0},
        {"nutrientId": 1003, "value": 17.0},
    ],
    "foodPortions": [],
}


class TestSearchFoods:
    @patch("src.services.usda.requests.get")
    def test_returns_deduplicated_results(self, mock_get):
        mock_get.return_value = _mock_response(SEARCH_RESPONSE)
        results = search_foods("egg")

        descriptions = [r["description"] for r in results]
        assert descriptions.count("Egg, whole, raw") == 1

    @patch("src.services.usda.requests.get")
    def test_result_structure(self, mock_get):
        mock_get.return_value = _mock_response(SEARCH_RESPONSE)
        results = search_foods("egg")

        assert all("fdc_id" in r and "description" in r for r in results)

    @patch("src.services.usda.requests.get")
    def test_empty_results(self, mock_get):
        mock_get.return_value = _mock_response({"foods": []})
        assert search_foods("xyznonexistent") == []

    @patch("src.services.usda.requests.get")
    def test_passes_api_key(self, mock_get):
        mock_get.return_value = _mock_response(SEARCH_RESPONSE)
        with patch("src.services.usda.os.getenv", return_value="TEST_KEY"):
            search_foods("egg")
        call_params = mock_get.call_args.kwargs["params"]
        assert call_params["api_key"] == "TEST_KEY"

    @patch("src.services.usda.requests.get")
    def test_raises_on_http_error(self, mock_get):
        from requests import HTTPError
        mock_get.return_value = _mock_response({}, status_code=429)
        with pytest.raises(HTTPError):
            search_foods("egg")


class TestGetFoodDetail:
    @patch("src.services.usda.requests.get")
    def test_parses_foundation_nutrients(self, mock_get):
        mock_get.return_value = _mock_response(FOOD_DETAIL_FOUNDATION)
        detail = get_food_detail(748967)

        n = detail["nutrients_per_100g"]
        assert n["energy_kcal"] == pytest.approx(143.0)
        assert n["protein_g"] == pytest.approx(12.6)
        assert n["fat_g"] == pytest.approx(9.51)

    @patch("src.services.usda.requests.get")
    def test_parses_branded_nutrients(self, mock_get):
        mock_get.return_value = _mock_response(FOOD_DETAIL_BRANDED)
        detail = get_food_detail(999999)

        n = detail["nutrients_per_100g"]
        assert n["energy_kcal"] == pytest.approx(100.0)
        assert n["protein_g"] == pytest.approx(17.0)

    @patch("src.services.usda.requests.get")
    def test_portions_exclude_tablespoon(self, mock_get):
        mock_get.return_value = _mock_response(FOOD_DETAIL_FOUNDATION)
        detail = get_food_detail(748967)

        labels = [p["label"] for p in detail["portions"]]
        assert not any("tablespoon" in l.lower() for l in labels)

    @patch("src.services.usda.requests.get")
    def test_portions_include_large_egg(self, mock_get):
        mock_get.return_value = _mock_response(FOOD_DETAIL_FOUNDATION)
        detail = get_food_detail(748967)

        grams = [p["grams"] for p in detail["portions"]]
        assert 50 in grams

    @patch("src.services.usda.requests.get")
    def test_branded_serving_size_as_portion(self, mock_get):
        mock_get.return_value = _mock_response(FOOD_DETAIL_BRANDED)
        detail = get_food_detail(999999)

        assert len(detail["portions"]) == 1
        assert detail["portions"][0]["grams"] == pytest.approx(150.0)

    @patch("src.services.usda.requests.get")
    def test_raises_on_404(self, mock_get):
        from requests import HTTPError
        mock_get.return_value = _mock_response({}, status_code=404)
        with pytest.raises(HTTPError):
            get_food_detail(000000)

    @patch("src.services.usda.requests.get")
    def test_missing_api_key_raises(self, mock_get):
        with patch("src.services.usda.os.getenv", return_value=""):
            with pytest.raises(EnvironmentError):
                get_food_detail(748967)
