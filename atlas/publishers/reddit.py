from pathlib import Path
import re

from atlas.browser.edge import get_edge_page, stabilize_page
from atlas.utils.paths import MODULES_DIR

from atlas.utils.urls import (
    WEBSITE_LINK,
    GITHUB_LINK,
    INSTAGRAM_ID_LINK,
    YOUTUBE_ID,
)

# ============================================================
# Markdown parsing
# ============================================================

IMAGE_PATTERN = re.compile(
    r"!\[(.*?)\]\((.*?)\)"
)


def read_blog(path: Path):

    md = path.read_text(
        encoding="utf-8"
    ).strip()


    lines = md.splitlines()


    title = (
        lines[0]
        .lstrip("#")
        .strip()
        if lines
        else "Atlas"
    )


    body = "\n".join(
        lines[1:]
    )


    return {
        "title": title,
        "body": body
    }



def parse_markdown(
    markdown_text,
    module_path
):

    images = []


    def extract_image(match):

        relative = match.group(2)


        image_path = (
            module_path /
            relative
        ).resolve()


        if image_path.exists():

            print(
                "Found image:",
                image_path
            )

            images.append(
                image_path
            )

        else:

            print(
                "Missing image:",
                image_path
            )


        return ""


    text = IMAGE_PATTERN.sub(
        extract_image,
        markdown_text
    )


    # Keep blockquotes readable

    text = re.sub(
        r"^>\s?",
        "> ",
        text,
        flags=re.MULTILINE
    )

    # Remove markdown horizontal rules
    text = re.sub(
        r"^\s*---+\s*$",
        "",
        text,
        flags=re.MULTILINE
    )

    # Clean bold markers

    text = text.replace(
        "**",
        ""
    )    

    # Collapse excessive blank lines

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )


    return {
        "text": text.strip(),
        "images": images
    }


# ============================================================
# Reddit elements
# ============================================================

def wait_title(page):

    for _ in range(60):

        el = page.locator(
            'textarea[name="title"]'
        )


        if el.count() and el.first.is_visible():

            return el.first


        page.wait_for_timeout(
            1000
        )


    raise RuntimeError(
        "Title missing"
    )



def wait_body(page):

    print(
        "Searching Reddit body..."
    )


    for i in range(60):

        editors = page.locator(
            'div[aria-label="Post body text field"][contenteditable="true"]'
        )


        print(
            "body scan",
            i,
            editors.count()
        )


        for x in range(editors.count()):

            el = editors.nth(x)


            try:

                if el.is_visible():

                    box = el.bounding_box()


                    if box:

                        print(
                            "Using body",
                            x,
                            box
                        )


                        return el


            except:

                pass


        page.wait_for_timeout(
            1000
        )


    raise RuntimeError(
        "Body missing"
    )

# ============================================================
# Footer
# ============================================================

def reddit_footer():

    links = []


    if WEBSITE_LINK:
        links.append(
            f"Website: {WEBSITE_LINK}"
        )


    if GITHUB_LINK:
        links.append(
            f"Github: {GITHUB_LINK}"
        )


    if INSTAGRAM_ID_LINK:
        links.append(
            f"Instagram: {INSTAGRAM_ID_LINK}"
        )


    if YOUTUBE_ID:
        links.append(
            f"Youtube: {YOUTUBE_ID}"
        )


    if not links:
        return ""


    return (
        "\n\n---\n\n"
        "Follow Atlas for more:\n" +
        "\n".join(links)
    )

# ============================================================
# Body insertion
# ============================================================

def insert_body(
    page,
    body,
    text
):

    print(
        "Clicking body"
    )


    body.click(
        force=True
    )


    page.wait_for_timeout(
        1000
    )


    active = page.evaluate(
        """
        () => ({
            tag: document.activeElement.tagName,
            role: document.activeElement.getAttribute("role"),
            aria: document.activeElement.getAttribute("aria-label")
        })
        """
    )


    print(
        "ACTIVE:",
        active
    )


    page.keyboard.insert_text(
        text
    )


    page.wait_for_timeout(
        3000
    )


    visible = body.inner_text()


    print(
        "VISIBLE BODY:",
        repr(visible[:100])
    )


    if len(visible.strip()) < 5:

        raise RuntimeError(
            "Reddit rejected body input"
        )

# ============================================================
# Markdown toggle
# ============================================================

def switch_to_markdown(page):
    print("Switching to Markdown...")

    # If we're already in Markdown mode, there won't be a rich-text editor.
    try:
        if page.locator('textarea[placeholder*="Markdown"]').count():
            print("Already in Markdown mode.")
            return
    except Exception:
        pass

    # Open the three-dot menu.
    menu_button = page.get_by_role(
        "button",
        name="More options",
    )

    menu_button.wait_for(
        state="visible",
        timeout=10000,
    )

    menu_button.click()

    # Click "Switch to Markdown".
    markdown_item = page.get_by_role(
        "menuitem",
        name="Switch to Markdown",
    )

    markdown_item.wait_for(
        state="visible",
        timeout=5000,
    )

    markdown_item.click()

    # Reddit usually asks for confirmation.
    try:
        page.get_by_role(
            "button",
            name=re.compile(r"continue|switch", re.I),
        ).click(timeout=3000)

        print("Confirmed Markdown switch.")

    except Exception:
        pass

    page.wait_for_timeout(1000)

    print("Markdown mode enabled.")

# ============================================================
# Upload
# ============================================================

def upload_image(
    page,
    image
):

    print(
        "Uploading:",
        image
    )


    inputs = page.locator(
        'input[type="file"]'
    )


    print(
        "Uploads:",
        inputs.count()
    )


    if inputs.count() == 0:

        raise RuntimeError(
            "No Reddit upload inputs found"
        )


    inputs.nth(0).set_input_files(
        str(image)
    )


    page.wait_for_timeout(
        5000
    )


    print(
        "Image uploaded."
    )


# ============================================================
# Community
# ============================================================

def select_community(page, community_name: str):

    print("Opening community picker")

    page.get_by_role(
        "button",
        name="Select Community"
    ).click(
        force=True
    )

    page.wait_for_timeout(2000)


    search = page.locator(
        'textarea[placeholder="Search"]'
    ).first


    search.wait_for(
        state="visible",
        timeout=10000
    )


    print(
        "Typing:",
        community_name
    )


    search.fill(
        community_name
    )


    page.wait_for_timeout(
        3000
    )


    print(
        "Looking for result..."
    )


    result = page.get_by_text(
        "r/" + community_name,
        exact=True
    ).last


    result.wait_for(
        state="visible",
        timeout=10000
    )


    print(
        "Found:",
        result.inner_text()
    )


    # Reddit's clickable area is usually the nearest
    # div with a pointer cursor
    clicked = False


    for level in range(1, 8):

        candidate = result.locator(
            "xpath=" + "/.." * level
        )


        try:

            if candidate.is_visible():

                box = candidate.bounding_box()

                if box:

                    print(
                        "Trying parent",
                        level,
                        box
                    )


                    candidate.click(
                        force=True
                    )

                    clicked = True
                    break


        except Exception:

            pass


    if not clicked:

        print(
            "Falling back to text click"
        )

        result.click(
            force=True
        )


    page.wait_for_timeout(
        5000
    )


    print(
        "Community selected"
    )


def click_post(page):

    print(
        "Waiting for Post button..."
    )


    button = page.get_by_role(
        "button",
        name="Post",
        exact=True
    )


    button.wait_for(
        state="visible",
        timeout=15000
    )


    print(
        "Post button found"
    )


    button.click(
        force=True
    )


    print(
        "Post clicked"
    )


    page.wait_for_timeout(
        5000
    )

# ============================================================
# Publisher
# ============================================================

def publish_reddit(
    module_name: str,
    community_name: str
):


    module_path = (
        MODULES_DIR /
        module_name
    )


    blog_path = (
        module_path /
        "blog.md"
    )


    if not blog_path.exists():

        raise FileNotFoundError(
            blog_path
        )


    blog = read_blog(
        blog_path
    )


    content = parse_markdown(
        blog["body"],
        module_path
    )


    page = get_edge_page(reuse=True)

    try:
        page.goto(
            "about:blank"
        )

        page.wait_for_timeout(1000)

        page.goto(
            "https://www.reddit.com/submit?type=TEXT",
            wait_until="domcontentloaded"
        )

        stabilize_page(page)

        print(
            "Reddit loaded"
        )


        page.wait_for_timeout(
            5000
        )

        select_community(
            page,
            community_name
        )


        print(
            "Reddit Community Selected"
        )


        # -------------------------
        # Title
        # -------------------------

        title = wait_title(
            page
        )


        title.fill(
            blog["title"]
        )


        print(
            "Title done:",
            blog["title"]
        )


        switch_to_markdown(
            page
            )
        


        # -------------------------
        # Body
        # -------------------------

        body = wait_body(page)
        text = content["text"]
        footer = reddit_footer()

        if footer:

            text += footer

        insert_body(
            page,
            body,
            text
        )


        # -------------------------
        # Images
        # -------------------------

        for image in content["images"]:

            try:

                upload_image(
                    page,
                    image
                )

            except Exception as e:

                print(
                    "⚠ Skipping image:",
                    image
                )

                print(
                    "  Reason:",
                    e
                )

                continue



        print(
            "Reddit draft ready"
        )


        click_post(page)


        print(
            "Reddit post submitted"
        )


        page.wait_for_timeout(
            5000
        )

        print(
            "Done."
        )

    finally:
        try:
            page.goto("about:blank")
        except Exception:
            pass




if __name__ == "__main__":

    publish_reddit(
        "gradient-descent",
        "learnmachinelearning"
    )