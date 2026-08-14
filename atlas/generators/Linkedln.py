import typer

from atlas.models.module import Module
from atlas.utils.paths import MODULES_DIR
from atlas.llm.ollama import generate


def generate_linkedln(
    slug: str,
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite an existing linkedln.md",
    ),
):

    module_path = MODULES_DIR / slug

    if not module_path.exists():
        raise typer.Exit(
            f"Unknown module: {slug}"
        )


    module = Module(module_path)


    destination = (
        module.generated
        /
        "linkedln.md"
    )


    if destination.exists() and not force:

        print(
            f" O {module.title}/linkedln.md exists"
        )

        return



    knowledge = ""

    if module.knowledge.exists():

        knowledge = module.knowledge.read_text(
            encoding="utf-8"
        )


    blog = ""

    if module.blog.exists():

        blog = module.blog.read_text(
            encoding="utf-8"
        )



    print(
        f" ▶ Generating LinkedIn posts: {module.title}"
    )



    prompt = f"""
You are a technical creator building a public learning portfolio.

Create LinkedIn posts from the following knowledge material.

The goal is NOT to sound like a motivational influencer.

The goal is to document:
- learning
- building
- experiments
- technical understanding
- curiosity

Make posts like a student/researcher really passionate babout the idea

Topic:
{module.title}



Knowledge Notes:
----------------
{knowledge}



Blog Draft:
-----------
{blog}



Generate 5 LinkedIn post options.

Each post should have a different angle:



# Post 1: Learning Journey

Write a post about:
"What I learned while exploring this topic."

Focus on:
- curiosity
- the mental model
- the surprising insight



# Post 2: Technical Explanation

Explain one important concept simply.

Structure:

Hook

Explanation

Why it matters



# Post 3: Project / Builder Update

Write as someone building Atlas.

Mention:
- what was explored
- what was built
- what problem it solves

Do not exaggerate.



# Post 4: Discussion Question

Create a thoughtful question that encourages discussion.

It should be based on a real open question,
tradeoff, or idea from the topic.



# Post 5: Reflection

Write a personal reflection about how this topic
changes the way someone thinks about intelligence,
learning, engineering, or science.



For every post include:

## Text

The complete LinkedIn post.

## Suggested Asset

Suggest a simple graphic/thumbnail to go with each. Image should be a simple visual metaphor. (no explanation)


Rules:
- Avoid generic AI hype.
- Avoid "AI is changing everything".
- Avoid emojis unless they naturally fit.
- Avoid hashtags spam.
- Write like a student engineer sharing genuine work.
- Keep posts between 100-250 words.
"""



    result = generate(
        prompt
    )


    content = f"""# {module.title}

{result}
"""


    destination.write_text(
        content,
        encoding="utf-8"
    )


    print(
        f" ✓ Generated {destination}"
    )