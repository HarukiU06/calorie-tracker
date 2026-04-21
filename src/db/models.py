from __future__ import annotations

import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Float, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
