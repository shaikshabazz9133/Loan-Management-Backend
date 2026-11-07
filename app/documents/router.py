"""M10 Documents  |  5 APIs
Direct-to-S3 uploads with presigned URLs, metadata, virus scan, secure download.

Endpoints to implement (thin handlers -> service layer):
    POST   /api/v1/documents/upload-url                        [Customer]  (reusable)
        Presigned PUT URL (type, size and MIME validated)
    POST   /api/v1/documents                                   [Customer]  (reusable)
        Confirm upload and save metadata; queues virus scan
    GET    /api/v1/applications/{id}/documents                 [Customer, Agent, Manager]  (reusable)
        List documents of an application
    GET    /api/v1/documents/{id}/download-url                 [Customer, Agent, Manager]  (reusable)
        Short-lived presigned GET URL
    DELETE /api/v1/documents/{id}                              [Customer]
        Remove a document before submission
"""
from fastapi import APIRouter

router = APIRouter(tags=["Documents"])
