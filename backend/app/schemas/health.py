"""
Pydantic models for request/response validation
"""

from datetime import datetime

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Health check response model"""

    status: str = Field(description="Service status")
    app_name: str = Field(description="Application name")
    version: str = Field(description="Application version")
    environment: str = Field(description="Environment")
    timestamp: datetime = Field(description="Current timestamp")
