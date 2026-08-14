import subprocess

from atlas.utils.paths import PROJECT_ROOT


def run_git(*args):

    return subprocess.run(
        [
            "git",
            *args
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True
    )


def publish_module(module_name):

    print(
        f"\nPublishing {module_name} to GitHub"
    )


    # Stage only publishable content
    run_git(
        "add",
        f"modules/{module_name}",
        "website"
    )


    # Check what is staged
    staged = run_git(
        "diff",
        "--cached",
        "--name-only"
    ).stdout.splitlines()


    if not staged:

        # Check if repo has other changes
        unstaged = run_git(
            "status",
            "--porcelain"
        ).stdout.splitlines()


        if unstaged:

            print(
                "\n⚠ Atlas internals changed."
            )

            print(
                "Not publishing module/website."
            )

            for file in unstaged:
                print(
                    f"  {file}"
                )

        else:

            print(
                "\nNo changes to publish."
            )

        return


    print(
        "\nPublishing:"
    )

    for file in staged:
        print(
            f"  {file}"
        )


    run_git(
        "commit",
        "-m",
        f"Publish {module_name}"
    )


    run_git(
        "push",
        "origin",
        "HEAD"
    )


    print(
        "\n✓ Published"
    )