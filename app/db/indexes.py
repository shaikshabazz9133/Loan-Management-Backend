"""All index definitions in one place (run on startup / migration).

users:            {email: 1} unique, {mobile: 1} unique, {role: 1, active: 1}, {location: "2dsphere"} (agents)
applications:     {customer_id: 1, created_at: -1}, {agent_id: 1, status: 1}, {status: 1, created_at: -1},
                  {location: "2dsphere"}, {app_no: 1} unique, {"declined_by.agent_id": 1}
application_events: {application_id: 1, at: 1}
documents:        {application_id: 1, type: 1}
notifications:    {user_id: 1, read: 1, created_at: -1}
disbursements:    {application_id: 1} unique, {utr: 1} unique sparse, {status: 1}
audit_logs:       {entity: 1, entity_id: 1, at: -1}, {actor_id: 1, at: -1}
sessions:         {expires_at: 1} TTL, otp_codes: {expires_at: 1} TTL, idempotency_keys: {created_at: 1} TTL 24h
"""
