from copy import deepcopy
import io
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import build_blog, indexnow
from scripts import indexnow_deploy as deploy
from scripts import indexnow_manifest as manifest
from scripts import indexnow_state as state


A, B, C = ("a" * 40, "b" * 40, "c" * 40)
KEY = "ab" * 16
ONE = indexnow.BASE + "/blog/one/"
TWO = indexnow.BASE + "/blog/two/"
THREE = indexnow.BASE + "/blog/three/"


def post(slug, *, body="<p>Published article</p>", title="Article", source=None):
    return {
        "url": f"/blog/{slug}/", "body": body, "title": title, "description": "Description",
        "date": "2026-11-25", "updated": "2026-11-25", "category": "Test", "language": "en",
        "tags": ["test"], "source_path": source or f"content/blog/2026/{slug}.md",
    }


def snapshot(commit, *posts):
    return manifest.generate(posts, indexnow.BASE, commit)


class MemoryState:
    def __init__(self, root, state_data=None):
        self.root = root
        self.revision = A if state_data is not None else None
        self.durable = deepcopy(state_data)

    def save(self, data):
        state.validate(data)
        self.revision = A
        self.durable = deepcopy(data)


class PublishedManifestTests(unittest.TestCase):
    def test_manifest_is_generated_from_published_posts_and_excludes_drafts(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(build_blog, "ROOT", Path(folder)):
            directory = Path(folder) / "content/blog/2026"
            directory.mkdir(parents=True)
            (Path(folder) / "index.html").write_text("<!-- latest:start --><!-- latest:end -->")
            for slug, draft in (("one", "false"), ("two", "true")):
                (directory / f"{slug}.md").write_text(
                    f"---\ntitle: Article\ndescription: Test\ndate: 2026-11-25\nupdated: 2026-11-25\n"
                    f"category: Test\nlanguage: en\ntags: [test]\nslug: {slug}\ndraft: {draft}\n---\n\nBody.\n"
                )
            result = snapshot(A, *build_blog.build())
            self.assertEqual(set(result["articles"]), {ONE})
            self.assertEqual(result["articles"][ONE]["source"], "content/blog/2026/one.md")
            self.assertNotIn("Body.", manifest.encode(result).decode())
            (directory / "one.md").write_text((directory / "one.md").read_text().replace("false", "true"))
            (directory / "two.md").write_text((directory / "two.md").read_text().replace("true", "false"))
            after = snapshot(B, *build_blog.build())
            self.assertEqual(manifest.changes(result, after)[0], {ONE: "historical", TWO: "current"})

    def test_deterministic_fingerprints_ignore_formatting_commit_and_source_move(self):
        previous = snapshot(A, post("one", body="<p>One line</p>"))
        current = snapshot(B, post("one", body="<p>One\nline</p>", source="content/blog/2027/one.md"))
        self.assertEqual(previous["articles"][ONE]["fingerprint"], current["articles"][ONE]["fingerprint"])
        self.assertEqual(manifest.changes(previous, current)[0], {})
        self.assertEqual(manifest.encode(previous), manifest.encode(snapshot(A, post("one", body="<p>One line</p>"))))

    def test_meaningful_body_title_and_code_changes(self):
        original = snapshot(A, post("one", body="<pre><code>x  y</code></pre>"))
        for changed in (post("one", body="<pre><code>x y</code></pre>"),
                        post("one", body="<pre><code>x  y</code></pre>", title="New title")):
            self.assertEqual(manifest.changes(original, snapshot(B, changed))[0], {ONE: "current"})

    def test_slug_changes_additions_and_deletions_are_deduplicated(self):
        old = snapshot(A, post("one"), post("three", body="<p>Different</p>"))
        new = snapshot(B, post("two", source="content/blog/2026/one.md"))
        affected, counts = manifest.changes(old, new)
        self.assertEqual(affected, {ONE: "historical", THREE: "historical", TWO: "current"})
        self.assertEqual(counts, dict(added=0, updated=0, deleted=1, renamed=1, changed_urls=3))
        self.assertEqual(manifest.changes(snapshot(A), new)[1]["added"], 1)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / f"{KEY}.txt").write_bytes(KEY.encode())
        self.data = state.empty_state()
        self.store = MemoryState(self.root, self.data)
        for target, value in (("require_live_commit", None), ("preflight", None)):
            fixture = patch.object(deploy, target, return_value=value)
            setattr(self, target, fixture.start())
            self.addCleanup(fixture.stop)

    def run_notification(self, current, *, staged=True, **options):
        if staged and self.data["deployment"]["published"] != current:
            self.data["deployment"]["candidates"].setdefault(current["commit"], current)
            self.store.save(self.data)
        report = dict.fromkeys(deploy.COUNT_NAMES, 0)
        report.update(initialized=False, accepted=0, failed=0, responses=[])
        deploy.deliver(self.store, self.data, current, report, **options)
        return report

    def test_initialize_and_rerun_never_submit_or_drop_pending(self):
        release = snapshot(A, post("one"))
        self.data["notifications"]["pending"][ONE] = {
            "event": A, "proof": A, "kind": "current", "blocked": False,
        }
        with patch.object(indexnow, "submit_batch") as submit:
            self.assertTrue(self.run_notification(release, paused=True)["initialized"])
            self.assertFalse(self.run_notification(release, paused=True)["initialized"])
            self.assertIn(ONE, self.store.durable["notifications"]["pending"])
            self.assertEqual(self.run_notification(snapshot(B, post("one")), paused=True)["changed_urls"], 0)
            submit.assert_not_called()

    def test_first_run_and_identical_deployments_skip_api(self):
        with patch.object(indexnow, "submit_batch") as submit:
            self.assertTrue(self.run_notification(snapshot(A, post("one")))["initialized"])
            self.assertEqual(self.run_notification(snapshot(B, post("one")))["pending_total"], 0)
            submit.assert_not_called()
            self.preflight.assert_not_called()

    def test_first_candidate_with_no_remote_state_is_staged_before_initialization(self):
        self.store = MemoryState(self.root)
        release = snapshot(A, post("one"))
        with patch.object(deploy, "published_commit", return_value=None):
            deploy.prepare(self.store, self.data, release)
        self.assertIsNone(self.store.durable["deployment"]["published"])
        self.assertEqual(self.store.durable["deployment"]["candidates"], {A: release})
        with patch.object(indexnow, "submit_batch") as submit:
            self.assertTrue(self.run_notification(release, staged=False)["initialized"])
            submit.assert_not_called()
        self.assertEqual(self.store.durable["deployment"]["candidates"], {})

    def test_failed_deployment_and_skipped_commits_do_not_drive_diff(self):
        original = snapshot(A, post("one"))
        failed = snapshot(B, post("one"), post("two"))
        deployed = snapshot(C, post("one"), post("three"))
        self.run_notification(original)
        with patch.object(deploy, "published_commit", return_value=A):
            deploy.prepare(self.store, self.data, failed)
            deploy.prepare(self.store, self.data, deployed)
        self.assertEqual(self.store.durable["deployment"]["published"], original)
        self.run_notification(deployed, staged=False, paused=True)
        self.assertEqual(set(self.store.durable["notifications"]["pending"]), {THREE})
        self.assertEqual(self.store.durable["deployment"]["published"]["commit"], C)

    def test_recovers_live_candidate_if_previous_post_deploy_job_never_completed(self):
        self.run_notification(snapshot(A, post("one")))
        previous = snapshot(B, post("one"), post("two"))
        with patch.object(deploy, "published_commit", return_value=A):
            deploy.prepare(self.store, self.data, previous)
        self.data = deepcopy(self.store.durable)
        with patch.object(deploy, "published_commit", return_value=B):
            deploy.prepare(self.store, self.data, snapshot(C, post("one")))
        self.assertEqual(self.store.durable["deployment"]["published"], previous)
        self.run_notification(snapshot(C, post("one")), staged=False, paused=True)
        self.assertEqual(self.store.durable["notifications"]["pending"][TWO],
                         {"event": C, "proof": B, "kind": "historical", "blocked": False})

    def test_stale_or_failed_production_check_does_not_advance_state(self):
        self.run_notification(snapshot(A, post("one")))
        self.require_live_commit.side_effect = indexnow.IndexNowError("Different deployed version")
        with patch.object(deploy.time, "sleep"), patch.object(indexnow, "submit_batch") as submit:
            with self.assertRaises(indexnow.IndexNowError):
                self.run_notification(snapshot(B))
            submit.assert_not_called()
        self.assertEqual(self.store.durable["deployment"]["published"]["commit"], A)

    def test_live_release_without_staged_manifest_fails_closed(self):
        self.run_notification(snapshot(A, post("one")))
        with patch.object(indexnow, "submit_batch") as submit:
            with self.assertRaisesRegex(indexnow.IndexNowError, "not staged"):
                self.run_notification(snapshot(B, post("two")), staged=False)
            submit.assert_not_called()
        self.assertEqual(self.store.durable["deployment"]["published"]["commit"], A)

    def test_historical_urls_require_verified_prior_manifest_and_current_absence(self):
        self.run_notification(snapshot(A, post("one")))
        current = snapshot(B, post("two"))
        self.run_notification(current, paused=True)
        pending = self.store.durable["notifications"]["pending"]
        self.assertEqual(pending[ONE]["proof"], A)
        self.assertEqual(pending[TWO]["proof"], B)
        deploy.validate_pending(current, pending, {TWO})
        for deployed in ({ONE, TWO}, set()):
            with self.assertRaises(indexnow.IndexNowError):
                deploy.validate_pending(current, pending, deployed)
        with self.assertRaises(indexnow.IndexNowError):
            deploy.validate_pending(current, {"https://outside.test/blog/one/": pending[ONE]}, set())
        with self.assertRaises(indexnow.IndexNowError):
            indexnow.select_urls([ONE], [TWO])

    def test_persists_successful_batch_before_network_failure_and_retries_only_pending(self):
        self.run_notification(snapshot(A))
        release = snapshot(B, post("one"), post("two"))
        responses = [(200, "received", 0, None), (None, "network_error", 0, "Network failure")]
        with patch.object(deploy, "BATCH_SIZE", 1), patch.object(indexnow, "submit_batch", side_effect=responses):
            with self.assertRaisesRegex(indexnow.IndexNowError, "Network failure"):
                self.run_notification(release)
        self.assertEqual(set(self.store.durable["notifications"]["accepted"]), {ONE})
        self.assertEqual(set(self.store.durable["notifications"]["pending"]), {TWO})
        self.data = deepcopy(self.store.durable)
        with patch.object(indexnow, "submit_batch", return_value=(202, "accepted_pending_verification", 0, None)) as submit:
            self.run_notification(release)
            submit.assert_called_once_with(KEY, [TWO])
        self.assertEqual(self.store.durable["notifications"]["pending"], {})
        log = (self.root / indexnow.LOG_PATH).read_text()
        self.assertNotIn(KEY, log)
        self.assertEqual([json.loads(line)["http_status"] for line in log.splitlines()], [200, None, 202])
        with patch.object(indexnow, "submit_batch") as submit:
            self.run_notification(release)
            submit.assert_not_called()

    def test_rate_limits_leave_queue_and_invalid_requests_are_blocked_until_retry(self):
        self.run_notification(snapshot(A))
        release = snapshot(B, post("one"))
        for code, expected_blocked in ((429, False), (422, True)):
            with patch.object(indexnow, "submit_batch", return_value=(code, "failure", 3, "Failure")):
                with self.assertRaises(indexnow.IndexNowError):
                    self.run_notification(release)
            entry = self.store.durable["notifications"]["pending"][ONE]
            self.assertIs(entry["blocked"], expected_blocked)
            self.assertEqual(entry["last_failure"]["retry_count"], 3)
        with patch.object(indexnow, "submit_batch", return_value=(200, "received", 0, None)) as submit:
            self.run_notification(release)
            submit.assert_not_called()
            self.run_notification(release, retry_blocked=True)
            submit.assert_called_once_with(KEY, [ONE])


class GitStateTests(unittest.TestCase):
    def test_fast_forward_state_rejects_a_concurrent_writer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            remote = root / "remote.git"
            subprocess.run(["git", "init", "--bare", "--quiet", remote], check=True)
            stores = []
            for name in ("first", "second", "observer"):
                checkout = root / name
                checkout.mkdir()
                subprocess.run(["git", "init", "--quiet", checkout], check=True)
                subprocess.run(["git", "-C", checkout, "remote", "add", "origin", remote.as_uri()], check=True)
                stores.append(state.GitState(checkout))
            first, second, observer = stores
            initial = first.load()
            initial["deployment"]["published"] = snapshot(A)
            first.save(initial)
            stale = second.load()
            original = first.load()
            original["deployment"]["published"] = snapshot(B)
            first.save(original)
            stale["deployment"]["published"] = snapshot(C)
            with self.assertRaisesRegex(indexnow.IndexNowError, "push"):
                second.save(stale)
            self.assertEqual(observer.load()["deployment"]["published"]["commit"], B)


class ProductionPreflightTests(unittest.TestCase):
    def test_version_marker_waits_for_expected_commit_with_bounded_delays(self):
        class Response(io.BytesIO):
            status = 200

        values = [Response((A + "\n").encode()), Response((B + "\n").encode())]
        with patch.object(indexnow, "http_open", side_effect=values) as http, patch.object(deploy.time, "sleep") as sleep:
            deploy.wait_until(lambda: deploy.require_live_commit(B))
        sleep.assert_called_once_with(2)
        self.assertEqual(http.call_args.args[0].full_url, f"{indexnow.BASE}/{manifest.MARKER}")

    def test_corrupted_historical_queue_cannot_pass_state_validation(self):
        damaged = state.empty_state()
        damaged["notifications"]["pending"]["https://external.test/blog/one/"] = {
            "event": B, "proof": A, "kind": "historical", "blocked": False,
        }
        with self.assertRaisesRegex(indexnow.IndexNowError, "Invalid IndexNow state"):
            state.validate(damaged)
