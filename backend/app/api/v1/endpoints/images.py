"""Scene Image Generation API"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.middleware.auth import get_current_active_user
from app.services.image_service import image_service

router = APIRouter(prefix="/images", tags=["images"])


class ImageGenerationRequest(BaseModel):
    """Request model for image generation"""

    scene_description: str
    use_cache: bool = True


class ImageGenerationResponse(BaseModel):
    """Response model for image generation"""

    image_data: str | None
    cached: bool
    scene_description: str


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_scene_image(
    request: ImageGenerationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a scene image using Pixtral

    Args:
        request: Image generation request
        current_user: Authenticated user
        db: Database session

    Returns:
        Generated image data (base64) or None
    """
    # Generate or retrieve from cache
    image_data = await image_service.generate_scene_image(
        scene_description=request.scene_description,
        db=db,
        use_cache=request.use_cache,
    )

    return ImageGenerationResponse(
        image_data=image_data,
        cached=False,  # Would need to track this in service
        scene_description=request.scene_description,
    )
