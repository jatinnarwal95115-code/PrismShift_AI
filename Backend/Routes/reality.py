from pathlib import Path

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from Backend.Routes.auth import get_optional_user
from Backend.services.image_service import save_uploaded_image
from Backend.services.gemma_service import (
    ModelUnavailableError,
    edit_content,
    edit_prompt_text,
    finish_reality_report,
    generate_reality_report,
    normalise_document_type,
    reality_prompt_text
)
from Backend.services.stream_service import (
    event_line,
    stream_response,
    stream_snapshots
)
from Backend.services.report_service import generate_report
from Backend.services.database import (
    create_conversation,
    save_message,
    get_user_conversation,
    delete_image_file,
    REPORT_DIR
)

router = APIRouter(
    prefix="/reality",
    tags=["Reality Mode"]
)


def _model_error(error: Exception) -> HTTPException:
    """Ollama problems are 503 (service unavailable), not a generic 500."""

    if isinstance(error, ModelUnavailableError):
        return HTTPException(status_code=503, detail=str(error))

    return HTTPException(status_code=500, detail=f"Request failed: {error}")


# --------------------------------------------------
# 1. GENERATE FORMAL DOCUMENT
# --------------------------------------------------

def _save_report(user, document_type, location, report, image_path,
                 author_name="", authority="", additional_points=""):
    """Store the finished document in the user's history. Returns the id."""

    if not user:
        delete_image_file(image_path)
        return None

    conversation_id = create_conversation(
        user_id=user["id"],
        title=f"{document_type.title()} - {location.strip() or 'New Report'}",
        mode="reality",
        image_path=image_path,
        input_data={
            "document_type": document_type,
            "author_name": author_name,
            "location": location,
            "authority": authority,
            "additional_points": additional_points
        }
    )
    save_message(conversation_id, "assistant", report)

    return conversation_id


@router.post("/generate")
async def reality_generate(
    image: UploadFile = File(...),
    document_type: str = Form(...),
    author_name: str = Form(""),
    location: str = Form(""),
    authority: str = Form(""),
    additional_points: str = Form(""),
    stream: bool = Form(False),
    user=Depends(get_optional_user)
):
    # Validate before saving the upload or calling the (slow) model.
    try:
        document_type = normalise_document_type(document_type)
        prompt, today = reality_prompt_text(
            document_type, author_name, location, authority, additional_points
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    image_path = await save_uploaded_image(image)

    if stream:
        # The page shows the document while it is being written, so the user
        # sees text within seconds instead of waiting for the whole answer.
        def events():
            try:
                raw = ""

                for raw, snapshot in stream_snapshots(prompt, image_path, 1200):
                    yield event_line({"text": snapshot})

                report = finish_reality_report(raw, today, author_name)
                conversation_id = _save_report(
                    user, document_type, location, report, image_path,
                    author_name, authority, additional_points
                )

                yield event_line({
                    "done": True,
                    "document": report,
                    "conversation_id": conversation_id
                })

            except Exception as error:
                delete_image_file(image_path)
                yield event_line({"error": str(_model_error(error).detail)})

        return stream_response(events())

    try:
        # The model call is slow and blocking. Run it in a worker thread so
        # the server keeps answering other requests (history, login, ...).
        report = await run_in_threadpool(
            generate_reality_report,
            image_path=image_path,
            document_type=document_type,
            author_name=author_name,
            location=location,
            authority=authority,
            additional_points=additional_points
        )
    except Exception as error:
        delete_image_file(image_path)
        raise _model_error(error)

    conversation_id = _save_report(
        user, document_type, location, report, image_path,
        author_name, authority, additional_points
    )

    return {
        "success": True,
        "mode": "reality",
        "document": report,
        "conversation_id": conversation_id
    }


# --------------------------------------------------
# 2. EDIT DOCUMENT
# --------------------------------------------------

@router.post("/edit")
async def reality_edit(
    instruction: str = Form(...),
    content: str = Form(...),
    conversation_id: int | None = Form(None),
    stream: bool = Form(False),
    user=Depends(get_optional_user)
):
    if not instruction.strip() or not content.strip():
        raise HTTPException(
            status_code=400,
            detail="Content and editing instruction are required."
        )

    if conversation_id is not None:
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Please log in to edit a saved conversation."
            )

        conversation = get_user_conversation(conversation_id, user["id"])

        if not conversation or conversation["mode"] != "reality":
            raise HTTPException(
                status_code=404,
                detail="Reality conversation not found."
            )

    def remember(revised):
        if conversation_id is not None:
            save_message(conversation_id, "user", instruction)
            save_message(conversation_id, "assistant", revised)

    if stream:
        prompt = edit_prompt_text(content, instruction, "report")

        def events():
            try:
                snapshot = ""

                for _, snapshot in stream_snapshots(prompt, None, 1500):
                    yield event_line({"text": snapshot})

                remember(snapshot)
                yield event_line({
                    "done": True,
                    "revised_document": snapshot,
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
            content_type="report"
        )
    except Exception as error:
        raise _model_error(error)

    remember(revised)

    return {
        "success": True,
        "revised_document": revised,
        "conversation_id": conversation_id
    }


# --------------------------------------------------
# 3. EXPORT DOCUMENT (PDF / DOCX / PPTX)
# --------------------------------------------------

MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
    "pptx": (
        "application/vnd.openxmlformats-officedocument."
        "presentationml.presentation"
    )
}


@router.post("/export")
def reality_export(
    content: str = Form(...),
    file_format: str = Form(...)
):
    file_format = file_format.lower().strip()

    if file_format not in MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Choose PDF, DOCX, or PPTX."
        )

    if not content.strip():
        raise HTTPException(
            status_code=400,
            detail="There is no report content to export."
        )

    try:
        filepath = Path(generate_report(content, file_format)).resolve()
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Report export failed: {error}"
        )

    if filepath.parent != REPORT_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid report path.")

    return FileResponse(
        path=str(filepath),
        filename=f"PrismShift_Reality_Report.{file_format}",
        media_type=MEDIA_TYPES[file_format],
        # The file is only needed for this download; don't let them pile up.
        background=BackgroundTask(filepath.unlink, missing_ok=True)
    )
