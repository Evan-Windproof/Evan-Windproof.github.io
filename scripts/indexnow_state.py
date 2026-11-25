"""Store deployment and notification state in an append-only Git branch."""

import json
import subprocess

if __package__:
    from . import indexnow, indexnow_manifest as manifest
else:
    import indexnow
    import indexnow_manifest as manifest


REF = "refs/heads/indexnow-state"
FILE = "state.json"


def empty_state():
    return {
        "schema_version": 1,
        "deployment": {"published": None, "candidates": {}},
        "notifications": {"pending": {}, "accepted": {}},
    }


def validate(state):
    try:
        if state["schema_version"] != 1:
            raise ValueError
        deployment = state["deployment"]
        published = deployment["published"]
        if published is not None:
            manifest.validate_manifest(published)
        for commit, candidate in deployment["candidates"].items():
            manifest.validate_manifest(candidate)
            if commit != candidate["commit"]:
                raise ValueError
        for group in ("pending", "accepted"):
            for url, record in state["notifications"][group].items():
                manifest.validate_article_url(url)
                if not manifest.SHA.fullmatch(record["event"]) or not manifest.SHA.fullmatch(record["proof"]):
                    raise ValueError
                if record["kind"] not in {"current", "historical"}:
                    raise ValueError
                if group == "pending" and type(record["blocked"]) is not bool:
                    raise ValueError
                if group == "accepted" and record["http_status"] not in {200, 202}:
                    raise ValueError
    except (KeyError, TypeError, AttributeError, ValueError, indexnow.IndexNowError):
        raise indexnow.IndexNowError("Invalid IndexNow state. Restore a verified state revision.") from None


class GitState:
    def __init__(self, root):
        self.root = root
        self.revision = None
        self.saved = None

    def git(self, *args, data=None, missing=False):
        try:
            result = subprocess.run(
                ["git", *args], cwd=self.root, input=data, capture_output=True, timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise indexnow.IndexNowError(f"IndexNow state Git operation timed out or failed ({args[0]}).") from None
        if missing and result.returncode == 2:
            return None
        if result.returncode:
            raise indexnow.IndexNowError(f"IndexNow state Git operation failed ({args[0]}).")
        return result.stdout

    def load(self):
        if self.git("ls-remote", "--exit-code", "origin", REF, missing=True) is None:
            self.revision = self.saved = None
            return empty_state()
        self.git("fetch", "--no-tags", "--depth=1", "origin", REF)
        self.revision = self.git("rev-parse", "FETCH_HEAD").decode("ascii").strip()
        try:
            state = json.loads(self.git("show", f"{self.revision}:{FILE}"))
        except (UnicodeError, ValueError):
            raise indexnow.IndexNowError("Invalid IndexNow state JSON. Restore a verified state revision.") from None
        validate(state)
        self.saved = manifest.encode(state)
        return state

    def save(self, state):
        validate(state)
        data = manifest.encode(state)
        if data == self.saved:
            return
        blob = self.git("hash-object", "-w", "--stdin", data=data).strip()
        tree = self.git("mktree", data=b"100644 blob " + blob + b"\t" + FILE.encode() + b"\n").decode().strip()
        parents = ["-p", self.revision] if self.revision else []
        commit = self.git(
            "-c", "user.name=github-actions[bot]",
            "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "commit-tree", tree, *parents, "-m", "Record IndexNow deployment state",
        ).decode().strip()
        # A stale writer's commit has a different parent. Git rejects it without force.
        self.git("push", "origin", f"{commit}:{REF}")
        self.revision, self.saved = commit, data
