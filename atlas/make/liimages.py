from pathlib import Path
import re
import time
from datetime import datetime
import urllib.parse

import requests

from atlas.utils.paths import MODULES_DIR


# ============================================================
# Image generation style
# ============================================================

STYLE = """
Create a simple clean vector illustration.

Style:
- minimal modern illustration
- blog artwork
- flat design
- few elements
- large clear shapes
- strong composition

Rules:
- show the concept visually
- use symbols and objects only
- no writing

Keep it simple:
one main object,
one supporting idea,
one visual metaphor.
"""


# ============================================================
# Markdown parsing
# ============================================================

def extract_assets(md):

    pattern = (
        r"\*\*Suggested Asset:\*\*\s*"
        r"(.*?)(?=\n\n###|\Z)"
    )

    return list(
        re.finditer(
            pattern,
            md,
            flags=re.DOTALL
        )
    )



def clean_prompt(prompt):

    prompt = (
        prompt
        .strip()
        .replace("\n", " ")
    )


    # Ignore already-generated files
    if re.search(
        r"\.(png|jpg|jpeg|webp|gif)$",
        prompt,
        re.IGNORECASE
    ):
        return None


    # Ignore image URLs
    if prompt.startswith("http"):
        return None


    return prompt



# ============================================================
# Filename
# ============================================================

def make_filename(
    module_name,
    index
):

    return (
        f"{module_name}"
        f"_linkedin_{index}.png"
    )



# ============================================================
# Pollinations
# ============================================================

def generate_image(
    prompt,
    output
):

    full_prompt = f"""
{STYLE}

Concept to illustrate:
{prompt}

Create a single clean visual representation.
"""

    encoded = urllib.parse.quote(
        full_prompt
    )

    url = (
        "https://image.pollinations.ai/prompt/"
        + encoded
        + "?width=1024&height=576"
    )

    print(
        "Requesting image..."
    )

    for attempt in range(3):

        try:

            response = requests.get(
                url,
                timeout=180
            )

            response.raise_for_status()

            output.write_bytes(
                response.content
            )

            return True

        except requests.RequestException as e:

            print(
                f"Image request failed "
                f"(attempt {attempt + 1}/3): {e}"
            )

            if attempt < 2:

                time.sleep(
                    5 * (attempt + 1)
                )

    print(
        f"Skipping image generation: {output}"
    )

    return False




# ============================================================
# Markdown update
# ============================================================

def replace_asset_block(
    md,
    match,
    filename,
    metadata
):

    replacement = f"""
**Suggested Asset:**
{filename}

<!-- Atlas Image Metadata
Generated: {metadata["generated"]}
Prompt: {metadata["prompt"]}
Provider: Pollinations
-->
""".strip()


    return (
        md[:match.start()]
        +
        replacement
        +
        md[match.end():]
    )



# ============================================================
# Main
# ============================================================

def generate_module_liimages(
    module_name: str
):

    module_path = (
        MODULES_DIR /
        module_name
    )


    md_path = (
        module_path /
        "generated" /
        "linkedln.md"
    )


    assets_dir = (
        module_path /
        "assets"
    )


    assets_dir.mkdir(
        exist_ok=True
    )


    if not md_path.exists():

        raise FileNotFoundError(
            md_path
        )


    md = md_path.read_text(
        encoding="utf-8"
    )


    matches = extract_assets(
        md
    )


    if not matches:

        print(
            "No Suggested Asset blocks found."
        )

        return



    # Keep numbering:
    # Post 1 -> image_1
    # Post 2 -> image_2
    indexed_matches = list(
        enumerate(matches, 1)
    )


    # Replace backwards so positions stay valid
    for index, match in reversed(
        indexed_matches
    ):

        raw_prompt = match.group(1)


        prompt = clean_prompt(
            raw_prompt
        )


        # Already converted
        if not prompt:

            continue



        filename = make_filename(
            module_name,
            index
        )


        output = (
            assets_dir /
            filename
        )


        print(
            "\nPost:",
            index
        )

        print(
            "Image:",
            filename
        )


        if output.exists():

            print(
                "Already exists."
            )


        else:

            print(
                "Prompt:",
                prompt
            )


            success = generate_image(
                prompt,
                output
            )

            if success:

                print(
                    "Saved:",
                    output
                )

                time.sleep(
                    3
                )

            else:

                print(
                    "Image generation failed:",
                    output
                )




        metadata = {

            "generated":
                datetime.now()
                .isoformat(
                    timespec="seconds"
                ),

            "prompt":
                prompt,

            "provider":
                "Pollinations",

            "file":
                filename
        }



        md = replace_asset_block(
            md,
            match,
            filename,
            metadata
        )


    md_path.write_text(
        md,
        encoding="utf-8"
    )


    print(
        "\nLinkedIn images complete."
    )