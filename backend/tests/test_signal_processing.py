from datetime import datetime, timezone
from math import pi, sin

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.core.config import get_settings
from app.services.signal_processing import FEATURE_EXTRACTOR_VERSION, extract_signal_features


def _sine_wave(frequency: float, sample_rate: float, count: int) -> list[float]:
    return [sin(2 * pi * frequency * index / sample_rate) for index in range(count)]


def test_signal_features_are_numerical_and_deterministic():
    samples = _sine_wave(50, 1000, 1000)
    first = extract_signal_features(samples, 1000)
    second = extract_signal_features(samples, 1000)
    assert first == second
    assert abs(first.features["dominant_frequency_hz"] - 50) < 0.001
    assert abs(first.features["rms"] - (2 ** -0.5)) < 0.001
    band_total = sum(first.features[name] for name in ("low_band_energy_fraction", "mid_band_energy_fraction", "high_band_energy_fraction"))
    assert abs(band_total - 1) < 0.001
    assert first.features["second_harmonic_ratio"] < 0.001
    assert first.configuration["extractor_version"] == FEATURE_EXTRACTOR_VERSION


def test_signal_window_api_persists_raw_and_derived_evidence():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    settings = get_settings()
    previous_token = settings.edge_ingest_token
    try:
        machine = client.post("/api/machines", json={"name": "Signal Motor"}).json()
        payload = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "sample_rate_hz": 1000,
            "channel": "vibration_x",
            "unit": "g",
            "device_id": "esp32-lab-01",
            "samples": _sine_wave(50, 1000, 1000),
        }
        settings.edge_ingest_token = "test-edge-token"
        unauthorized = client.post(f"/api/machines/{machine['id']}/signal-windows", json=payload)
        assert unauthorized.status_code == 401
        response = client.post(f"/api/machines/{machine['id']}/signal-windows", json=payload, headers={"X-Nexora-Edge-Token": "test-edge-token"})
        assert response.status_code == 201
        body = response.json()
        assert body["samples"] == payload["samples"]
        assert body["feature_set"]["signal_window_id"] == body["id"]
        assert abs(body["feature_set"]["features"]["dominant_frequency_hz"] - 50) < 0.001

        listed = client.get(f"/api/machines/{machine['id']}/signal-windows")
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == body["id"]
    finally:
        settings.edge_ingest_token = previous_token
        app.dependency_overrides.clear()
