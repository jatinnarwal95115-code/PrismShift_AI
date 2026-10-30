from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_DIR = BASE_DIR / "Prompts"

PROMPT_FILES = {
    "reality": "reality_prompt.txt",
    "digital": "digital_prompt.txt",
    "reality_edit": "reality_edit_prompt.txt",
    "digital_edit": "digital_edit_prompt.txt",
}


def load_prompt(prompt_name: str) -> str:
    """Load a prompt template by its registered name."""

    if prompt_name not in PROMPT_FILES:
        raise ValueError(f"Unknown prompt template: {prompt_name}")

    prompt_path = PROMPT_DIR / PROMPT_FILES[prompt_name]

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file is missing: {prompt_path}"
        )

    return prompt_path.read_text(encoding="utf-8")


def build_prompt(prompt_name: str, **values) -> str:
    """Load a template and replace its placeholders."""

    template = load_prompt(prompt_name)

    try:
        return template.format(**values)
    except KeyError as error:
        raise ValueError(
            f"Missing prompt value: {error}"
        ) from error