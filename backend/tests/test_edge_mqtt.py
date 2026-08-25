import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.core.config import PROJECT_ROOT, Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.maintenance import EdgeIngestionReceipt, SignalWindow
from app.edge.mqtt_bridge import decode_message


def test_mqtt_topic_and_payload_decode_into_authoritative_contract() -> None:
    payload = {"message_id": "device-boot-1", "signal_window": {"recorded_at": datetime.now(timezone.utc).isoformat(), "sample_rate_hz": 1000, "samples": [0, 1, 0, -1, 0, 1, 0, -1]}}
    envelope = decode_message("nexora/machines/machine-1/signal-windows", json.dumps(payload).encode())
    assert envelope.machine_id == "machine-1"
    assert envelope.signal_window.samples == payload["signal_window"]["samples"]


def test_standalone_bridge_settings_use_repository_environment_file() -> None:
    settings = Settings()
    assert Settings.model_config["env_file"] == PROJECT_ROOT / ".env"
    assert settings.mqtt_port > 0
    assert settings.api_url.startswith(("http://", "https://"))


def test_edge_ingestion_is_token_protected_and_idempotent() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_db():
        db = session_factory()
        try: yield db
        finally: db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    settings = get_settings()
    previous_token = settings.edge_ingest_token
    settings.edge_ingest_token = "edge-secret"
    try:
        machine = client.post("/api/machines", json={"name": "MQTT Motor"}).json()
        payload = {"message_id": "device-boot-1", "machine_id": machine["id"], "signal_window": {"recorded_at": datetime.now(timezone.utc).isoformat(), "sample_rate_hz": 1000, "samples": [0, 1, 0, -1, 0, 1, 0, -1]}}
        assert client.post("/api/edge/signal-windows", json=payload).status_code == 401
        first = client.post("/api/edge/signal-windows", json=payload, headers={"X-Nexora-Edge-Token": "edge-secret"})
        second = client.post("/api/edge/signal-windows", json=payload, headers={"X-Nexora-Edge-Token": "edge-secret"})
        assert first.status_code == 201 and second.status_code == 201
        assert first.json()["id"] == second.json()["id"]
        assert first.json()["source"] == "esp32_mqtt"
        db = session_factory()
        assert db.query(SignalWindow).count() == 1
        assert db.query(EdgeIngestionReceipt).count() == 1
        db.close()
        conflict = {**payload, "machine_id": client.post("/api/machines", json={"name": "Other Motor"}).json()["id"]}
        assert client.post("/api/edge/signal-windows", json=conflict, headers={"X-Nexora-Edge-Token": "edge-secret"}).status_code == 409
    finally:
        settings.edge_ingest_token = previous_token
        app.dependency_overrides.clear()
