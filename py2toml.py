#!/usr/bin/env python
"""Converts a setup.py file to a pyproject.toml file."""
import ast
import os
import sys

try:
    from rich import print
except ImportError:
    print = print


def find_setup_function(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            try:
                found = node.func.id == "setup"
            except AttributeError:
                found = node.func.attr == "setup"

            if found:
                return node
    return None


def extract_metadata_from_setup(setup_node):
    metadata = {}
    for keyword in setup_node.keywords:
        if not isinstance(keyword.arg, str):
            print(f"Error: Keyword '{keyword.arg}' is not an instance of ast.keyword")
            continue
        elif keyword.arg == "author" or keyword.arg == "author_email":
            value = [author.strip() for author in keyword.value.value.split(",")]
            print(f"Adding to '{keyword.arg}' the list '{value}'")
        elif keyword.arg == "keywords":
            if isinstance(keyword.value.value, str):
                keywords = keyword.value.value.split(",")
                if len(keywords) == 1:
                    keywords = keyword.value.value.split()
                keywords = [k.strip() for k in keywords]
            else:
                keywords = keyword.value.value
            value = [k.strip() for k in keywords]
            print(f"Adding to '{keyword.arg}' the list '{value}'")
        elif isinstance(keyword.value, ast.Constant):
            print(f"Adding to '{keyword.arg}' the constant '{keyword.value.value}'")
            if isinstance(keyword.value.value, str):
                value = " ".join(keyword.value.value.split())
            else:
                value = keyword.value.value
        elif isinstance(keyword.value, ast.List) or isinstance(
            keyword.value, ast.Tuple
        ):
            value = [elt.value.strip() for elt in keyword.value.elts]
            print(f"Adding to '{keyword.arg}' the list '{value}'")
        elif isinstance(keyword.value, ast.Name):
            print(f"Adding to '{keyword.arg}' the name '{keyword.value.id}'")
            value = keyword.value.id

        metadata[keyword.arg] = value

    if "author_email" in metadata:
        # Match the author emails to the authors
        authors = metadata["author"]
        emails = metadata["author_email"]
        if len(authors) != len(emails):
            print(
                "Error: The number of authors does not match the number of author emails."
            )
        else:
            metadata["author"] = [
                f"{author} <{email}>" for author, email in zip(authors, emails)
            ]

    print(f"Metadata: {metadata}")

    return metadata


def parse_setup_py(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        setup_content = file.read()

    # Parse the setup.py file using AST
    setup_info = ast.parse(setup_content)

    # Find the setup function in the AST
    setup_node = find_setup_function(setup_info)
    if setup_node:
        metadata = extract_metadata_from_setup(setup_node)
        return metadata
    else:
        print("Error: Could not find the setup function in the AST.")
        return {}


def generate_pyproject_toml(metadata):
    classifiers = metadata.get("classifiers", [])
    if classifiers:
        classifiers = "[\n" + "\n".join(f'    "{cls}",' for cls in classifiers) + "\n]"

    pyproject_toml = f"""[tool.poetry]
name = "{metadata.get('name', '')}"
version = "{metadata.get('version', '')}"
description = "{metadata.get('description', '')}"
license = "{metadata.get('license', '')}"
authors = {metadata.get('author', '[]')}
readme = "README.md"
repository = "{metadata.get('url', '')}"
keywords = {metadata.get('keywords', '[]')}
classifiers = {classifiers}

[tool.poetry.dependencies]
python = "{metadata.get('python_requires', '>=3.5')}"
{generate_dependency_section(metadata.get('install_requires', []))}

[tool.poetry.scripts]
{scripts_section(metadata.get('scripts', []))}

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
"""

    return pyproject_toml.replace("\n\n\n", "\n\n")


def generate_dependency_section(install_requires):
    return "\n".join(f'{req} = "*"' for req in install_requires)


def scripts_section(scripts):
    return "\n".join(
        f'{os.path.splitext(os.path.basename(script))[0]} = "{script}.__main__:main"'
        for script in scripts
    )


def write_to_file(content, file_path):
    with open(file_path, "w") as file:
        file.write(content)


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python script.py <path_to_setup_py> <path_to_output_pyproject_toml>"
        )
        sys.exit(1)

    setup_file_path = sys.argv[1]
    pyproject_toml_path = sys.argv[2]

    pyproject_toml_content = generate_pyproject_toml(parse_setup_py(setup_file_path))
    write_to_file(pyproject_toml_content, pyproject_toml_path)

    print(f"Conversion complete. Pyproject.toml saved to {pyproject_toml_path}")


if __name__ == "__main__":
    main()
