"""Stage and verify the assets published by the production Worker."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

import indexnow

ROOT = Path(__file__).resolve().parents[1]
METADATA = Path("_meta/deployment.json")
ROOT_FILES = {
    Path(name) for name in ("index.html", "styles.css", "app.js", "rss.xml", "sitemap.xml", "robots.txt", "LICENSE")
}
BLOG_FILES = {
    Path("blog") / name for name in ("index.html", "tags/index.html", "articles.json", "blog.css", "blog.js", "highlight.css")
}
MEDIA = {".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico", ".woff", ".woff2"}
PUBLIC_TREES = {
    "articles": {".js", ".md"},
    "assets": MEDIA,
    "js": {".js"},
    "locales": {".js"},
    "projects": MEDIA | {".html", ".css", ".js"},
}
PRIVATE_DIRS = {"content", "node_modules", "scripts", "tests", "work", "venv", "__pycache__"}


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True)


def checked_commit(root):
    commit = git(root, "rev-parse", "--verify", "HEAD").strip()
    if os.environ.get("WORKERS_CI") == "1":
        if os.environ.get("WORKERS_CI_BRANCH") != "main":
            raise ValueError("The production Worker requires a Workers Builds push to main.")
        if os.environ.get("WORKERS_CI_COMMIT_SHA") != commit:
            raise ValueError("The checked-out commit differs from the Workers Builds commit.")
        if not os.environ.get("WORKERS_CI_BUILD_UUID"):
            raise ValueError("The Workers Builds ID is missing.")
    return commit


def tracked_public_files(root):
    # Only Git-tracked public resources can enter the artifact from these trees.
    for name in git(root, "ls-files", "-z", "--", *PUBLIC_TREES).split("\0"):
        if not name:
            continue
        path = Path(name)
        if any(part.startswith(".") or part in PRIVATE_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in PUBLIC_TREES[path.parts[0]]:
            yield path


def generated_html(root):
    manifest = json.loads((root / "blog/.generated.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, list) or not manifest:
        raise ValueError("Expected a nonempty blog generation manifest.")
    for name in manifest:
        path = Path(name)
        if (
            not path.parts or path.parts[0] != "blog" or path.name != "index.html"
            or any(part.startswith(".") for part in path.parts)
        ):
            raise ValueError(f"Unexpected generated HTML path: {path}")
        yield path


def public_files(root):
    key = indexnow.find_key(root)
    if not key:
        raise ValueError("The public IndexNow verification file is missing.")
    key_path = Path(f"{key}.txt")
    if not git(root, "ls-files", "-z", "--", str(key_path)):
        raise ValueError("The public IndexNow verification file must be tracked.")
    paths = ROOT_FILES | BLOG_FILES | {key_path}
    paths.update(tracked_public_files(root))
    paths.update(generated_html(root))
    for path in paths:
        source = root / path
        if source.resolve() != source or not source.is_file() or not source.stat().st_size:
            raise ValueError(f"Required public file is missing, empty, or a symlink: {path}")
    return paths


def validate(root, dist, paths, commit):
    expected = paths | {METADATA}
    directories = {parent for path in expected for parent in path.parents}
    if dist.is_symlink() or not dist.is_dir():
        raise ValueError("The staged asset directory is missing or is a symlink.")
    found = set()
    for entry in dist.rglob("*"):
        path = entry.relative_to(dist)
        if entry.is_symlink() or (entry.is_dir() and path not in directories):
            raise ValueError(f"Unexpected staged path: {path}")
        if not entry.is_dir():
            if not entry.is_file() or path not in expected:
                raise ValueError(f"Unexpected staged file: {path}")
            if path != METADATA and entry.read_bytes() != (root / path).read_bytes():
                raise ValueError(f"Staged file differs from the build output: {path}")
            found.add(path)
    if missing := expected - found:
        raise ValueError("Missing staged files: " + ", ".join(map(str, sorted(missing))))

    metadata = json.loads((dist / METADATA).read_text(encoding="utf-8"))
    if metadata["commit"] != commit:
        raise ValueError("The staged deployment commit does not match the checkout.")
    if metadata.get("build_id") != os.environ.get("WORKERS_CI_BUILD_UUID"):
        raise ValueError("The staged deployment metadata does not match the current build.")
    if datetime.fromisoformat(metadata["built_at"]).utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError("The staged deployment timestamp must be in UTC.")


def stage(root, dist, paths, commit):
    if dist.is_symlink():
        raise ValueError("Refusing to stage into a symlinked dist directory.")
    if dist.exists():
        shutil.rmtree(dist)

    work = root / "work"
    work.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=work) as temp:
        candidate = Path(temp) / "dist"
        for path in sorted(paths):
            target = candidate / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / path, target)
        metadata = {"commit": commit, "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        if build_id := os.environ.get("WORKERS_CI_BUILD_UUID"):
            metadata["build_id"] = build_id
        target = candidate / METADATA
        target.parent.mkdir()
        target.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        validate(root, candidate, paths, commit)
        candidate.rename(dist)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-source", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        commit = checked_commit(ROOT)
        if args.check_source:
            if os.environ.get("WORKERS_CI") == "1" and git(ROOT, "status", "--porcelain", "--untracked-files=all").strip():
                raise ValueError("Workers Builds must start with a clean Git checkout.")
            print(f"Building checkout {commit}")
            return

        dist = ROOT / "dist"
        paths = public_files(ROOT)
        if args.verify:
            validate(ROOT, dist, paths, commit)
        else:
            stage(ROOT, dist, paths, commit)
        print(f"Validated {len(paths) + 1} public files for {commit}")
    except (OSError, KeyError, TypeError, ValueError, subprocess.CalledProcessError, indexnow.IndexNowError) as error:
        parser.exit(1, f"Cloudflare asset validation failed: {error}\n")


if __name__ == "__main__":
    main()
