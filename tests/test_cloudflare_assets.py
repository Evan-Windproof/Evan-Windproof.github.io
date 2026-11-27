import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_cloudflare_assets as assets


class CloudflareAssetsTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.dist = self.root / "dist"
        self.article = Path("blog/new-post/index.html")
        self.source = self.root / self.article
        self.source.parent.mkdir(parents=True)
        self.source.write_text("generated article", encoding="utf-8")
        self.paths = {self.article}
        self.commit = "a" * 40

    def test_restage_removes_old_assets_and_records_commit(self):
        self.dist.mkdir()
        (self.dist / "old.html").touch()
        assets.stage(self.root, self.dist, self.paths, self.commit)
        self.assertFalse((self.dist / "old.html").exists())
        self.assertEqual((self.dist / self.article).read_bytes(), self.source.read_bytes())
        metadata = json.loads((self.dist / assets.METADATA).read_text(encoding="utf-8"))
        self.assertEqual(metadata["commit"], self.commit)
        with self.assertRaisesRegex(ValueError, "commit does not match"):
            assets.validate(self.root, self.dist, self.paths, "b" * 40)

    def test_verify_rejects_stale_missing_and_unexpected_assets(self):
        assets.stage(self.root, self.dist, self.paths, self.commit)
        staged = self.dist / self.article
        staged.write_text("old article", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "differs from the build output"):
            assets.validate(self.root, self.dist, self.paths, self.commit)
        staged.unlink()
        with self.assertRaisesRegex(ValueError, "Missing staged files"):
            assets.validate(self.root, self.dist, self.paths, self.commit)
        (self.dist / "content").mkdir()
        with self.assertRaisesRegex(ValueError, "Unexpected staged path: content"):
            assets.validate(self.root, self.dist, self.paths, self.commit)

    def test_generated_html_is_limited_to_blog_index_files(self):
        manifest = self.root / "blog/.generated.json"
        manifest.write_text(json.dumps([str(self.article)]), encoding="utf-8")
        self.assertEqual(list(assets.generated_html(self.root)), [self.article])
        manifest.write_text(json.dumps(["blog/../scripts/index.html"]), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unexpected generated HTML path"):
            list(assets.generated_html(self.root))

    def test_workers_builds_requires_trigger_branch_commit_and_build_id(self):
        environment = {
            "WORKERS_CI": "1",
            "WORKERS_CI_BRANCH": "main",
            "WORKERS_CI_COMMIT_SHA": self.commit,
            "WORKERS_CI_BUILD_UUID": "build-id",
        }
        with patch.object(assets, "git", return_value=self.commit + "\n"), patch.dict(os.environ, environment):
            self.assertEqual(assets.checked_commit(self.root), self.commit)
            with patch.dict(os.environ, {"WORKERS_CI_BRANCH": "preview"}):
                with self.assertRaisesRegex(ValueError, "push to main"):
                    assets.checked_commit(self.root)
            with patch.dict(os.environ, {"WORKERS_CI_COMMIT_SHA": "b" * 40}):
                with self.assertRaisesRegex(ValueError, "differs from the Workers Builds commit"):
                    assets.checked_commit(self.root)
            with patch.dict(os.environ, {"WORKERS_CI_BUILD_UUID": ""}):
                with self.assertRaisesRegex(ValueError, "Builds ID is missing"):
                    assets.checked_commit(self.root)
