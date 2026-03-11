"""
Models and Providers Router
API endpoints for managing AI provider models and configurations
"""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.models import User
from app.middleware.auth import get_current_active_user
from app.observability.logger import get_logger
from app.services.model_discovery_service import get_model_discovery_service
from app.services.provider_init import get_provider_status
from app.services.provider_selector import provider_selector

logger = get_logger(__name__)

router = APIRouter(prefix="/api/models", tags=["models"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================


class ProviderModelsResponse(BaseModel):
    """Response model for provider models listing"""

    provider: str = Field(description="Provider name")
    models: List[str] = Field(description="List of available model identifiers")
    current_model: str = Field(description="Currently selected model")


class AllModelsResponse(BaseModel):
    """Response model for all providers' models"""

    providers: Dict[str, List[str]] = Field(description="Models by provider")


class ModelSwitchRequest(BaseModel):
    """Request model for switching a provider's model"""

    provider: str = Field(description="Provider name (qwen, groq, etc.)")
    model: str = Field(description="Model identifier to switch to")


class ProviderStatusResponse(BaseModel):
    """Response model for provider status"""

    name: str = Field(description="Provider name")
    priority: int = Field(description="Provider priority")
    status: str = Field(description="Current status")
    current_model: str = Field(description="Currently selected model")
    available_models: List[str] = Field(description="Available models")
    last_error: str | None = Field(description="Last error message if any")
    stats: Dict = Field(description="Usage statistics")


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/", response_model=AllModelsResponse, summary="List all provider models")
async def list_all_models(current_user: User = Depends(get_current_active_user)):
    """
    Get available models for all configured providers.

    Returns a dictionary mapping provider names to their available model lists.
    Uses the model discovery service which fetches from APIs or uses fallback lists.

    **Note**: Discovery results are cached to reduce API calls.
    """
    try:
        discovery_service = get_model_discovery_service()
        all_models = await discovery_service.get_all_models()

        return AllModelsResponse(providers=all_models)

    except Exception as e:
        logger.error(f"Error listing all models: {e}")
        raise HTTPException(status_code=500, detail="Failed to list models")


@router.get(
    "/{provider_name}", response_model=ProviderModelsResponse, summary="List provider models"
)
async def list_provider_models(
    provider_name: str, current_user: User = Depends(get_current_active_user)
):
    """
    Get available models for a specific provider.

    Args:
        provider_name: Name of the provider (qwen, groq, cerebras, etc.)

    Returns:
        List of available model identifiers and the currently selected model.

    **Supported Providers**:
    - `qwen`: Alibaba DashScope (hardcoded list)
    - `groq`: Groq API (dynamic discovery)
    - `cerebras`: Cerebras API (dynamic discovery)
    - `together`: Together.ai API (dynamic discovery)
    - `sambanova`: Sambanova API (dynamic discovery)
    """
    try:
        provider_name = provider_name.lower()

        # Get models from discovery service
        discovery_service = get_model_discovery_service()
        models = await discovery_service.discover_models(provider_name)

        # Get current model from active provider if available
        current_model = "unknown"
        for provider in provider_selector.providers:
            if provider.name == provider_name:
                # Check if provider has get_model method (Qwen does)
                if hasattr(provider, "get_model"):
                    current_model = provider.get_model()  # type: ignore[attr-defined]
                break

        return ProviderModelsResponse(
            provider=provider_name, models=models, current_model=current_model
        )

    except Exception as e:
        logger.error(f"Error listing models for {provider_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list models for provider")


@router.post("/switch", summary="Switch provider model")
async def switch_provider_model(
    request: ModelSwitchRequest, current_user: User = Depends(get_current_active_user)
):
    """
    Switch the active model for a specific provider.

    Args:
        request: Model switch request with provider name and target model

    Returns:
        Success message with new model information

    **Example**:
    ```json
    {
        "provider": "qwen",
        "model": "qwen-turbo"
    }
    ```

    **Note**: Currently only supports Qwen provider. Other providers will be added in Phase 4.
    """
    try:
        provider_name = request.provider.lower()

        # Find the provider
        target_provider = None
        for provider in provider_selector.providers:
            if provider.name == provider_name:
                target_provider = provider
                break

        if not target_provider:
            raise HTTPException(
                status_code=404, detail=f"Provider '{provider_name}' not found or not initialized"
            )

        # Check if provider supports model switching
        if not hasattr(target_provider, "set_model"):
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{provider_name}' does not support dynamic model switching",
            )

        # Verify the model is available
        if hasattr(target_provider, "get_available_models"):
            available_models = await target_provider.get_available_models()  # type: ignore[attr-defined]
            if request.model not in available_models:
                raise HTTPException(
                    status_code=400,
                    detail=f"Model '{request.model}' not available for provider '{provider_name}'. "
                    f"Available models: {', '.join(available_models)}",
                )

        # Switch the model
        target_provider.set_model(request.model)  # type: ignore[attr-defined]

        return {
            "success": True,
            "provider": provider_name,
            "model": request.model,
            "message": f"Successfully switched {provider_name} to model {request.model}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching model for {request.provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to switch model")


@router.get(
    "/providers/status", response_model=List[ProviderStatusResponse], summary="Get provider status"
)
async def get_providers_status(current_user: User = Depends(get_current_active_user)):
    """
    Get comprehensive status for all configured providers.

    Returns detailed information including:
    - Current status (available, rate-limited, error)
    - Selected model and available models
    - Usage statistics
    - Last error message if any

    **Useful for**: Monitoring, debugging, and admin dashboards
    """
    try:
        # Get provider status from provider_init
        status_data = await get_provider_status()

        providers_status = []
        discovery_service = get_model_discovery_service()

        for provider_data in status_data["providers"]:
            provider_name = provider_data["name"]

            # Get available models
            available_models = await discovery_service.discover_models(provider_name)

            # Get current model if provider supports it
            current_model = "unknown"
            for provider in provider_selector.providers:
                if provider.name == provider_name:
                    if hasattr(provider, "get_model"):
                        current_model = provider.get_model()  # type: ignore[attr-defined]
                    elif hasattr(provider, "model"):
                        current_model = provider.model  # type: ignore[attr-defined]
                    break

            providers_status.append(
                ProviderStatusResponse(
                    name=provider_data["name"],
                    priority=provider_data["priority"],
                    status=provider_data["status"],
                    current_model=current_model,
                    available_models=available_models,
                    last_error=provider_data["last_error"],
                    stats=provider_data["stats"],
                )
            )

        return providers_status

    except Exception as e:
        logger.error(f"Error getting provider status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get provider status")


@router.post("/discovery/refresh", summary="Refresh model discovery cache")
async def refresh_model_discovery(
    provider_name: str | None = None, current_user: User = Depends(get_current_active_user)
):
    """
    Clear the model discovery cache to force re-fetching from APIs.

    Args:
        provider_name: Optional provider name to refresh. If not provided, clears all caches.

    Returns:
        Success message

    **Use case**: When a provider adds new models and you want to discover them immediately.
    """
    try:
        discovery_service = get_model_discovery_service()
        discovery_service.clear_cache(provider_name)

        if provider_name:
            return {
                "success": True,
                "message": f"Cleared discovery cache for {provider_name}",
            }
        else:
            return {
                "success": True,
                "message": "Cleared all discovery caches",
            }

    except Exception as e:
        logger.error(f"Error refreshing discovery cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh discovery cache")
