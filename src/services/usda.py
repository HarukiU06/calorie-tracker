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

# Volumetric/non-piece units to deprioritize
_VOLUME_KEYWORDS = {"tbsp", "tsp", "tablespoon", "teaspoon", "cup", "ml", "fl", "oz", "slice", "pat"}

# Keywords that suggest a countable whole item
_PIECE_KEYWORDS = {"large", "medium", "small", "extra", "whole", "each", "piece", "item"}


def _api_key() -> str:
    key = os.getenv("USDA_API_KEY", "")
    if not key:
        raise EnvironmentError("USDA_API_KEY is not set in .env.")
    return key


def search_foods(query: str, page_size: int = 20) -> list[dict[str, Any]]:
    """Search foods and return deduplicated candidates."""
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


def _extract_portions(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a list of {label, grams} portion options, prioritizing whole-item sizes."""
    portions: list[dict[str, Any]] = []

    # Foundation / SR Legacy — foodPortions list
    for p in data.get("foodPortions", []):
        gram_weight = float(p.get("gramWeight") or 0)
        if gram_weight <= 0:
            continue
        modifier: str = (p.get("modifier") or "").lower()
        unit_name: str = (p.get("measureUnit", {}) or {}).get("name", "").lower()
        amount = p.get("amount", 1)
        combined = f"{modifier} {unit_name}".strip()

        # Skip volumetric measures
        if any(kw in combined for kw in _VOLUME_KEYWORDS):
            continue

        # Build label
        if modifier:
            label = f"{amount} {modifier} ({gram_weight:.0f}g)"
        elif unit_name and unit_name != "undetermined":
            label = f"{amount} {unit_name} ({gram_weight:.0f}g)"
        else:
            label = f"{amount} piece ({gram_weight:.0f}g)"

        is_piece = any(kw in combined for kw in _PIECE_KEYWORDS)
        portions.append({"label": label, "grams": gram_weight, "is_piece": is_piece})

    # Branded — single servingSize field
    if not portions and data.get("servingSize"):
        unit = (data.get("servingSizeUnit") or "g").lower()
        size = float(data["servingSize"])
        gram_weight = size * 29.5735 if unit == "ml" else size
        if gram_weight > 0:
            portions.append({"label": f"1 serving ({gram_weight:.0f}g)", "grams": gram_weight, "is_piece": False})

    # Sort: whole-item portions first, then by gram weight descending
    portions.sort(key=lambda p: (not p["is_piece"], -p["grams"]))
    return portions


def get_food_detail(fdc_id: int) -> dict[str, Any]:
    """Return nutrients per 100g and available portion options for a given fdcId."""
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

    portions = _extract_portions(data)

    return {
        "nutrients_per_100g": nutrients,
        "portions": portions,
    }


def get_nutrients_per_100g(fdc_id: int) -> dict[str, float]:
    return get_food_detail(fdc_id)["nutrients_per_100g"]


def scale_nutrients(nutrients_per_100g: dict[str, float], grams: float) -> dict[str, float]:
    """Scale per-100g nutrients to actual intake grams."""
    factor = grams / 100
    return {k: round(v * factor, 4) for k, v in nutrients_per_100g.items()}
