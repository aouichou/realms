"""
Metrics endpoint for Prometheus scraping
"""

from fastapi import APIRouter, Response

from app.observability.metrics import metrics

router = APIRouter(tags=["monitoring"])


@router.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint

    Returns metrics in Prometheus text format for scraping
    """
    metrics_data = metrics.generate_metrics()
    return Response(content=metrics_data, media_type="text/plain; charset=utf-8")
