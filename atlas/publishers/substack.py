from pathlib import Path
import re
import time
import io

import markdown
from PIL import Image
import win32clipboard
import win32con

from atlas.browser.edge import get_edge_page, stabilize_page
from atlas.utils.paths import MODULES_DIR


# ------------------------------------------------------------
# Markdown parsing
# ------------------------------------------------------------

IMAGE_PATTERN = re.compile(
    r"!\[(.*?)\]\((.*?)\)"
)

from markdown_it import MarkdownIt


def markdown_to_blocks(md):

    parser = MarkdownIt(
        "commonmark"
    )

    tokens = parser.parse(md)

    blocks = []

    image_positions = []


    # Find image ranges in the source markdown
    for token in tokens:

        if token.type == "inline":

            for child in token.children or []:

                if child.type == "image":

                    image_positions.append(
                        {
                            "start": token.map[0],
                            "path": child.attrGet("src"),
                            "alt": child.content,
                        }
                    )


    if not image_positions:
        return [
            {
                "type": "html",
                "content": markdown.markdown(
                    md,
                    extensions=[
                        "extra",
                        "fenced_code",
                        "tables",
                    ],
                ),
            }
        ]


    lines = md.splitlines()

    cursor = 0


    for image in image_positions:

        image_line = image["start"]


        before = "\n".join(
            lines[cursor:image_line]
        )


        if before.strip():

            blocks.append(
                {
                    "type": "html",
                    "content": markdown.markdown(
                        before,
                        extensions=[
                            "extra",
                            "fenced_code",
                            "tables",
                        ],
                    ),
                }
            )


        blocks.append(
            {
                "type": "image",
                "alt": image["alt"],
                "path": image["path"],
            }
        )


        cursor = image_line + 1


    remaining = "\n".join(
        lines[cursor:]
    )


    if remaining.strip():

        blocks.append(
            {
                "type": "html",
                "content": markdown.markdown(
                    remaining,
                    extensions=[
                        "extra",
                        "fenced_code",
                        "tables",
                    ],
                ),
            }
        )


    return blocks


# ------------------------------------------------------------
# Windows clipboard image handling
# ------------------------------------------------------------

def copy_image_to_clipboard(image_path: Path):

    try:
        image = Image.open(image_path)
        image = image.convert("RGB")

    except Exception as exc:

        print(
            "Skipping unreadable image:",
            image_path
        )

        print(
            "Reason:",
            exc
        )

        return False

    output = io.BytesIO()

    image.save(
        output,
        "BMP"
    )

    data = output.getvalue()[14:]

    win32clipboard.OpenClipboard()

    try:

        win32clipboard.EmptyClipboard()

        win32clipboard.SetClipboardData(
            win32con.CF_DIB,
            data
        )

    finally:

        win32clipboard.CloseClipboard()

    return True



# ------------------------------------------------------------
# Substack insertion helpers
# ------------------------------------------------------------

def move_cursor_to_end(editor):

    editor.evaluate(
        """
        element => {

            element.focus();

            const range =
                document.createRange();

            range.selectNodeContents(element);

            range.collapse(false);


            const selection =
                window.getSelection();

            selection.removeAllRanges();

            selection.addRange(range);
        }
        """
    )

def clean_html(html: str):

    html = html.replace("\n", "")

    html = re.sub(
        r">\s+<",
        "><",
        html
    )

    return html



def insert_html(editor, html):

    html = clean_html(html)

    editor.evaluate(
        """
        (element, html) => {

            element.focus();

            document.execCommand(
                "insertHTML",
                false,
                html
            );

            element.dispatchEvent(
                new InputEvent(
                    "input",
                    {
                        bubbles:true
                    }
                )
            );
        }
        """,
        html
    )


def paste_image(page, editor, image_path):

    print(
        "Pasting image:",
        image_path
    )

    # Count images already present in the editor
    before = editor.locator("img").count()

    copy_image_to_clipboard(
        image_path
    )

    editor.click(
        force=True
    )

    page.keyboard.press(
        "Control+V"
    )

    # Wait for Substack to actually insert the image.
    for _ in range(30):

        page.wait_for_timeout(500)

        after = editor.locator("img").count()

        if after > before:

            print(
                f"Image inserted: {image_path.name}"
            )

            # Give Substack time to finish the upload/render.
            page.wait_for_timeout(1500)

            return

    print(
        f"WARNING: Substack did not visibly insert {image_path.name}"
    )



# ------------------------------------------------------------
# Publishing
# ------------------------------------------------------------

def publish_substack(module_name: str):

    module_path = (
        MODULES_DIR / module_name
    )

    blog_path = (
        module_path / "blog.md"
    )


    if not blog_path.exists():
        raise FileNotFoundError(
            blog_path
        )


    md = blog_path.read_text(
        encoding="utf-8"
    )


    blocks = markdown_to_blocks(md)


    page = get_edge_page()


    page.goto(
        "https://substack.com/?utm_source=user-menu",
        wait_until="domcontentloaded"
    )

    stabilize_page(page)

    print(
        "Opened Substack"
    )


    page.get_by_text(
        "Create",
        exact=True
    ).click()


    page.get_by_text(
        "Article",
        exact=True
    ).click()


    page.wait_for_url(
        "**/publish/post/**",
        timeout=30000
    )


    page.wait_for_timeout(
        3000
    )


    editor = page.locator(
        '[data-testid="editor"]'
    )


    editor.wait_for(
        state="visible"
    )


    print(
        "Editor ready"
    )


    for block in blocks:

        if block["type"] == "html":

            insert_html(
                editor,
                block["content"]
            )

            move_cursor_to_end(
                editor
            )

            page.keyboard.press("Space")

            page.wait_for_timeout(500)


        elif block["type"] == "image":

            image_path = (
                module_path /
                block["path"]
            ).resolve()


            if not image_path.exists():

                print(
                    "Missing image:",
                    image_path
                )

                continue


            if image_path.suffix.lower() not in {
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".gif",
            }:

                print(
                    "Skipping non-image asset:",
                    image_path
                )

                continue


            pasted = paste_image(
                page,
                editor,
                image_path
            )

            if not pasted:
                continue


            move_cursor_to_end(editor)

            page.wait_for_timeout(1000)


    print(
        "Draft inserted"
    )


    input(
        "Review Substack draft. ENTER to exit..."
    )



if __name__ == "__main__":

    publish_substack(
        "YOUR_MODULE_NAME"
    )