import re
from datetime import datetime
from pathlib import Path

import ollama

from Backend.config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT
from Backend.services.prompt_service import build_prompt

MODEL = OLLAMA_MODEL


class ModelUnavailableError(RuntimeError):
    """Ollama is not running, the model is missing, or it timed out."""


# --------------------------------------------------
# LOW-LEVEL MODEL CALL
# --------------------------------------------------

def ask_gemma(
    prompt: str,
    image_path: str | None = None,
    temperature: float = 0.3
) -> str:
    """Send a text prompt, optionally with an image, to Gemma."""

    message = {"role": "user", "content": prompt}

    if image_path:
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        message["images"] = [str(path)]

    try:
        client = ollama.Client(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT)

        response = client.chat(
            model=MODEL,
            messages=[message],
            options={"temperature": temperature}
        )

        text = (response["message"]["content"] or "").strip()

    except Exception as error:
        raise ModelUnavailableError(
            f"Could not get a response from Gemma. Make sure Ollama is "
            f"running and {MODEL} is installed. Details: {error}"
        ) from error

    if not text:
        raise ModelUnavailableError(
            "Gemma returned an empty response. Please try again."
        )

    return text


# --------------------------------------------------
# OUTPUT CLEAN-UP
# --------------------------------------------------

_PREAMBLE = re.compile(
    r"^(here(?:'s| is| are)\b|sure\b|certainly\b|okay\b|of course\b|"
    r"below is\b|absolutely\b)",
    re.IGNORECASE
)

_TRAILING_NOTE = re.compile(
    r"^\(?\s*(note|disclaimer|please note|remember)\b",
    re.IGNORECASE
)

_RULE_LINE = re.compile(r"^\s*([-*_=]\s*){3,}$")


def clean_document(text: str) -> str:
    """Turn model output into clean plain text.

    Small local models like to add chatty intros, Markdown (**bold**, ## headings,
    --- lines) and explanations inside [placeholders]. None of that belongs in a
    letter that will be printed or exported.
    """

    text = (text or "").replace("\r\n", "\n").strip()

    # A whole answer wrapped in a code fence.
    fenced = re.match(r"^```[\w-]*\n(.*?)\n?```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    lines = text.split("\n")

    # Chatty introduction ("Here is your formal letter:")
    while lines and (
        not lines[0].strip()
        or _RULE_LINE.match(lines[0])
        or (_PREAMBLE.match(lines[0].strip()) and len(lines[0]) < 140)
    ):
        lines.pop(0)

    # Closing notes ("Note: ...") in the last few lines.
    for index in range(max(0, len(lines) - 6), len(lines)):
        if _TRAILING_NOTE.match(lines[index].strip()):
            lines = lines[:index]
            break

    cleaned = []

    for line in lines:
        if _RULE_LINE.match(line):
            cleaned.append("")
            continue

        line = re.sub(r"^\s*#{1,6}\s*", "", line)          # headings
        line = re.sub(r"^(\s*)[*•]\s+", r"\1- ", line)     # bullets
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)       # bold
        line = re.sub(r"__(.+?)__", r"\1", line)
        line = re.sub(r"(?<![*\w])\*(?!\s)([^*\n]+?)\*(?![*\w])", r"\1", line)
        line = line.replace("`", "")

        # "[Date - Omitted as not provided]" -> "[Date]"
        line = re.sub(
            r"\[([^\]\n]*?)\s+[-–—:]\s+[^\]\n]*\]",
            r"[\1]",
            line
        )

        cleaned.append(line.rstrip())

    text = "\n".join(cleaned).strip()

    return re.sub(r"\n{3,}", "\n\n", text)


# --------------------------------------------------
# DIGITAL MODE
# --------------------------------------------------

def analyze_image(image_path: str, mode: str) -> str:
    """Analyze an uploaded image in Reality or Digital Mode."""

    if mode == "reality":
        prompt = """
You are PrismShift AI's Reality Mode analysis assistant.

Carefully examine the uploaded real-world photograph.

Organize your response under these headings:

1. Visible Evidence
Describe only things that can actually be seen in the photograph.

2. Observed Concerns
Explain any visible damage, obstruction, waste, maintenance issue,
or other concern. Do not exaggerate.

3. Possible Impacts
Describe potential consequences, clearly identifying them as possibilities
rather than confirmed facts.

4. Recommended Actions
Suggest practical next steps.

5. Missing Information
List details that cannot be established from the image alone.

Important:
- Never invent the location, date, measurements, ownership, or cause.
- Do not claim that a person or authority is responsible without evidence.
- Clearly distinguish observations from assumptions.
- Use professional, neutral language. Plain text only, no Markdown symbols.
"""

    elif mode == "digital":
        prompt = """
You are PrismShift AI's Digital Mode visual-design analyst.

Analyze the uploaded design reference.

Use these headings:

1. Design Category
Identify whether it appears to be a poster, website, app interface,
logo, banner, social media graphic, or another design.

2. Overall Visual Style
Describe the visual direction and mood.

3. Colour Palette
Describe the visible main and supporting colours.

4. Layout and Composition
Explain spacing, alignment, positioning, and visual balance.

5. Typography
Describe the visible typography characteristics.
Do not invent exact font names.

6. Visual Hierarchy
Explain what attracts attention first and why.

7. Design Elements
Describe visible shapes, icons, buttons, images, borders, and other elements.

8. Improvement Opportunities
Suggest useful improvements, if appropriate.

9. Reference Summary
Provide a concise summary of the design.

Important:
- Do not invent exact CSS values or font names.
- Do not generate an image, website, SVG, or code.
- This mode is for visual analysis and prompt writing only.
- Plain text only, no Markdown symbols.
"""

    else:
        raise ValueError("Mode must be 'reality' or 'digital'.")

    return clean_document(ask_gemma(prompt, image_path))


_PROMPT_MARKER = re.compile(r"GENERATED\s+AI\s+PROMPT\s*:?", re.IGNORECASE)


def generate_digital_prompt(
    image_path: str,
    description: str = ""
) -> tuple[str, str]:
    """Return (analysis, generated_prompt) for a design reference.

    The template asks the model for an analysis followed by a section called
    GENERATED AI PROMPT. The two parts are split so the UI can show the prompt
    (the thing the user copies) separately from the analysis.
    """

    prompt = build_prompt(
        "digital",
        description=description.strip() or "No additional changes provided."
    )

    text = clean_document(ask_gemma(prompt, image_path))

    parts = _PROMPT_MARKER.split(text)

    if len(parts) < 2 or not parts[-1].strip():
        # The model ignored the format: treat everything as the prompt.
        return "", text

    return parts[0].strip(), parts[-1].strip()


# --------------------------------------------------
# REALITY MODE
# --------------------------------------------------

DOCUMENT_TYPES = ["letter", "application", "complaint", "report"]

_TYPE_GUIDANCE = {
    "letter": """DOCUMENT LAYOUT - formal letter. Use exactly this order, with a blank line between blocks:

From:
{author_name}
{location}

Date: {today}

To,
{authority}

Subject: (one clear line)

Respected Sir/Madam,

(Opening paragraph: who you are and why you are writing.)
(Paragraph: what is visible in the photograph.)
(Paragraph: possible consequences if it is not addressed.)
(Paragraph: the action you request.)

Thank you for your time and attention.

Yours sincerely,
{author_name}
{location}""",

    "application": """DOCUMENT LAYOUT - formal application. Use exactly this order, with a blank line between blocks:

To,
{authority}

Date: {today}

Subject: Application regarding (the issue) (one clear line)

Respected Sir/Madam,

(Opening paragraph: who you are and what you are applying for.)
(Paragraph: what is visible in the photograph.)
(Paragraph: why the matter needs attention.)
(Paragraph: the specific request or action sought.)

Thank you for considering this application.

Yours faithfully,
{author_name}
{location}""",

    "complaint": """DOCUMENT LAYOUT - formal complaint. Use exactly this order, with a blank line between blocks:

From:
{author_name}
{location}

Date: {today}

To,
{authority}

Subject: Complaint regarding (the issue) (one clear line)

Respected Sir/Madam,

(Opening paragraph: state that you are lodging a complaint and about what.)
(Paragraph: what is visible in the photograph.)
(Paragraph: the inconvenience, risk or impact, worded as possibilities.)
(Paragraph: the corrective action you request and a polite request for a reply.)

Yours sincerely,
{author_name}
{location}""",

    "report": """DOCUMENT LAYOUT - detailed report. Use exactly this order, with a blank line between blocks:

Title: (one clear line)

Prepared by: {author_name}
Location: {location}
Date: {today}
Submitted to: {authority}

1. Introduction
(2-3 sentences.)

2. Observations
(What is visible in the photograph, as a short list.)

3. Description of the Issue
(A short paragraph.)

4. Possible Consequences
(Worded as possibilities.)

5. Recommended Action
(A short numbered or dashed list.)

6. Conclusion
(2-3 sentences.)

Prepared by,
{author_name}""",
}


def normalise_document_type(document_type: str) -> str:
    value = (document_type or "").strip().lower()

    if value not in DOCUMENT_TYPES:
        raise ValueError(
            "Document type must be letter, application, complaint, or report."
        )

    return value


def generate_reality_report(
    image_path: str,
    document_type: str,
    author_name: str,
    location: str,
    authority: str,
    additional_points: str = ""
) -> str:
    """Generate a formal Reality Mode document from a photograph."""

    document_type = normalise_document_type(document_type)

    today = datetime.now().strftime("%d %B %Y").lstrip("0")

    # Missing details become short placeholders the user can fill in.
    values = {
        "author_name": author_name.strip() or "[Your Name]",
        "location": location.strip() or "[Location]",
        "authority": authority.strip() or "[Recipient Authority and Designation]",
        "today": today,
    }

    prompt = build_prompt(
        "reality",
        document_type=document_type,
        additional_points=additional_points.strip() or "None provided.",
        type_guidance=_TYPE_GUIDANCE[document_type].format(**values),
        **values
    )

    document = clean_document(ask_gemma(prompt, image_path))

    # Fill details the model left as placeholders although we know them.
    document = re.sub(
        r"\[(?:today'?s |current )?date\]", today, document, flags=re.IGNORECASE
    )

    if author_name.strip():
        document = re.sub(
            r"\[(?:your|author'?s?|sender'?s?)(?: full)? name\]",
            author_name.strip(),
            document,
            flags=re.IGNORECASE
        )

    return document


# --------------------------------------------------
# EDITING
# --------------------------------------------------

def edit_content(
    original_content: str,
    instruction: str,
    content_type: str
) -> str:
    """Revise an existing report or reusable design prompt."""

    if content_type == "report":
        prompt = build_prompt(
            "reality_edit",
            current_report=original_content,
            instruction=instruction
        )
    elif content_type == "prompt":
        prompt = build_prompt(
            "digital_edit",
            original_prompt=original_content,
            instruction=instruction
        )
    else:
        raise ValueError("content_type must be 'report' or 'prompt'.")

    return clean_document(ask_gemma(prompt))
