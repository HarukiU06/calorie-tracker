from __future__ import annotations

import datetime
import math
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Float, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, validates


class Base(DeclarativeBase):
    pass


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(StrEnum):
    SEDENTARY = "sedentary"          # 1.2
    LIGHTLY_ACTIVE = "lightly_active"  # 1.375
    MODERATELY_ACTIVE = "moderately_active"  # 1.55
    VERY_ACTIVE = "very_active"      # 1.725
    EXTRA_ACTIVE = "extra_active"    # 1.9


class Goal(StrEnum):
    LOSE = "lose"
    MAINTAIN = "maintain"
    GAIN = "gain"


class MealType(StrEnum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


def _check_range(name: str, value: float, lo: float, hi: float) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f"{name} must be between {lo} and {hi}.")
    return value


def _check_choice(name: str, value: str, enum: type[StrEnum]) -> str:
    if value not in {e.value for e in enum}:
        raise ValueError(f"Invalid {name}.")
    return str(value)


class Profile(Base):
    """シングルトン想定 (id=1 のみ使用)"""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    body_fat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    activity_level: Mapped[str] = mapped_column(String(20), nullable=False, default=ActivityLevel.SEDENTARY)
    goal: Mapped[str] = mapped_column(String(10), nullable=False, default=Goal.MAINTAIN)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    @validates("gender")
    def _validate_gender(self, _key: str, value: str) -> str:
        return _check_choice("gender", value, Gender)

    @validates("activity_level")
    def _validate_activity_level(self, _key: str, value: str) -> str:
        return _check_choice("activity level", value, ActivityLevel)

    @validates("goal")
    def _validate_goal(self, _key: str, value: str) -> str:
        return _check_choice("goal", value, Goal)

    @validates("age")
    def _validate_age(self, _key: str, value: int) -> int:
        return int(_check_range("age", value, 10, 120))

    @validates("height_cm")
    def _validate_height(self, _key: str, value: float) -> float:
        return _check_range("height", value, 100, 250)

    @validates("weight_kg")
    def _validate_weight(self, _key: str, value: float) -> float:
        return _check_range("weight", value, 20, 300)

    @validates("body_fat_pct")
    def _validate_body_fat(self, _key: str, value: float | None) -> float | None:
        return None if value is None else _check_range("body fat", value, 0, 70)


class MealEntry(Base):
    """1食ごとの食事ログ"""

    __tablename__ = "meal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(String(10), nullable=False)
    food_name: Mapped[str] = mapped_column(String(200), nullable=False)
    grams: Mapped[float] = mapped_column(Float, nullable=False)
    # 栄養素は snake_case + 単位サフィックス形式の JSON blob
    # 例: {"energy_kcal": 165.0, "protein_g": 31.0, "fat_g": 3.6, "carb_g": 0.0}
    # USDA から per 100g で取得し、grams でスケール済みの値を保存する
    nutrients: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    @validates("meal_type")
    def _validate_meal_type(self, _key: str, value: str) -> str:
        return _check_choice("meal type", value, MealType)

    @validates("food_name")
    def _validate_food_name(self, _key: str, value: str) -> str:
        value = str(value).strip()
        if not value or len(value) > 200:
            raise ValueError("food_name must be 1-200 characters.")
        return value

    @validates("grams")
    def _validate_grams(self, _key: str, value: float) -> float:
        return _check_range("grams", value, 0.1, 5000)

    @validates("nutrients")
    def _validate_nutrients(self, _key: str, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("nutrients must be a dict.")
        for k, v in value.items():
            if (
                not isinstance(k, str)
                or isinstance(v, bool)
                or not isinstance(v, (int, float))
                or not math.isfinite(v)
            ):
                raise ValueError("nutrients must map names to finite numbers.")
        return value
