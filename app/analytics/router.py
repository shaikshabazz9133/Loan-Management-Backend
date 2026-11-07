"""M13 Dashboards & Analytics  |  7 APIs
Role dashboards (aggregation pipelines, Redis cached), charts and exports.

Endpoints to implement (thin handlers -> service layer):
    GET    /api/v1/dashboard/customer                          [Customer]
        Customer stat cards and latest application
    GET    /api/v1/dashboard/agent                             [Agent]
        Agent stat cards and to-do list
    GET    /api/v1/dashboard/manager                           [Manager]
        Manager stat cards and action alerts
    GET    /api/v1/reports/applications/monthly                [Manager]
        Monthly applications chart
    GET    /api/v1/reports/applications/outcomes               [Manager]
        Approved vs rejected vs in-progress
    GET    /api/v1/reports/agents/performance                  [Manager]
        Agent performance chart
    GET    /api/v1/reports/export                              [Manager]
        CSV/XLSX export (async job, download link)
"""
from fastapi import APIRouter

router = APIRouter(tags=["Dashboards & Analytics"])
