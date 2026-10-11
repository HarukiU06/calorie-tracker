"""Tests for USDA API client functions (HTTP calls mocked)."""

from unittest.mock import MagicMock, patch

import pytest

from src.services.usda import USDAError, get_food_detail, search_foods


@pytest.fixture(autouse=True)
def _api_key_env(monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "DUMMY_KEY")


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
        assert mock_get.call_args.kwargs["headers"]["X-Api-Key"] == "TEST_KEY"
        assert "api_key" not in mock_get.call_args.kwargs["params"]

    @patch("src.services.usda.requests.get")
    def test_error_message_does_not_leak_api_key(self, mock_get):
        from requests import HTTPError
        mock = _mock_response({}, status_code=403)
        mock.raise_for_status.side_effect = HTTPError(
            "403 Client Error for url: https://api.nal.usda.gov/?api_key=SECRET", response=mock
        )
        mock_get.return_value = mock
        with pytest.raises(USDAError) as exc:
            search_foods("egg")
        assert "SECRET" not in str(exc.value)
        assert exc.value.__cause__ is None

    @patch("src.services.usda.requests.get")
    def test_query_is_truncated(self, mock_get):
        mock_get.return_value = _mock_response(SEARCH_RESPONSE)
        search_foods("a" * 1000)
        assert len(mock_get.call_args.kwargs["params"]["query"]) == 100

    @patch("src.services.usda.requests.get")
    def test_skips_malformed_results(self, mock_get):
        mock_get.return_value = _mock_response(
            {"foods": [{"fdcId": "x", "description": "Bad"}, {"description": "No id"}]}
        )
        assert search_foods("egg") == []

    @patch("src.services.usda.requests.get")
    def test_raises_on_http_error(self, mock_get):
        mock_get.return_value = _mock_response({}, status_code=429)
        with pytest.raises(USDAError):
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
        mock_get.return_value = _mock_response({}, status_code=404)
        with pytest.raises(USDAError):
            get_food_detail(1)

    def test_rejects_non_positive_fdc_id(self):
        with pytest.raises(ValueError):
            get_food_detail(0)

    @patch("src.services.usda.requests.get")
    def test_ignores_non_finite_nutrients(self, mock_get):
        mock_get.return_value = _mock_response(
            {"foodNutrients": [{"nutrient": {"id": 1008}, "amount": "nan"},
                               {"nutrient": {"id": 1003}, "amount": "inf"}]}
        )
        assert get_food_detail(1)["nutrients_per_100g"] == {}

    @patch("src.services.usda.requests.get")
    def test_missing_api_key_raises(self, mock_get):
        with patch("src.services.usda.os.getenv", return_value=""):
            with pytest.raises(EnvironmentError):
                get_food_detail(748967)
