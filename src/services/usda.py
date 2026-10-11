import math
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


# Upper bounds for user/API-supplied values
MAX_QUERY_LENGTH = 100
MAX_PAGE_SIZE = 50
MAX_DESCRIPTION_LENGTH = 200


class USDAError(Exception):
    """Raised for USDA API failures; message is safe to show to users."""


class MissingAPIKeyError(USDAError, OSError):
    pass


def _api_key() -> str:
    key = os.getenv("USDA_API_KEY", "")
    if not key:
        raise MissingAPIKeyError("USDA_API_KEY is not set in .env.")
    return key


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    # The key goes in a header (not the query string) so it never appears in
    # request URLs, which end up in exception messages, logs and proxies.
    headers = {"X-Api-Key": _api_key()}
    try:
        resp = requests.get(
            f"{_BASE_URL}{path}",
            params=params,
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        status = getattr(e.response, "status_code", None)
        msg = f"USDA API request failed (HTTP {status})." if status else "USDA API request failed."
        raise USDAError(msg) from None
    except ValueError:
        raise USDAError("USDA API returned an invalid response.") from None
    if not isinstance(data, dict):
        raise USDAError("USDA API returned an invalid response.")
    return data


def _safe_float(value: Any) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    return f if math.isfinite(f) else 0.0


def search_foods(query: str, page_size: int = 20) -> list[dict[str, Any]]:
    """Search foods and return deduplicated candidates."""
    query = query.strip()[:MAX_QUERY_LENGTH]
    if not query:
        return []
    page_size = max(1, min(int(page_size), MAX_PAGE_SIZE))
    data = _get(
        "/foods/search",
        {
            "query": query,
            "pageSize": page_size,
            "dataType": "Foundation,SR Legacy,Branded",
        },
    )
    foods = data.get("foods") or []

    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for f in foods:
        try:
            fdc_id = int(f["fdcId"])
            desc = str(f["description"]).strip()[:MAX_DESCRIPTION_LENGTH]
        except (KeyError, TypeError, ValueError):
            continue
        if desc and desc not in seen:
            seen.add(desc)
            results.append({
                "fdc_id": fdc_id,
                "description": desc,
                "data_type": f.get("dataType", ""),
            })
    return results


def _extract_portions(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a list of {label, grams} portion options, prioritizing whole-item sizes."""
    portions: list[dict[str, Any]] = []

    # Foundation / SR Legacy — foodPortions list
    for p in data.get("foodPortions", []):
        gram_weight = _safe_float(p.get("gramWeight"))
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
        size = _safe_float(data["servingSize"])
        gram_weight = size * 29.5735 if unit == "ml" else size
        if gram_weight > 0:
            portions.append({"label": f"1 serving ({gram_weight:.0f}g)", "grams": gram_weight, "is_piece": False})

    # Sort: whole-item portions first, then by gram weight descending
    portions.sort(key=lambda p: (not p["is_piece"], -p["grams"]))
    return portions


def get_food_detail(fdc_id: int) -> dict[str, Any]:
    """Return nutrients per 100g and available portion options for a given fdcId."""
    fdc_id = int(fdc_id)
    if fdc_id <= 0:
        raise ValueError("fdc_id must be a positive integer.")
    data = _get(f"/food/{fdc_id}")

    nutrients: dict[str, float] = {}
    for n in data.get("foodNutrients", []):
        nutrient_id = (n.get("nutrient") or {}).get("id") or n.get("nutrientId")
        amount = n.get("amount") if n.get("amount") is not None else n.get("value") or 0.0
        try:
            key = _NUTRIENT_ID_MAP.get(int(nutrient_id)) if nutrient_id else None
        except (TypeError, ValueError):
            continue
        amount = _safe_float(amount)
        if key and amount > 0:
            nutrients[key] = round(amount, 4)

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
