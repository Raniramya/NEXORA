from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.db.base import Base
from app.db.session import get_db
from app.main import app


def test_machine_telemetry_fault_and_maintenance_workflow():
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
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        machine = client.post("/api/machines", json={"name": "Motor 01", "latitude": 12.97, "longitude": 77.59})
        assert machine.status_code == 201
        machine_id = machine.json()["id"]

        incomplete_location = client.post("/api/machines", json={"name": "Motor 02", "latitude": 12.97})
        assert incomplete_location.status_code == 422

        reading = client.post(f"/api/machines/{machine_id}/readings", json={"recorded_at": timestamp, "vibration_rms": 5.7, "temperature": 48, "current": 2.1, "rpm": 1450})
        assert reading.status_code == 201
        assert reading.json()["machine_id"] == machine_id

        empty_reading = client.post(f"/api/machines/{machine_id}/readings", json={"recorded_at": timestamp})
        assert empty_reading.status_code == 422

        missing_machine = client.post(f"/api/machines/unknown/readings", json={"recorded_at": timestamp, "rpm": 1400})
        assert missing_machine.status_code == 404

        fault = client.post(f"/api/machines/{machine_id}/fault-events", json={"fault_type": "imbalance", "severity": "high", "confidence": 0.84, "observed_at": timestamp})
        assert fault.status_code == 201

        action = client.post(f"/api/machines/{machine_id}/maintenance-actions", json={"action_type": "correct_imbalance", "predicted_benefit": 2.4})
        assert action.status_code == 201
        assert action.json()["status"] == "planned"

        assert len(client.get(f"/api/machines/{machine_id}/readings").json()) == 1
        assert len(client.get(f"/api/machines/{machine_id}/fault-events").json()) == 1
        assert len(client.get(f"/api/machines/{machine_id}/maintenance-actions").json()) == 1
    finally:
        app.dependency_overrides.clear()
