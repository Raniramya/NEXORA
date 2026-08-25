from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Any

import numpy as np
from sklearn.cluster import DBSCAN

EARTH_RADIUS_KM = 6371.0088


def haversine_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    lat_a, lon_a, lat_b, lon_b = map(radians, (latitude_a, longitude_a, latitude_b, longitude_b))
    delta_lat, delta_lon = lat_b - lat_a, lon_b - lon_a
    value = sin(delta_lat / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(value))


def asset_distances(origin_latitude: float, origin_longitude: float, assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for asset in assets:
        if asset.get("latitude") is None or asset.get("longitude") is None:
            continue
        rows.append({
            "machine_id": asset["machine_id"],
            "machine_name": asset["machine_name"],
            "distance_km": haversine_km(origin_latitude, origin_longitude, float(asset["latitude"]), float(asset["longitude"])),
        })
    return sorted(rows, key=lambda item: item["distance_km"])


def cluster_fault_hotspots(events: list[dict[str, Any]], *, epsilon_km: float = 1.0, minimum_assets: int = 2) -> dict[str, Any]:
    by_machine: dict[str, dict[str, Any]] = {}
    excluded_event_ids = []
    for event in events:
        if event.get("latitude") is None or event.get("longitude") is None:
            excluded_event_ids.append(event["event_id"])
            continue
        machine = by_machine.setdefault(event["machine_id"], {
            "machine_id": event["machine_id"], "machine_name": event["machine_name"],
            "latitude": float(event["latitude"]), "longitude": float(event["longitude"]), "event_ids": [],
        })
        machine["event_ids"].append(event["event_id"])
    assets = list(by_machine.values())
    if not assets:
        return {"clusters": [], "noise_assets": [], "included_asset_count": 0, "included_event_count": 0, "excluded_event_ids": excluded_event_ids, "warning": "Spatial clusters are descriptive patterns, not causal explanations."}
    coordinates = np.radians([[item["latitude"], item["longitude"]] for item in assets])
    labels = DBSCAN(eps=epsilon_km / EARTH_RADIUS_KM, min_samples=minimum_assets, metric="haversine", algorithm="ball_tree").fit_predict(coordinates)
    clusters = []
    noise = []
    for label in sorted(set(labels)):
        members = [asset for asset, assigned in zip(assets, labels) if assigned == label]
        if label == -1:
            noise = [{"machine_id": item["machine_id"], "machine_name": item["machine_name"], "event_ids": item["event_ids"]} for item in members]
            continue
        clusters.append({
            "cluster_id": int(label),
            "centroid": {"latitude": float(np.mean([item["latitude"] for item in members])), "longitude": float(np.mean([item["longitude"] for item in members]))},
            "machine_ids": [item["machine_id"] for item in members],
            "machine_names": [item["machine_name"] for item in members],
            "event_ids": [event_id for item in members for event_id in item["event_ids"]],
            "asset_count": len(members),
            "fault_event_count": sum(len(item["event_ids"]) for item in members),
        })
    return {
        "clusters": clusters,
        "noise_assets": noise,
        "included_asset_count": len(assets),
        "included_event_count": sum(len(item["event_ids"]) for item in assets),
        "excluded_event_ids": excluded_event_ids,
        "warning": "Spatial clusters are descriptive patterns, not causal explanations.",
    }
