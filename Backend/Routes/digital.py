from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends
)
from fastapi.concurrency import run_in_threadpool

from Backend.Routes.auth import get_optional_user
from Backend.services.image_service import save_uploaded_image
from Backend.services.gemma_service import (
    ModelUnavailableError,
    analyze_image,
    digital_prompt_text,
    edit_content,
    edit_prompt_text,
    generate_digital_prompt,
    split_digital_output
)
from Backend.services.stream_service import (
    event_line,
    stream_response,
    stream_snapshots
)
from Backend.services.database import (
    create_conversation,
    save_message,
    get_user_conversation,
    delete_image_file
)

router = APIRouter(
    prefix="/digital",
    tags=["Digital Mode"]
)


def _model_error(error: Exception) -> HTTPException:
    if isinstance(error, ModelUnavailableError):
        return HTTPException(status_code=503, detail=str(error))

    return HTTPException(status_code=500, detail=f"Request failed: {error}")


# --------------------------------------------------
# 1. IMAGE ANALYSIS (stand-alone, nothing is saved to history)
# --------------------------------------------------

@router.post("/analyze")
async def digital_analyze(
    image: UploadFile = File(...),
    user=Depends(get_optional_user)
):
    image_path = await save_uploaded_image(image)

    try:
        analysis = await run_in_threadpool(analyze_image, image_path, "digital")
    except Exception as error:
        raise _model_error(error)
    finally:
        # A quick analysis is not a conversation, so don't keep the file or
        # fill the history with "Design Analysis" entries.
        delete_image_file(image_path)

    return {"success": True, "mode": "digital", "analysis": analysis}


# --------------------------------------------------
# 2. GENERATE REUSABLE DESIGN PROMPT
# --------------------------------------------------

def _save_prompt(user, description, generated_prompt, image_path):
    if not user:
        delete_image_file(image_path)
        return None

    conversation_id = create_conversation(
        user_id=user["id"],
        title="Digital Design Prompt",
        mode="digital",
        image_path=image_path
    )

    if description.strip():
        save_message(conversation_id, "user", description)

    save_message(conversation_id, "assistant", generated_prompt)

    return conversation_id


@router.post("/generate")
async def digital_generate(
    image: UploadFile = File(...),
    description: str = Form(""),
    stream: bool = Form(False),
    user=Depends(get_optional_user)
):
    image_path = await save_uploaded_image(image)

    if stream:
        prompt = digital_prompt_text(description)

        def events():
            try:
                raw = ""

                for raw, snapshot in stream_snapshots(prompt, image_path, 1800):
                    yield event_line({"text": snapshot})

                analysis, generated_prompt = split_digital_output(raw)
                conversation_id = _save_prompt(
                    user, description, generated_prompt, image_path
                )

                yield event_line({
                    "done": True,
                    "analysis": analysis,
                    "generated_prompt": generated_prompt,
                    "conversation_id": conversation_id
                })
            except Exception as error:
                delete_image_file(image_path)
                yield event_line({"error": str(_model_error(error).detail)})

        return stream_response(events())

    try:
        analysis, generated_prompt = await run_in_threadpool(
            generate_digital_prompt,
            image_path=image_path,
            description=description
        )
    except Exception as error:
        delete_image_file(image_path)
        raise _model_error(error)

    conversation_id = _save_prompt(user, description, generated_prompt, image_path)

    return {
        "success": True,
        "mode": "digital",
        "analysis": analysis,
        "generated_prompt": generated_prompt,
        "conversation_id": conversation_id
    }


# --------------------------------------------------
# 3. EDIT GENERATED PROMPT
# --------------------------------------------------

@router.post("/edit")
async def digital_edit(
    instruction: str = Form(...),
    content: str = Form(...),
    conversation_id: int | None = Form(None),
    stream: bool = Form(False),
    user=Depends(get_optional_user)
):
    if not instruction.strip() or not content.strip():
        raise HTTPException(
            status_code=400,
            detail="Prompt and editing instruction are required."
        )

    if conversation_id is not None:
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Please log in to edit a saved conversation."
            )

        conversation = get_user_conversation(conversation_id, user["id"])

        if not conversation or conversation["mode"] != "digital":
            raise HTTPException(
                status_code=404,
                detail="Digital conversation not found."
            )

    def remember(revised):
        if conversation_id is not None:
            save_message(conversation_id, "user", instruction)
            save_message(conversation_id, "assistant", revised)

    if stream:
        prompt = edit_prompt_text(content, instruction, "prompt")

        def events():
            try:
                snapshot = ""

                for _, snapshot in stream_snapshots(prompt, None, 1500):
                    yield event_line({"text": snapshot})

                remember(snapshot)
                yield event_line({
                    "done": True,
                    "revised_prompt": snapshot,
                    "conversation_id": conversation_id
                })
            except Exception as error:
                yield event_line({"error": str(_model_error(error).detail)})

        return stream_response(events())

    try:
        revised = await run_in_threadpool(
            edit_content,
            original_content=content,
            instruction=instruction,
            content_type="prompt"
        )
    except Exception as error:
        raise _model_error(error)

    remember(revised)

    return {
        "success": True,
        "revised_prompt": revised,
        "conversation_id": conversation_id
    }
