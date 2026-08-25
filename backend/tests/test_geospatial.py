from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.geospatial import cluster_fault_hotspots, haversine_km


def test_haversine_uses_great_circle_distance() -> None:
    assert haversine_km(0, 0, 0, 0) == 0
    assert abs(haversine_km(0, 0, 0, 1) - 111.195) < 0.01


def test_hotspots_count_unique_assets_and_retain_event_provenance() -> None:
    events = [
        {"event_id": "e1", "machine_id": "m1", "machine_name": "A", "latitude": 12.9716, "longitude": 77.5946},
        {"event_id": "e2", "machine_id": "m1", "machine_name": "A", "latitude": 12.9716, "longitude": 77.5946},
        {"event_id": "e3", "machine_id": "m2", "machine_name": "B", "latitude": 12.9720, "longitude": 77.5950},
        {"event_id": "e4", "machine_id": "m3", "machine_name": "C", "latitude": 13.10, "longitude": 77.70},
    ]
    result = cluster_fault_hotspots(events, epsilon_km=1, minimum_assets=2)
    assert result["clusters"][0]["machine_ids"] == ["m1", "m2"]
    assert result["clusters"][0]["event_ids"] == ["e1", "e2", "e3"]
    assert result["clusters"][0]["fault_event_count"] == 3
    assert result["noise_assets"][0]["machine_id"] == "m3"
    assert "not causal" in result["warning"]


def test_geospatial_api_persists_distances_and_hotspots() -> None:
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
    try:
        machines = []
        for index, coordinates in enumerate(((12.9716, 77.5946), (12.9720, 77.5950), (None, None))):
            payload = {"name": f"Asset {index}", "asset_type": "motor", "status": "active"}
            if coordinates[0] is not None:
                payload.update({"latitude": coordinates[0], "longitude": coordinates[1]})
            response = client.post("/api/machines", json=payload)
            assert response.status_code == 201
            machines.append(response.json())
        now = datetime.now(timezone.utc).isoformat()
        for machine in machines[:2]:
            response = client.post(f"/api/machines/{machine['id']}/fault-events", json={
                "fault_type": "bearing_fault", "severity": "warning", "observed_at": now,
            })
            assert response.status_code == 201

        assets = client.get("/api/geo/assets")
        assert assets.status_code == 200
        assert len(assets.json()) == 2
        distances = client.post("/api/geo/distances", json={"origin_latitude": 12.9716, "origin_longitude": 77.5946})
        assert distances.status_code == 201
        assert distances.json()["result"]["excluded_asset_count"] == 1
        hotspots = client.post("/api/geo/hotspots", json={"epsilon_km": 1, "minimum_assets": 2, "lookback_days": 1})
        assert hotspots.status_code == 201
        assert hotspots.json()["result"]["clusters"][0]["asset_count"] == 2
    finally:
        app.dependency_overrides.clear()
