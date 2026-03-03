from __future__ import annotations

import os
import json
from typing import List
from zipfile import ZipFile
from openai import OpenAI
from pathlib import Path
from capstone.code_bundle import bundle_code_from_zip
from capstone.code_bundle import BundledFile

MAX_FILES = 5
MAX_CHARS_PER_FILE = 4000


def _get_openai_client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def _select_relevant_files(files: List[BundledFile]) -> List[BundledFile]:
    """
    Select a limited number of relevant source files.
    Prioritize backend and logic files.
    """
    priority_extensions = (".py", ".js", ".ts", ".java", ".cs")

    filtered = [
        f for f in files
        if f.path.endswith(priority_extensions)
    ]

    return filtered[:MAX_FILES]


def _truncate_file_content(bf: BundledFile) -> str:
    if len(bf.text) > MAX_CHARS_PER_FILE:
        return bf.text[:MAX_CHARS_PER_FILE]
    return bf.text


def run_ai_error_analysis(
    project_id: str,
    snapshot: dict,
    zip_path: str,
) -> list[dict]:
    """
    Real AI error analysis using extracted source files.
    """

    client = _get_openai_client()
    if client is None:
        return []

    # 1️⃣ Bundle project files from snapshot
    zip_path = Path(zip_path)
    

    with ZipFile(zip_path) as z:
        include_paths = [
            info.filename
            for info in z.infolist()
            if not info.is_dir()
        ]

    bundled_files = bundle_code_from_zip(
        zip_path,
        include_paths
    )
    print(" RUNNING AI ERROR ANALYSIS")
    print("Project:", project_id)
    print("Zip path:", zip_path)
    if not bundled_files:
        return []

    selected_files = _select_relevant_files(bundled_files)

    file_blocks = []
    for bf in selected_files:
        truncated_text = _truncate_file_content(bf)
        file_blocks.append(
            f"\nFILE: {bf.path}\nBEGIN\n{truncated_text}\nEND\n"
        )

    languages = snapshot.get("languages", {})
    frameworks = snapshot.get("frameworks", [])

    prompt = f"""
You are a senior software engineer performing an automated bug investigation.

Project ID: {project_id}

Languages: {json.dumps(languages)}
Frameworks: {json.dumps(frameworks)}

Analyze the provided source files carefully.

Detect:
- Syntax errors
- Runtime risks
- Unhandled edge cases
- Architectural flaws
- Bad practices
- Security risks
- Missing validation
- Async or promise issues
- Error handling problems

Return ONLY valid JSON in this exact format:

[
  {{
    "title": "Short issue name",
    "detail": "Clear explanation of the issue and why it matters",
    "severity": "low | medium | high"
  }}
]

If the project appears clean, return [].

Be realistic. Do not invent fake issues.
"""
    print(" Bundled files count:", len(bundled_files))
    full_prompt = prompt + "\n".join(file_blocks)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert code reviewer."},
            {"role": "user", "content": full_prompt}
        ],
        temperature=0.1,
    )

    content = response.choices[0].message.content.strip()
    print(" RAW AI RESPONSE:")
    print(response)
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return parsed
        return []
    except Exception:
        return []
