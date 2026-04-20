import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

_BASE_URL = "https://api.nal.usda.gov/fdc/v1"
_NUTRIENT_ID_MAP: dict[int, str] = {
    1008: "energy_kcal",
    1003: "protein_g",
    1004: "fat_g",
    1005: "carb_g",
    1079: "fiber_g",
    1093: "sodium_mg",
    1087: "calcium_mg",
    1089: "iron_mg",
    1090: "magnesium_mg",
    1095: "zinc_mg",
    1162: "vitamin_c_mg",
    1114: "vitamin_d_ug",
    1178: "vitamin_b12_ug",
    1177: "folate_ug",
    1106: "vitamin_a_ug",
    1092: "potassium_mg",
}


def _api_key() -> str:
    key = os.getenv("USDA_API_KEY", "")
    if not key:
        raise EnvironmentError("USDA_API_KEY が .env に設定されていません。")
    return key


def search_foods(query: str, page_size: int = 20) -> list[dict[str, Any]]:
    """食材名で検索し、候補リストを返す。各要素は {fdc_id, description} を含む。"""
    resp = requests.get(
        f"{_BASE_URL}/foods/search",
        params={
            "query": query,
            "pageSize": page_size,
            "dataType": "Foundation,SR Legacy",
            "api_key": _api_key(),
        },
        timeout=10,
    )
    resp.raise_for_status()
    foods = resp.json().get("foods", [])
    return [{"fdc_id": f["fdcId"], "description": f["description"]} for f in foods]


def get_nutrients_per_100g(fdc_id: int) -> dict[str, float]:
    """指定した fdcId の食材の栄養素を per 100g で返す。キーは snake_case + 単位サフィックス。"""
    resp = requests.get(
        f"{_BASE_URL}/food/{fdc_id}",
        params={"api_key": _api_key()},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    nutrients: dict[str, float] = {}
    for n in data.get("foodNutrients", []):
        nutrient_id = n.get("nutrient", {}).get("id") or n.get("nutrientId")
        amount = n.get("amount") or n.get("value") or 0.0
        key = _NUTRIENT_ID_MAP.get(nutrient_id)
        if key:
            nutrients[key] = round(float(amount), 4)

    return nutrients


def scale_nutrients(nutrients_per_100g: dict[str, float], grams: float) -> dict[str, float]:
    """per 100g の栄養素を実際の摂取グラム数でスケールする。"""
    factor = grams / 100
    return {k: round(v * factor, 4) for k, v in nutrients_per_100g.items()}
