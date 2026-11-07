"""Idempotency-Key support for POST /applications and POST /applications/{id}/disburse.
Stores (key, user, request hash) -> response in Mongo with a 24 h TTL index.
"""
