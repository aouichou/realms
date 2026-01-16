from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.health import NarrateRequest, NarrateResponse
from app.services.dm_engine import get_dm_engine
from app.utils.logger import get_logger

router = APIRouter(prefix="/api", tags=["narration"])
logger = get_logger(__name__)


@router.post("/narrate", response_model=NarrateResponse)
async def narrate_action(request: NarrateRequest):
    """
    Generate narration for a player action (non-streaming)
    """
    try:
        dm_engine = get_dm_engine()

        result = await dm_engine.narrate(
            user_action=request.action,
            character_context=request.character_context,
            game_state=request.game_state,
        )

        return NarrateResponse(narration=result["narration"], tokens_used=result["tokens_used"])

    except Exception as e:
        logger.error("Error in narrate_action: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/narrate/stream")
async def narrate_action_stream(request: NarrateRequest):
    """
    Generate narration for a player action (streaming)
    """
    try:
        dm_engine = get_dm_engine()

        async def generate():
            try:
                async for chunk in dm_engine.narrate_stream(
                    user_action=request.action,
                    character_context=request.character_context,
                    game_state=request.game_state,
                ):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error("Error in stream: %s", e)
                yield f"data: [ERROR] {str(e)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error("Error in narrate_action_stream: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/adventure/start", response_model=NarrateResponse)
async def start_adventure():
    """
    Start a new adventure (non-streaming)
    """
    try:
        dm_engine = get_dm_engine()

        result = await dm_engine.start_adventure()

        return NarrateResponse(narration=result["narration"], tokens_used=result["tokens_used"])

    except Exception as e:
        logger.error("Error in start_adventure: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/adventure/start/stream")
async def start_adventure_stream():
    """
    Start a new adventure (streaming)
    """
    try:
        dm_engine = get_dm_engine()

        async def generate():
            try:
                async for chunk in dm_engine.start_adventure_stream():
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error("Error in stream: %s", e)
                yield f"data: [ERROR] {str(e)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error("Error in start_adventure_stream: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
