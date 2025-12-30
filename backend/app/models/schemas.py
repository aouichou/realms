"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str = Field(description="Service status")
    app_name: str = Field(description="Application name")
    version: str = Field(description="Application version")
    environment: str = Field(description="Environment")
    timestamp: datetime = Field(description="Current timestamp")


class NarrateRequest(BaseModel):
    """Request model for DM narration"""
    message: str = Field(description="User message to the DM", min_length=1, max_length=1000)
    session_id: Optional[str] = Field(default=None, description="Session ID for context")
    character_id: Optional[str] = Field(default=None, description="Character ID for context")


class NarrateResponse(BaseModel):
    """Response model for DM narration"""
    response: str = Field(description="DM response")
    session_id: str = Field(description="Session ID")
    tokens_used: int = Field(description="Number of tokens used")
    timestamp: datetime = Field(description="Response timestamp")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
