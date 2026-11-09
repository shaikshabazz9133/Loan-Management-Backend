"""Distance helpers for the 2 km agent radius.

Distances are computed in Python (haversine) - agent and open-request counts are small, and it keeps the
logic identical to the frontend's distanceKm(). Points are {"lat": .., "lng": ..} or GeoJSON Points.
"""
from math import asin, cos, radians, sin, sqrt
from typing import Any

_EARTH_RADIUS_KM = 6371.0


def to_lat_lng(point: dict[str, Any]) -> tuple[float, float]:
    if "coordinates" in point:  # GeoJSON stores [lng, lat]
        lng, lat = point["coordinates"]
        return lat, lng
    return point["lat"], point["lng"]


def distance_km(a: dict[str, Any], b: dict[str, Any]) -> float:
    lat1, lng1 = to_lat_lng(a)
    lat2, lng2 = to_lat_lng(b)
    d_lat, d_lng = radians(lat2 - lat1), radians(lng2 - lng1)
    h = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * asin(sqrt(h))
