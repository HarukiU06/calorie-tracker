import json
from pathlib import Path

from src.db.models import Profile

_DRI_PATH = Path(__file__).parent.parent / "data" / "dri.json"


def _load_raw() -> dict:
    with open(_DRI_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_dri(profile: Profile) -> dict[str, float]:
    """プロフィールに応じた1日の栄養素推奨量を返す。"""
    raw = _load_raw()
    dri: dict[str, float] = dict(raw["default"])

    if profile.gender == "female":
        dri.update(raw["overrides"]["female"])

    if profile.age >= 51:
        dri.update(raw["overrides"]["age_51_plus"])

    return dri
