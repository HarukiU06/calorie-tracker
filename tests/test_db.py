"""Tests for DB models and session management using in-memory SQLite."""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import ActivityLevel, Base, Goal, MealEntry, MealType, Profile


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


class TestProfileSingleton:
    def test_create_and_retrieve(self, session):
        p = Profile(
            id=1,
            gender="male",
            age=28,
            height_cm=178.0,
            weight_kg=72.0,
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
            goal=Goal.MAINTAIN,
        )
        session.add(p)
        session.commit()

        retrieved = session.get(Profile, 1)
        assert retrieved is not None
        assert retrieved.gender == "male"
        assert retrieved.age == 28

    def test_upsert_updates_existing(self, session):
        p = Profile(id=1, gender="male", age=25, height_cm=170, weight_kg=65,
                    activity_level=ActivityLevel.SEDENTARY, goal=Goal.MAINTAIN)
        session.add(p)
        session.commit()

        p.age = 26
        p.weight_kg = 66.5
        session.commit()

        updated = session.get(Profile, 1)
        assert updated.age == 26
        assert updated.weight_kg == 66.5

    def test_body_fat_nullable(self, session):
        p = Profile(id=1, gender="female", age=30, height_cm=165, weight_kg=58,
                    activity_level=ActivityLevel.LIGHTLY_ACTIVE, goal=Goal.LOSE,
                    body_fat_pct=None)
        session.add(p)
        session.commit()

        assert session.get(Profile, 1).body_fat_pct is None

    def test_body_fat_stored(self, session):
        p = Profile(id=1, gender="male", age=35, height_cm=180, weight_kg=80,
                    activity_level=ActivityLevel.VERY_ACTIVE, goal=Goal.GAIN,
                    body_fat_pct=18.5)
        session.add(p)
        session.commit()

        assert session.get(Profile, 1).body_fat_pct == pytest.approx(18.5)


class TestMealEntry:
    def test_create_entry(self, session):
        entry = MealEntry(
            date=datetime.date(2024, 1, 15),
            meal_type=MealType.BREAKFAST,
            food_name="Egg, whole, raw",
            grams=50.0,
            nutrients={"energy_kcal": 71.5, "protein_g": 6.3, "fat_g": 4.8},
        )
        session.add(entry)
        session.commit()

        retrieved = session.get(MealEntry, entry.id)
        assert retrieved.food_name == "Egg, whole, raw"
        assert retrieved.grams == 50.0

    def test_nutrients_json_roundtrip(self, session):
        nutrients = {
            "energy_kcal": 165.0,
            "protein_g": 31.0,
            "fat_g": 3.6,
            "carb_g": 0.0,
            "vitamin_b12_ug": 0.34,
        }
        entry = MealEntry(
            date=datetime.date.today(),
            meal_type=MealType.LUNCH,
            food_name="Chicken breast",
            grams=100.0,
            nutrients=nutrients,
        )
        session.add(entry)
        session.commit()
        session.expire(entry)

        retrieved = session.get(MealEntry, entry.id)
        assert retrieved.nutrients == nutrients

    def test_autoincrement_id(self, session):
        for food in ["Apple", "Banana", "Orange"]:
            session.add(MealEntry(
                date=datetime.date.today(), meal_type=MealType.SNACK,
                food_name=food, grams=100.0, nutrients={},
            ))
        session.commit()

        entries = session.query(MealEntry).order_by(MealEntry.id).all()
        ids = [e.id for e in entries]
        assert ids == sorted(ids)
        assert len(set(ids)) == 3

    def test_filter_by_date(self, session):
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        session.add(MealEntry(date=today, meal_type=MealType.BREAKFAST,
                               food_name="Oats", grams=80.0, nutrients={}))
        session.add(MealEntry(date=yesterday, meal_type=MealType.DINNER,
                               food_name="Rice", grams=150.0, nutrients={}))
        session.commit()

        today_entries = session.query(MealEntry).filter(MealEntry.date == today).all()
        assert len(today_entries) == 1
        assert today_entries[0].food_name == "Oats"

    def test_delete_entry(self, session):
        entry = MealEntry(
            date=datetime.date.today(), meal_type=MealType.SNACK,
            food_name="Banana", grams=120.0, nutrients={"energy_kcal": 107.0},
        )
        session.add(entry)
        session.commit()
        entry_id = entry.id

        session.delete(entry)
        session.commit()

        assert session.get(MealEntry, entry_id) is None

    def test_empty_nutrients_default(self, session):
        entry = MealEntry(
            date=datetime.date.today(), meal_type=MealType.SNACK,
            food_name="Water", grams=250.0,
        )
        session.add(entry)
        session.commit()
        session.expire(entry)

        assert session.get(MealEntry, entry.id).nutrients == {}
