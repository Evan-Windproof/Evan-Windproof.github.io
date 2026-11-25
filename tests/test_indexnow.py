from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from email.message import Message
from email.utils import format_datetime
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree as ET

from scripts import indexnow


HOME = f"{indexnow.BASE}/"
ARTICLE = f"{indexnow.BASE}/blog/example/"
KEY = "ab" * 16


def sitemap(*urls):
    root = ET.Element(f"{indexnow.SITEMAP_NS}urlset")
    for url in urls:
        entry = ET.SubElement(root, f"{indexnow.SITEMAP_NS}url")
        ET.SubElement(entry, f"{indexnow.SITEMAP_NS}loc").text = url
    return ET.tostring(root, encoding="utf-8")


class Response(io.BytesIO):
    def __init__(self, status=200, body=b"", retry_after=None):
        super().__init__(body)
        self.status = status
        self.headers = Message()
        if retry_after is not None:
            self.headers["Retry-After"] = retry_after


class IndexNowTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.sitemap = self.root / indexnow.SITEMAP
        self.sitemap.write_bytes(sitemap(HOME, ARTICLE))

    def invoke(self, *args):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(indexnow.main(args, self.root), 0)
        return stdout.getvalue()

    def assert_cli_error(self, expected, *args):
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
            indexnow.main(args, self.root)
        self.assertEqual(caught.exception.code, 1)
        self.assertIn(expected, stderr.getvalue())
        self.assertNotIn(KEY, stderr.getvalue())

    def write_key(self, body=KEY.encode()):
        (self.root / f"{KEY}.txt").write_bytes(body)

    def test_key_format(self):
        for value in (KEY, "ABCDE-123", "a" * 128):
            self.assertTrue(indexnow.valid_key(value))
        for value in ("a" * 7, "a" * 129, "abcdefgh\n", "abcd_efg", "abcdéfgh"):
            self.assertFalse(indexnow.valid_key(value))

    def test_generate_and_reuse_one_key(self):
        self.assertIsNone(indexnow.find_key(self.root))
        with patch.object(indexnow.secrets, "token_hex", return_value=KEY) as token:
            created = self.invoke("--init-key")
            reused = self.invoke("--init-key")
        token.assert_called_once_with(16)
        self.assertEqual(indexnow.find_key(self.root), KEY)
        self.assertEqual(list(self.root.glob("*.txt")), [self.root / f"{KEY}.txt"])
        self.assertEqual((self.root / f"{KEY}.txt").read_bytes(), KEY.encode())
        self.assertNotIn(KEY, created + reused)

    def test_invalid_or_ambiguous_key_does_not_rotate(self):
        self.write_key(KEY.encode() + b"\n")
        self.assert_cli_error("differs from its filename", "--init-key")
        self.write_key()
        other = "Existing-123"
        (self.root / f"{other}.txt").write_bytes(other.encode())
        self.assert_cli_error("Multiple public key files", "--init-key")

    def test_url_validation(self):
        for url in (HOME, ARTICLE, f"{indexnow.BASE}/caf%C3%A9/"):
            indexnow.validate_url(url)
        for url in (
            "http://evanwindproof.top/", "https://evanwindproof.top",
            "https://evanwindproof.top:443/", "https://user@evanwindproof.top/",
            "https://EVANWINDPROOF.TOP/", "https://evanwindproof.top./", "/blog/",
            ARTICLE + "?utm_source=test", ARTICLE + "?", ARTICLE + "#", ARTICLE + "x y",
            ARTICLE + "%GG", ARTICLE + "%", ARTICLE + "%c3", ARTICLE + "中文",
            ARTICLE + "\n", ARTICLE + r"\escape", ARTICLE + "../test/", ARTICLE + "/",
        ):
            with self.subTest(url=url), self.assertRaises(indexnow.IndexNowError):
                indexnow.validate_url(url)

    def test_external_hosts_and_nonpublished_urls_rejected(self):
        for url in (
            "https://example.org/", "https://localhost/", "https://staging.evanwindproof.top/",
            "https://evanwindproof.top.example.org/", "https://evanwindproof.top@evil.test/",
            ARTICLE.rstrip("/"), f"{indexnow.BASE}/blog/draft/", f"{indexnow.BASE}/styles.css",
        ):
            with self.subTest(url=url), patch.object(indexnow, "http_open") as get:
                self.assert_cli_error("URL", "--url", url, "--dry-run")
                get.assert_not_called()

    def test_deduplication_keeps_first_occurrence(self):
        self.assertEqual(indexnow.select_urls([ARTICLE, HOME, ARTICLE], [HOME, ARTICLE]),
                         [ARTICLE, HOME])

    def test_batch_boundaries(self):
        urls = list(range(10_001))
        self.assertEqual([len(batch) for batch in indexnow.batches(urls, 10_000)], [10_000, 1])
        for size in (0, 10_001):
            with self.assertRaises(indexnow.IndexNowError):
                list(indexnow.batches(urls, size))

    def test_payload_preserves_encoded_url(self):
        url = f"{indexnow.BASE}/caf%C3%A9/"
        self.assertEqual(json.loads(indexnow.payload(KEY, [url])),
                         {"host": indexnow.HOST, "key": KEY, "urlList": [url]})

    def test_dry_run_sitemap_and_file_never_use_network_or_logs(self):
        self.write_key()
        self.sitemap.write_bytes(sitemap(HOME, ARTICLE, HOME))
        source = self.root / "urls.txt"
        source.write_text(f"\n{HOME}\n{ARTICLE}\n", encoding="utf-8-sig")
        with patch.object(indexnow, "http_open") as get, patch.object(indexnow, "find_key") as key:
            output = self.invoke("--url", ARTICLE, "--url-file", str(source), "--batch-size", "1", "--dry-run")
            all_urls = self.invoke("--sitemap", "--dry-run")
        get.assert_not_called()
        key.assert_not_called()
        self.assertIn(indexnow.ENDPOINT, output)
        self.assertIn("Batch size: 1", output)
        self.assertEqual(output.splitlines()[3::2], [ARTICLE, HOME])
        self.assertEqual(all_urls.splitlines()[3:], [HOME, ARTICLE])
        self.assertNotIn(KEY, output + all_urls)
        self.assertFalse((self.root / indexnow.LOG_PATH).exists())

    def test_bad_sitemap_fails_before_network(self):
        for body in (b"<bad xml", sitemap("https://other.example/"), sitemap()):
            with self.subTest(body=body), patch.object(indexnow, "http_open") as get:
                self.sitemap.write_bytes(body)
                self.assert_cli_error("itemap" if b"other" not in body else "URL", "--sitemap", "--dry-run")
                get.assert_not_called()

    def test_verify_key_requires_200_exact_content(self):
        self.write_key()
        with patch.object(indexnow, "http_open", return_value=Response(body=KEY.encode())) as http:
            self.assertIn("HTTP 200", self.invoke("--verify-key"))
            self.assertEqual(http.call_args.args[0].full_url, f"{indexnow.BASE}/{KEY}.txt")
        for response in (Response(202, KEY.encode()), Response(body=KEY.encode() + b"\n")):
            with patch.object(indexnow, "http_open", return_value=response) as http:
                self.assert_cli_error("exact content match", "--url", ARTICLE)
                self.assertEqual(http.call_count, 1)

    def test_submission_preflight_checks_production_membership(self):
        self.write_key()
        with patch.object(indexnow, "http_open",
                          side_effect=[Response(body=KEY.encode()), Response(body=sitemap(HOME))]) as http:
            self.assert_cli_error("missing from the published sitemap", "--url", ARTICLE)
            self.assertEqual([call.args[0].get_method() for call in http.call_args_list], ["GET", "GET"])
        self.assertFalse((self.root / indexnow.LOG_PATH).exists())

    def test_real_cli_posts_batches_and_logs_key_free_records(self):
        self.write_key()
        responses = [Response(body=KEY.encode()), Response(body=sitemap(HOME, ARTICLE)),
                     Response(200), Response(202)]
        with patch.object(indexnow, "http_open", side_effect=responses) as http:
            output = self.invoke("--sitemap", "--batch-size", "1")
        first, second = (call.args[0] for call in http.call_args_list[2:])
        self.assertEqual(first.get_method(), "POST")
        self.assertEqual(first.full_url, indexnow.ENDPOINT)
        self.assertEqual(first.get_header("Content-type"), "application/json; charset=utf-8")
        self.assertEqual(json.loads(first.data)["urlList"], [HOME])
        self.assertEqual(json.loads(second.data)["urlList"], [ARTICLE])
        self.assertIn("key validation pending", output)
        log = (self.root / indexnow.LOG_PATH).read_text(encoding="utf-8")
        self.assertNotIn(KEY, output + log)
        records = [json.loads(line) for line in log.splitlines()]
        self.assertEqual([item["http_status"] for item in records], [200, 202])
        self.assertEqual(records[1]["result"], "accepted_pending_verification")
        self.assertEqual(records[0]["urls"], [HOME])
        self.assertEqual(records[0]["batch_size"], 1)
        self.assertEqual(records[0]["endpoint"], indexnow.ENDPOINT)
        self.assertEqual(records[0]["retry_count"], 0)
        self.assertIsNone(records[0]["error"])
        self.assertEqual(datetime.fromisoformat(records[0]["timestamp"]).tzinfo, timezone.utc)

    def test_http_failures_are_logged_and_stop_later_batches(self):
        for status, result in ((400, "invalid_request"), (403, "key_verification_failed"),
                               (422, "validation_error"), (302, "unexpected_response")):
            self.write_key()
            response = HTTPError(indexnow.ENDPOINT, status, KEY, Message(), io.BytesIO(KEY.encode()))
            with self.subTest(status=status), patch.object(
                indexnow, "http_open",
                side_effect=[Response(body=KEY.encode()), Response(body=sitemap(HOME, ARTICLE)), response],
            ) as http, patch.object(indexnow.time, "sleep") as sleep:
                self.assert_cli_error(f"HTTP {status}", "--sitemap", "--batch-size", "1")
                self.assertEqual(http.call_count, 3)
                sleep.assert_not_called()
            log = (self.root / indexnow.LOG_PATH).read_text(encoding="utf-8")
            self.assertNotIn(KEY, log)
            self.assertEqual(json.loads(log.splitlines()[-1])["result"], result)

    def test_rate_limit_obeys_retry_after_then_succeeds(self):
        headers = Message()
        headers["Retry-After"] = "7"
        limited = HTTPError(indexnow.ENDPOINT, 429, "rate limited", headers, None)
        with patch.object(indexnow, "http_open", side_effect=[limited, Response(200)]), \
             patch.object(indexnow.time, "sleep") as sleep:
            self.assertEqual(indexnow.submit_batch(KEY, [HOME]), (200, "received", 1, None))
            sleep.assert_called_once_with(7)

    def test_retry_limits_delay_and_count(self):
        with patch.object(indexnow, "http_open", return_value=Response(429, retry_after="120")) as http, \
             patch.object(indexnow.time, "sleep") as sleep:
            self.assertEqual(indexnow.submit_batch(KEY, [HOME])[:3], (429, "rate_limited", 0))
            self.assertEqual(http.call_count, 1)
            sleep.assert_not_called()
        with patch.object(indexnow, "http_open", side_effect=[Response(503) for _ in range(4)]) as http, \
             patch.object(indexnow.time, "sleep") as sleep:
            self.assertEqual(indexnow.submit_batch(KEY, [HOME])[:3], (503, "server_error", 3))
            self.assertEqual(http.call_count, 4)
            self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 2, 4])

    def test_retry_after_supports_http_date_and_invalid_values(self):
        when = datetime.now(timezone.utc) + timedelta(seconds=30)
        self.assertTrue(25 < indexnow.retry_delay(format_datetime(when, usegmt=True), 0) <= 30)
        self.assertEqual(indexnow.retry_delay("invalid date", 2), 4)
        self.assertEqual(indexnow.retry_delay("000", 2), 0)

    def test_network_errors_do_not_echo_exception_details(self):
        with patch.object(indexnow, "http_open", side_effect=URLError(KEY)):
            status, result, retries, detail = indexnow.submit_batch(KEY, [HOME])
        self.assertEqual((status, result, retries), (None, "network_error", 0))
        self.assertNotIn(KEY, detail)
