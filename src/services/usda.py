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
        raise EnvironmentError("USDA_API_KEY is not set in .env.")
    return key


def search_foods(query: str, page_size: int = 20) -> list[dict[str, Any]]:
    """Search foods and return deduplicated candidates with {fdc_id, description, data_type}."""
    resp = requests.get(
        f"{_BASE_URL}/foods/search",
        params={
            "query": query,
            "pageSize": page_size,
            "dataType": "Foundation,SR Legacy,Branded",
            "api_key": _api_key(),
        },
        timeout=10,
    )
    resp.raise_for_status()
    foods = resp.json().get("foods", [])

    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for f in foods:
        desc = f["description"].strip()
        if desc not in seen:
            seen.add(desc)
            results.append({
                "fdc_id": f["fdcId"],
                "description": desc,
                "data_type": f.get("dataType", ""),
            })
    return results


def get_food_detail(fdc_id: int) -> dict[str, Any]:
    """Return nutrients per 100g and serving size info for a given fdcId."""
    resp = requests.get(
        f"{_BASE_URL}/food/{fdc_id}",
        params={"api_key": _api_key()},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    nutrients: dict[str, float] = {}
    for n in data.get("foodNutrients", []):
        nutrient_id = (n.get("nutrient") or {}).get("id") or n.get("nutrientId")
        amount = n.get("amount") if n.get("amount") is not None else n.get("value") or 0.0
        key = _NUTRIENT_ID_MAP.get(int(nutrient_id)) if nutrient_id else None
        if key and amount:
            nutrients[key] = round(float(amount), 4)

    # Serving size: Branded foods expose servingSize directly;
    # Foundation/SR Legacy expose foodPortions list.
    serving_g: float | None = None
    serving_label: str = ""
    if data.get("servingSize"):
        unit = data.get("servingSizeUnit", "g").lower()
        size = float(data["servingSize"])
        serving_g = size * 29.5735 if unit == "ml" else size
        serving_label = f"1 serving ({serving_g:.0f}g)"
    elif data.get("foodPortions"):
        portion = data["foodPortions"][0]
        serving_g = float(portion.get("gramWeight", 0)) or None
        if serving_g:
            desc = portion.get("modifier") or portion.get("measureUnit", {}).get("name", "serving")
            amount_val = portion.get("amount", 1)
            serving_label = f"{amount_val} {desc} ({serving_g:.0f}g)"

    return {
        "nutrients_per_100g": nutrients,
        "serving_g": serving_g,
        "serving_label": serving_label,
    }


def get_nutrients_per_100g(fdc_id: int) -> dict[str, float]:
    return get_food_detail(fdc_id)["nutrients_per_100g"]


def scale_nutrients(nutrients_per_100g: dict[str, float], grams: float) -> dict[str, float]:
    """Scale per-100g nutrients to actual intake grams."""
    factor = grams / 100
    return {k: round(v * factor, 4) for k, v in nutrients_per_100g.items()}
