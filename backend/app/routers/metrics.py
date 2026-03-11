"""
Metrics endpoint for Prometheus scraping
"""

from fastapi import APIRouter, Depends, Response

from app.db.models import User
from app.middleware.auth import get_current_active_user
from app.observability.metrics import metrics

router = APIRouter(tags=["monitoring"])


@router.get("/metrics")
async def get_metrics(current_user: User = Depends(get_current_active_user)):
    """
    Prometheus metrics endpoint

    Returns metrics in Prometheus text format for scraping
    """
    metrics_data = metrics.generate_metrics()
    return Response(content=metrics_data, media_type="text/plain; charset=utf-8")
