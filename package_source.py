"""Create a shareable source archive without local secrets or runtime files."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "dist"
OUTPUT_FILE = OUTPUT_DIR / "argue-with-data-source.zip"
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", "dist"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
EXCLUDED_RELATIVE_PATHS = {".streamlit/secrets.toml"}


def include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        not path.is_symlink()
        and not any(part.lower() in EXCLUDED_PARTS for part in relative.parts)
        and relative.name.lower() != ".env"
        and path.suffix.lower() not in EXCLUDED_SUFFIXES
        and relative.as_posix().lower() not in EXCLUDED_RELATIVE_PATHS
    )


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    files = sorted(path for path in ROOT.rglob("*") if path.is_file() and include(path))
    with ZipFile(OUTPUT_FILE, "w", compression=ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(f"Created {OUTPUT_FILE} with {len(files)} source files.")


if __name__ == "__main__":
    main()
