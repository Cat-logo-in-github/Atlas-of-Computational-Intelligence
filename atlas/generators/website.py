from atlas.utils.paths import WEBSITE_DIR
from atlas.utils.filesystem import (
    write_if_changed,
    copy_if_changed,
)

from atlas.generators.notebook import (
    copy_notebook,
    build_notebook_page,
    build_notebook_html,
)

from atlas.validators.module import (
    module_needs_build,
    mark_module_built,
)

IGNORE = {
    "run.py",
    "__pycache__",
    ".DS_Store",
    ".ipynb_checkpoints",
    "requirements.txt",
    "venv",
    ".venv",
}


IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
}



def build_assets(module):

    source = module.assets

    if not source.exists():
        return


    if not any(source.iterdir()):
        return


    destination = (
        WEBSITE_DIR
        /
        "content"
        /
        module.slug
        /
        "assets"
    )


    for asset in source.iterdir():

        if not asset.is_file():
            continue


        target = destination / asset.name


        if copy_if_changed(
            asset,
            target
        ):
            print(
                f" ✓ {module.slug}/assets/{asset.name} updated"
            )


def copy_simulation(module):

    simulation = module.simulation / "outputs"

    if not simulation.exists():
        return


    content_destination = (
        WEBSITE_DIR
        /
        "content"
        /
        module.slug
        /
        "simulation"
    )


    model_destination = (
        WEBSITE_DIR
        /
        "quartz"
        /
        "static"
        /
        "simulations"
        /
        module.slug
    )


    models = {
        model.name
        for model in get_simulation_models(module)
    }


    for file in simulation.rglob("*"):

        if not file.is_file():
            continue


        relative = file.relative_to(simulation)


        if relative.parts and relative.parts[0] in models:

            target = (
                model_destination
                /
                relative
            )

        elif file.suffix.lower() == ".html":
            target = (model_destination / relative)

        else:

            target = (
                content_destination
                /
                relative
            )


        if copy_if_changed(
            file,
            target
        ):
            print(
                f" ✓ {target.relative_to(WEBSITE_DIR)}"
            )

def get_simulation_outputs(module):

    output = module.simulation / "outputs"

    if not output.exists():
        return []


    models = get_simulation_models(module)


    model_files = set()

    for model in models:
        for file in model.rglob("*"):
            if file.is_file():
                model_files.add(file)


    return [
        file
        for file in output.rglob("*")
        if (
            file.is_file()
            and file not in model_files
        )
    ]



def get_simulation_models(module):

    output = module.simulation / "outputs"

    if not output.exists():
        return []

    return [
        folder
        for folder in output.iterdir()
        if (
            folder.is_dir()
            and (folder / "index.html").exists()
        )
    ]

def classify_output(file):

    name = file.name.lower()
    suffix = file.suffix.lower()


    if name == "atlas_metadata.json":
        return "ignore"


    if suffix == ".html":
        return "interactive"


    if suffix in IMAGE_EXTENSIONS:
        return "figure"


    if suffix in {".json", ".csv"}:
        return "data"


    return "other"

def build_simulation_page(module):

    outputs = get_simulation_outputs(module)
    models = get_simulation_models(module)

    if not outputs and not models:
        return


    simulation_output = module.simulation / "outputs"


    lines = [
        "---\n",
        f'title: "{module.title} Simulation"\n',
        "---\n\n",
        "This page contains generated simulation outputs.\n\n\n\n",
    ]


    if models:

        lines.append(
            "## Interactive Models\n\n\n\n"
        )


        for model in models:

            relative = model.relative_to(
                simulation_output
            ).as_posix()


            lines.extend(
                [
                    f"### {model.name}:\n\n",
                    (
                        f'<iframe src="/static/simulations/{module.slug}/{relative}/index.html" '
                        'width="100%" '
                        'height="700" '
                        'style="border:none;"></iframe>\n\n'
                    )
                ]
            )


    interactive = [
        f
        for f in outputs
        if classify_output(f) == "interactive"
    ]


    if interactive:

        lines.append(
            "## Interactive Visualizations\n\n\n\n"
        )


        for file in interactive:

            relative = file.relative_to(
                simulation_output
            ).as_posix()


            lines.extend(
                [
                    f"### {file.stem}\n\n",
                    (
                        f'<iframe src="/static/simulations/{module.slug}/{relative}" '
                        'width="100%" '
                        'height="700" '
                        'style="border:none;"></iframe>\n\n'
                    )
                ]
            )


    figures = [
        f
        for f in outputs
        if classify_output(f) == "figure"
    ]


    if figures:

        lines.append(
            "\n\n## Figures\n\n\n\n"
        )


        for file in figures:

            relative = file.relative_to(
                simulation_output
            ).as_posix()


            lines.extend(
                [
                    f"### {file.stem}\n\n",
                    f"![](/{module.slug}/simulation/{relative})\n\n"
                    .replace("/ ", "/")
                ]
            )


    data = [
        f
        for f in outputs
        if classify_output(f) == "data"
    ]


    if data:

        lines.append(
            "\n\n## Data\n\n\n\n"
        )


        for file in data:

            relative = file.relative_to(
                simulation_output
            ).as_posix()


            lines.append(
                f"- [{file.name}](/{module.slug}/simulation/{relative})\n"
                .replace("/ ", "/")
            )


    destination = (
        WEBSITE_DIR
        /
        "content"
        /
        module.slug
        /
        "simulation.md"
    )


    write_if_changed(
        destination,
        "".join(lines)
    )



def build_knowledge_page(module):

    if not module.knowledge.exists():
        return


    content = f"""---
title: "{module.title}"
---

<!--
GENERATED BY ATLAS
SOURCE: {module.knowledge}
-->

{module.knowledge.read_text(encoding="utf-8")}
{build_external_links(module)}
"""



    destination = (
        WEBSITE_DIR
        /
        "content"
        /
        module.slug
        /
        "index.md"
    )


    if write_if_changed(
        destination,
        content
    ):
        print(
            f" ✓ {module.slug}/index.md updated"
        )



def build_blog_page(module):

    if not module.blog.exists():
        return


    content = f"""---
title: "{module.title} - Blog"
---

<!--
GENERATED BY ATLAS
SOURCE: {module.blog}
-->

{module.blog.read_text(encoding="utf-8")}
"""


    destination = (
        WEBSITE_DIR
        /
        "content"
        /
        module.slug
        /
        f"{module.slug}-blog.md"
    )


    if write_if_changed(
        destination,
        content
    ):
        print(
            f" ✓ {module.slug}/{module.slug}-blog.md updated"
        )

def build_index(modules):

    lines = [
        "# Atlas of Computational Intelligence\n\n",
        "## Modules\n\n"
    ]


    for module in modules:

        lines.append(
            f"- [{module.title}]({module.slug}/)\n"
        )


    destination = (
        WEBSITE_DIR
        /
        "content"
        /
        "index.md"
    )


    if write_if_changed(
        destination,
        "".join(lines)
    ):
        print(
            " ✓ index.md updated"
        )



def build_blog_index(modules):

    lines = [
        "# Atlas Blog\n\n",
        "## Articles\n\n"
    ]


    for module in modules:

        lines.append(
            f"- [{module.title}]({module.slug}/{module.slug}-blog)\n"
        )


    destination = (
        WEBSITE_DIR
        /
        "content"
        /
        "blog.md"
    )


    if write_if_changed(
        destination,
        "".join(lines)
    ):
        print(
            " ✓ blog.md updated"
        )

def build_external_links(module):

    links = []

    outputs = module.metadata.outputs

    if outputs.youtube.published and outputs.youtube.url:
        links.append(
            f"- [YouTube]({outputs.youtube.url})"
        )

    if outputs.instagram.published and outputs.instagram.url:
        links.append(
            f"- [Instagram]({outputs.instagram.url})"
        )

    if outputs.blog.published and outputs.blog.url:
        links.append(
            f"- [Blog]({outputs.blog.url})"
        )

    if not links:
        return ""

    return (
        "\n\n## External Links\n\n"
        +
        "\n".join(links)
    )


def build_website(modules):

    print("\nWebsite")


    for module in modules:

        if not module_needs_build(module):

            print(
                f" O {module.slug} unchanged"
            )

            continue


        build_knowledge_page(module)

        build_blog_page(module)


        if module.metadata.outputs.notebook.published:
            copy_notebook(module)
            build_notebook_page(module)
            build_notebook_html(module)

        if module.metadata.outputs.simulation.published:
            copy_simulation(module)
            build_simulation_page(module)

        build_assets(module)


        mark_module_built(module)

    # Website entry points

    build_index(
        modules
    )

    build_blog_index(
        modules
    )