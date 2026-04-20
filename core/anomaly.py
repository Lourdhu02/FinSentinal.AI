from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest


class AnomalyResult(BaseModel):
    anomaly_score: float
    z_score: float
    is_anomaly: bool


class AnomalyDetector:
    def score(self, value: float, historical_values: list[float]) -> AnomalyResult:
        if len(historical_values) < 3:
            return AnomalyResult(anomaly_score=0.0, z_score=0.0, is_anomaly=False)
        history = np.asarray(historical_values, dtype=float)
        mean = float(history.mean())
        std = float(history.std())
        z_score = 0.0 if std == 0.0 else (value - mean) / std
        model = IsolationForest(random_state=42, contamination=0.1)
        model.fit(history.reshape(-1, 1))
        decision = float(model.decision_function(np.asarray([[value]], dtype=float))[0])
        predicted = int(model.predict(np.asarray([[value]], dtype=float))[0])
        anomaly_score = 1.0 / (1.0 + math.exp(decision * 5.0))
        is_anomaly = predicted == -1 or abs(z_score) >= 3.0
        return AnomalyResult(
            anomaly_score=round(float(anomaly_score), 4),
            z_score=round(float(z_score), 4),
            is_anomaly=is_anomaly,
        )
