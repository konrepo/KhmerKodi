import re
import sys
import zipfile
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
GENERATOR = REPO_ROOT / "addons_xml_generator.py"


def run(cmd, cwd=None):
    print(f"\n> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd or REPO_ROOT, check=True)


def read_text(path):
    return path.read_text(encoding="utf-8")


def write_text(path, content):
    path.write_text(content, encoding="utf-8", newline="\n")


def bump_patch_version(version):
    parts = version.strip().split(".")
    if len(parts) < 3:
        parts += ["0"] * (3 - len(parts))
    parts = [int(p) for p in parts[:3]]
    parts[2] += 1
    return ".".join(str(p) for p in parts)


def get_addon_version(addon_xml_path):
    content = read_text(addon_xml_path)
    match = re.search(r'(<addon\b[^>]*\bversion=")([^"]+)(")', content, re.IGNORECASE)
    if not match:
        raise RuntimeError(f"Could not find addon version in {addon_xml_path}")
    return match.group(2)


def set_addon_version(addon_xml_path, new_version):
    content = read_text(addon_xml_path)
    new_content, count = re.subn(
        r'(<addon\b[^>]*\bversion=")([^"]+)(")',
        rf"\g<1>{new_version}\g<3>",
        content,
        count=1,
        flags=re.IGNORECASE
    )
    if count != 1:
        raise RuntimeError(f"Could not update addon version in {addon_xml_path}")
    write_text(addon_xml_path, new_content)


def zip_folder_with_root(source_dir, zip_path):
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in source_dir.rglob("*"):
            if file_path.is_dir():
                continue

            rel_parts = file_path.relative_to(source_dir).parts

            if "__pycache__" in rel_parts:
                continue
            if file_path.suffix.lower() == ".pyc":
                continue
            if file_path.name == ".DS_Store":
                continue

            arcname = str(Path(source_dir.name) / file_path.relative_to(source_dir))
            zf.write(file_path, arcname)

    print(f"Created: {zip_path}")


def release_addon(addon_id):
    addon_dir = REPO_ROOT / addon_id
    addon_xml = addon_dir / "addon.xml"
    zips_dir = REPO_ROOT / "zips" / addon_id

    if not addon_dir.is_dir():
        raise RuntimeError(f"Addon folder not found: {addon_dir}")
    if not addon_xml.is_file():
        raise RuntimeError(f"addon.xml not found: {addon_xml}")
    if not GENERATOR.is_file():
        raise RuntimeError(f"Generator not found: {GENERATOR}")

    zips_dir.mkdir(parents=True, exist_ok=True)

    old_version = get_addon_version(addon_xml)
    new_version = bump_patch_version(old_version)

    print(f"Addon: {addon_id}")
    print(f"Old version: {old_version}")
    print(f"New version: {new_version}")

    set_addon_version(addon_xml, new_version)

    zip_name = f"{addon_id}-{new_version}.zip"
    zip_path = zips_dir / zip_name

    zip_folder_with_root(addon_dir, zip_path)

    run([sys.executable, str(GENERATOR)])

    commit_msg = f"Release {addon_id} {new_version}"
    run(["git", "add", "."])
    run(["git", "commit", "-m", commit_msg])
    run(["git", "push"])

    print("\nDone.")
    print(f"Released {addon_id} {new_version}")


if __name__ == "__main__":
    addon = "plugin.video.KDubbed"
    if len(sys.argv) > 1:
        addon = sys.argv[1]
    release_addon(addon)