"""Manually submit canonical blog URLs to IndexNow."""

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPException
import json
from pathlib import Path
import re
import secrets
import time
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
HOST = "evanwindproof.top"
BASE = f"https://{HOST}"
ENDPOINT = "https://api.indexnow.org/indexnow"
SITEMAP = "sitemap.xml"
LOG_PATH = Path(".indexnow/submissions.jsonl")
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
MAX_BATCH_SIZE = 10_000
MAX_RETRIES = 3
MAX_RETRY_WAIT = 60
TIMEOUT = 15
KEY_FORMAT = re.compile(r"[A-Za-z0-9-]{8,128}")
KEY_FILENAME = re.compile(r"[0-9a-f]{32}")
URL_PATH = re.compile(r"/[A-Za-z0-9._~!$&'()*+,;=:@%/-]*")
INVALID_ESCAPE = re.compile(r"%(?![0-9A-F]{2})")
RESPONSE_RESULTS = {
    200: ("received", None),
    202: ("accepted_pending_verification", None),
    400: ("invalid_request", "IndexNow rejected the request format."),
    403: ("key_verification_failed", "IndexNow could not validate the key."),
    422: ("validation_error", "IndexNow rejected the URLs or payload."),
    429: ("rate_limited", "IndexNow rate-limited the request."),
}


class IndexNowError(Exception):
    """An error safe to display without exposing the key."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_open(request):
    return build_opener(NoRedirects()).open(request, timeout=TIMEOUT)


def valid_key(value):
    return KEY_FORMAT.fullmatch(value) is not None


def find_key(root):
    keys = []
    for path in root.glob("*.txt"):
        if not valid_key(path.stem):
            continue
        with path.open("rb") as file:
            matches = file.read(129) == path.stem.encode("ascii")
        if matches:
            keys.append(path.stem)
        elif KEY_FILENAME.fullmatch(path.stem):
            raise IndexNowError("The public key file content differs from its filename.")
    if len(keys) > 1:
        raise IndexNowError("Multiple public key files found in the site root.")
    return keys[0] if keys else None


def init_key(root):
    lock = root / LOG_PATH.parent / "key-init.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.touch(exist_ok=False)
    except FileExistsError:
        raise IndexNowError("Key initialization is already locked in .indexnow.") from None
    try:
        if find_key(root):
            return False
        key = secrets.token_hex(16)
        with (root / f"{key}.txt").open("xb") as file:
            file.write(key.encode("utf-8"))
        return True
    finally:
        lock.unlink()


def validate_url(url):
    path = url.removeprefix(BASE)
    if (
        path == url
        or not URL_PATH.fullmatch(path)
        or INVALID_ESCAPE.search(path)
        or any(segment in (".", "..") for segment in path.split("/"))
        or "//" in path
    ):
        raise IndexNowError(f"Expected a canonical HTTPS page URL on {HOST}.")


def sitemap_urls(source):
    try:
        tree = ET.parse(source)
    except ET.ParseError:
        raise IndexNowError("Sitemap XML could not be parsed.") from None
    if tree.getroot().tag != f"{SITEMAP_NS}urlset":
        raise IndexNowError("Expected a generated sitemap URL set.")
    urls = [loc.text or "" for loc in tree.findall(f"./{SITEMAP_NS}url/{SITEMAP_NS}loc")]
    if not urls:
        raise IndexNowError("Sitemap contains no page URLs.")
    for url in urls:
        validate_url(url)
    return urls


def select_urls(urls, published):
    available = set(published)
    unique = list(dict.fromkeys(urls))
    if not unique:
        raise IndexNowError("No URLs to submit.")
    for url in unique:
        validate_url(url)
        if url not in available:
            raise IndexNowError("A URL is missing from the published sitemap.")
    return unique


def batches(urls, size):
    if not 1 <= size <= MAX_BATCH_SIZE:
        raise IndexNowError(f"Batch size must be between 1 and {MAX_BATCH_SIZE}.")
    for start in range(0, len(urls), size):
        yield urls[start:start + size]


def payload(key, urls):
    return json.dumps({"host": HOST, "key": key, "urlList": urls}).encode("utf-8")


def verify_key(key):
    expected = key.encode("utf-8")
    try:
        with http_open(Request(f"{BASE}/{key}.txt")) as response:
            if response.status == 200 and response.read(len(expected) + 1) == expected:
                return
    except HTTPError as error:
        error.close()
        raise IndexNowError(f"Public key verification returned HTTP {error.code}.") from None
    except (OSError, HTTPException):
        raise IndexNowError("Could not reach the public key file.") from None
    raise IndexNowError("Public key verification requires HTTP 200 and an exact content match.")


def deployed_urls():
    try:
        with http_open(Request(f"{BASE}/{SITEMAP}")) as response:
            if response.status == 200:
                return sitemap_urls(response)
    except HTTPError as error:
        error.close()
        raise IndexNowError(f"Production sitemap returned HTTP {error.code}.") from None
    except (OSError, HTTPException):
        raise IndexNowError("Could not read the production sitemap.") from None
    raise IndexNowError("Production sitemap did not return HTTP 200.")


def retry_delay(value, retries):
    fallback = 2 ** retries
    if not value:
        return fallback
    value = value.strip()
    if re.fullmatch(r"[0-9]+", value):
        seconds = value.lstrip("0")
        return int(seconds or "0") if len(seconds) <= 2 else MAX_RETRY_WAIT + 1
    try:
        when = parsedate_to_datetime(value)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return max(0, (when - datetime.now(timezone.utc)).total_seconds())
    except (ValueError, TypeError, OverflowError):
        return fallback


def submit_batch(key, urls):
    request = Request(
        ENDPOINT,
        data=payload(key, urls),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    for retries in range(MAX_RETRIES + 1):
        retry_after = None
        try:
            with http_open(request) as response:
                status = response.status
                retry_after = response.headers.get("Retry-After")
        except HTTPError as error:
            status = error.code
            retry_after = error.headers.get("Retry-After") if error.headers else None
            error.close()
        except (OSError, HTTPException):
            return None, "network_error", retries, "IndexNow request failed at the network layer."

        server_error = 500 <= status < 600
        result, detail = RESPONSE_RESULTS.get(
            status,
            ("server_error", "IndexNow returned a server-side error.") if server_error
            else ("unexpected_response", "IndexNow returned an unexpected HTTP status."),
        )
        if retries == MAX_RETRIES or (status != 429 and not server_error):
            return status, result, retries, detail
        delay = retry_delay(retry_after, retries)
        if delay > MAX_RETRY_WAIT:
            return status, result, retries, "Retry-After exceeds the 60-second wait limit."
        time.sleep(delay)


def log_batch(path, urls, status, result, retries, error):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "urls": urls,
        "batch_size": len(urls),
        "endpoint": ENDPOINT,
        "http_status": status,
        "result": result,
        "retry_count": retries,
        "error": error,
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def run(args, root):
    if args.init_key:
        print("Public key file created." if init_key(root) else "Existing public key file reused.")
        return
    if args.verify_key:
        key = find_key(root)
        if not key:
            raise IndexNowError("Public key file missing from the site root.")
        verify_key(key)
        print("Public key verification passed (HTTP 200, exact content match).")
        return

    published = sitemap_urls(root / SITEMAP)
    requested = published if args.sitemap else args.url.copy()
    for path in args.url_file:
        requested.extend(line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()
                         if line.strip())
    urls = select_urls(requested, published)
    url_batches = list(batches(urls, args.batch_size))
    if args.dry_run:
        print(f"Endpoint: {ENDPOINT}\nBatch size: {args.batch_size}")
        for number, batch in enumerate(url_batches, start=1):
            print(f"Batch {number} ({len(batch)} URLs):")
            print("\n".join(batch))
        return

    key = find_key(root)
    if not key:
        raise IndexNowError("Public key file missing from the site root.")
    verify_key(key)
    select_urls(urls, deployed_urls())
    log = root / LOG_PATH
    log.parent.mkdir(parents=True, exist_ok=True)
    log.open("a", encoding="utf-8").close()
    for number, batch in enumerate(url_batches, start=1):
        status, result, retries, error = submit_batch(key, batch)
        log_batch(log, batch, status, result, retries, error)
        if error:
            response = f"HTTP {status}" if status is not None else result
            raise IndexNowError(f"Batch {number} ({response}): {error}")
        message = "received" if status == 200 else "accepted, key validation pending"
        print(f"Batch {number} ({len(batch)} URLs): HTTP {status}, {message}.")


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", default=[], help="Page URL (repeatable).")
    parser.add_argument("--url-file", action="append", default=[], type=Path,
                        help="UTF-8 file with one page URL per line (repeatable).")
    parser.add_argument("--sitemap", action="store_true", help="Use all URLs in sitemap.xml.")
    parser.add_argument("--init-key", action="store_true", help="Create or reuse the public key file.")
    parser.add_argument("--verify-key", action="store_true", help="Check the deployed public key file.")
    parser.add_argument("--batch-size", type=int, default=MAX_BATCH_SIZE)
    parser.add_argument("--dry-run", action="store_true", help="Preview batches without networking.")
    args = parser.parse_args(argv)
    has_explicit_urls = bool(args.url or args.url_file)
    if sum((has_explicit_urls, args.sitemap, args.init_key, args.verify_key)) != 1:
        parser.error("choose --url/--url-file, --sitemap, --init-key, or --verify-key")
    if args.dry_run and (args.init_key or args.verify_key):
        parser.error("--dry-run requires URL input or --sitemap")
    try:
        run(args, root)
    except (IndexNowError, OSError, UnicodeError) as error:
        message = str(error) if isinstance(error, IndexNowError) else "Could not read or write a local file."
        parser.exit(1, f"IndexNow: {message}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
