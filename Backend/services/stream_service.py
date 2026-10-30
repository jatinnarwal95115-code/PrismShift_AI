import json

from fastapi.responses import StreamingResponse

from Backend.services.gemma_service import clean_document, stream_gemma


def event_line(payload: dict) -> str:
    """One newline-delimited JSON event."""

    return json.dumps(payload, ensure_ascii=False) + "\n"


def stream_response(generator) -> StreamingResponse:
    return StreamingResponse(
        generator,
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


def stream_snapshots(prompt: str, image_path: str | None, max_tokens: int):
    """Run the model and yield (raw_text_so_far, cleaned_snapshot).

    The snapshot is what the page shows while the text is still being written:
    Markdown and chatty intros are already stripped.
    """

    raw, last = "", ""

    for chunk in stream_gemma(prompt, image_path, max_tokens=max_tokens):
        raw += chunk
        snapshot = clean_document(raw)

        if snapshot != last:
            last = snapshot
            yield raw, snapshot

    if not raw:
        yield raw, ""
