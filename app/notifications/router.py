"""M11 Notifications  |  Owner: Shahid  |  4 APIs
In-app inbox; SMS/e-mail/push are sent by background workers on domain events.

Endpoints to implement (thin handlers -> service layer):
    GET    /api/v1/notifications                               [Any]  (reusable)
        Paginated notification inbox
    GET    /api/v1/notifications/unread-count                  [Any]  (reusable)
        Badge count for the bell icon
    PATCH  /api/v1/notifications/{id}/read                     [Any]  (reusable)
        Mark one as read
    PATCH  /api/v1/notifications/read-all                      [Any]  (reusable)
        Mark all as read
"""
from fastapi import APIRouter

router = APIRouter(tags=["Notifications"])
