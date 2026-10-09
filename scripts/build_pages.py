"""Package the public, browser-only demo without copying server files or secrets."""

import re
import shutil
from pathlib import Path


DOCUMENTS = (
    "README.md",
    "CHANGELOG.md",
    "WINDOWS_INSTALLATION.md",
    "HELP.md",
    "REI_RESEARCH_EXPLORER_PROMPT.md",
    "COMMERCIAL_LICENSING.md",
    "THIRD_PARTY_NOTICES.md",
)
OPTIONAL_DOCUMENTS = ("LICENSE",)
HOSTED_MARKER = '<meta name="rei-hosted-demo" content="github-pages">'
PUBLIC_FOLDERS = {"licenses": {".txt"}, "assets": {".js", ".css"}, "documentation": {".md"}}


def _public_file(root, path):
    """Only regular files within this checkout can become public artifacts."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("Public source must be a regular file: {}".format(path.name))
    try:
        path.resolve().relative_to(root)
    except ValueError:
        raise ValueError("Public source leaves the checkout: {}".format(path.name))
    return path


def _clear_generated_site(root, target):
    """Refuse links, alternate targets, and unexpected files before cleaning."""
    if target.is_symlink() or target.resolve() != root / "_site":
        raise ValueError("Build output must stay in the checkout's _site directory.")
    if not target.exists():
        return
    if not target.is_dir():
        raise ValueError("Build output is not a directory.")
    if not (target / "index.html").is_file() or not (target / ".nojekyll").is_file():
        raise ValueError("Refusing to clean an unrecognized _site directory.")

    allowed = set(DOCUMENTS + OPTIONAL_DOCUMENTS + ("index.html", ".nojekyll"))
    files = []
    directories = []
    for child in target.iterdir():
        if child.is_symlink() or child.resolve().parent != target:
            raise ValueError("Refusing to clean linked build output.")
        if child.name in PUBLIC_FOLDERS and child.is_dir():
            directories.append(child)
            for license_file in child.iterdir():
                if (
                    license_file.is_symlink()
                    or not license_file.is_file()
                    or license_file.suffix not in PUBLIC_FOLDERS[child.name]
                    or license_file.resolve().parent != child
                ):
                    raise ValueError("Refusing to clean unexpected license output.")
                files.append(license_file)
        elif child.name in allowed and child.is_file():
            files.append(child)
        else:
            raise ValueError("Refusing to clean unexpected build output: {}".format(child.name))

    # All paths are checked before any removal. No recursive deletion is used.
    for path in files:
        path.unlink()
    for directory in directories:
        directory.rmdir()
    target.rmdir()


def build_site(checkout):
    root = Path(checkout).resolve()
    target = root / "_site"
    public_documents = [_public_file(root, root / name) for name in DOCUMENTS]
    public_documents.extend(
        _public_file(root, root / name)
        for name in OPTIONAL_DOCUMENTS
        if (root / name).exists() or (root / name).is_symlink()
    )
    index = _public_file(root, root / "index.html").read_text(encoding="utf-8")
    head = re.search(r"<head\b[^>]*>", index, re.IGNORECASE)
    if head is None:
        raise ValueError("The public index must have an HTML head.")
    hosted_index = index[: head.end()] + "\n" + HOSTED_MARKER + index[head.end() :]

    licenses = root / "licenses"
    if licenses.is_symlink() or not licenses.is_dir() or licenses.resolve().parent != root:
        raise ValueError("Dependency licenses must stay in the checkout's licenses directory.")
    public_licenses = [_public_file(root, path) for path in sorted(licenses.glob("*.txt"))]

    _clear_generated_site(root, target)
    target.mkdir()
    (target / "index.html").write_text(hosted_index, encoding="utf-8")
    (target / ".nojekyll").write_text("", encoding="utf-8")
    for document in public_documents:
        shutil.copyfile(document, target / document.name)
    (target / "licenses").mkdir()
    for license_file in public_licenses:
        shutil.copyfile(license_file, target / "licenses" / license_file.name)
    for name in ("assets", "documentation"):
        directory = root / name
        if directory.is_symlink():
            raise ValueError("Linked public assets rejected.")
        if directory.is_dir():
            (target / name).mkdir()
            for path in directory.iterdir():
                if path.suffix in PUBLIC_FOLDERS[name]:
                    shutil.copyfile(_public_file(root, path), target / name / path.name)
    return target


if __name__ == "__main__":
    output = build_site(Path(__file__).resolve().parent.parent)
    print("Public GitHub Pages demo packaged in {}".format(output))
