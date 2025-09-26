"""Model training and inference helpers."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Mapping, TYPE_CHECKING

import numpy as np
from sklearn.linear_model import LinearRegression

from .database import fetch_museum_city_rows

if TYPE_CHECKING:
    import pandas as pd

MODEL_FILE = Path(__file__).parent.parent / "models" / "visitors_population_linreg.json"


@dataclass
class TrainingRow:
    museum_name: str
    country: str
    city: str
    visitors: float
    population: float


def _ensure_model_dir() -> None:
    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_training_rows(min_visitors: int = 500_000) -> List[TrainingRow]:
    rows = fetch_museum_city_rows(min_visitors)
    return [
        TrainingRow(
            museum_name=str(row["museum_name"]),
            country=str(row["country"]),
            city=str(row["city"]),
            visitors=float(row["visitors"]),
            population=float(row["population"]),
        )
        for row in rows
    ]


def train_model(rows: Iterable[TrainingRow]) -> tuple[LinearRegression, Mapping[str, float]]:
    rows = list(rows)
    if not rows:
        raise ValueError("No training data available. Ensure ETL has populated the database.")

    populations = np.array([[row.population] for row in rows], dtype=float)
    visitors = np.array([row.visitors for row in rows], dtype=float)

    log_pop = np.log1p(populations)
    log_visitors = np.log1p(visitors)

    model = LinearRegression()
    model.fit(log_pop, log_visitors)

    predicted_log = model.predict(log_pop)
    predicted = np.expm1(predicted_log)
    residuals = visitors - predicted

    mae = float(np.mean(np.abs(residuals)))
    rmse = float(math.sqrt(np.mean(residuals**2)))
    ss_tot = float(np.sum((visitors - np.mean(visitors)) ** 2))
    ss_res = float(np.sum(residuals**2))
    r2 = 1 - ss_res / ss_tot if ss_tot else float("nan")

    metrics = {
        "r2": r2,
        "mae": mae,
        "rmse": rmse,
        "n_rows": float(len(rows)),
    }
    return model, metrics


def persist_model(model: LinearRegression, metrics: Mapping[str, float], rows: Iterable[TrainingRow]) -> None:
    _ensure_model_dir()
    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": {
            "coef_log": model.coef_.tolist(),
            "intercept_log": float(model.intercept_),
        },
        "training_metrics": dict(metrics),
        "training_sample_preview": [
            {
                "museum_name": row.museum_name,
                "country": row.country,
                "city": row.city,
                "visitors": row.visitors,
                "population": row.population,
            }
            for row in list(rows)[:5]
        ],
        "feature": "log1p(population)",
        "target": "log1p(visitors)",
    }
    MODEL_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def train_and_persist(min_visitors: int = 500_000) -> Mapping[str, float]:
    rows = load_training_rows(min_visitors)
    model, metrics = train_model(rows)
    persist_model(model, metrics, rows)
    return metrics


def build_features_frame(min_visitors: int = 100_000) -> "pd.DataFrame":
    import pandas as pd

    records = fetch_museum_city_rows(min_visitors)
    if not records:
        return pd.DataFrame(
            columns=[
                "museum_name",
                "country",
                "city",
                "visitors",
                "population",
                "log_visitors",
                "log_population",
                "visitors_per_1000",
            ]
        )

    frame = pd.DataFrame(records)
    frame["visitors"] = frame["visitors"].astype(float)
    frame["population"] = frame["population"].astype(float)
    frame["log_visitors"] = frame["visitors"].apply(lambda x: math.log1p(x))
    frame["log_population"] = frame["population"].apply(lambda x: math.log1p(x))
    frame["visitors_per_1000"] = frame["visitors"] / (frame["population"] / 1_000)
    return frame


def load_model_artifact() -> Mapping[str, object]:
    if not MODEL_FILE.exists():
        raise FileNotFoundError("Model artifact missing. Run training first.")
    return json.loads(MODEL_FILE.read_text(encoding="utf-8"))


def predict_from_population(population: int) -> float:
    if population <= 0:
        raise ValueError("Population must be positive.")
    artifact = load_model_artifact()
    model_data = artifact.get("model")
    if not model_data:
        raise ValueError("Model coefficients missing from artifact.")
    coef = float(model_data["coef_log"][0])
    intercept = float(model_data["intercept_log"])
    population_log = math.log1p(population)
    visitors_log = intercept + coef * population_log
    return float(math.expm1(visitors_log))


__all__ = [
    "MODEL_FILE",
    "TrainingRow",
    "build_features_frame",
    "load_model_artifact",
    "predict_from_population",
    "train_and_persist",
]

