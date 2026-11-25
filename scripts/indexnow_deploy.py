"""Reconcile production deployments and deliver their IndexNow notifications."""

import argparse
from datetime import datetime, timezone
from http.client import HTTPException
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request

if __package__:
    from . import indexnow, indexnow_manifest as manifest, indexnow_state
else:
    import indexnow
    import indexnow_manifest as manifest
    import indexnow_state


BATCH_SIZE = 100
PROPAGATION_DELAYS = (0, 2, 5, 10, 20)
COUNT_NAMES = ("added", "updated", "deleted", "renamed", "changed_urls")


def published_commit():
    request = Request(f"{indexnow.BASE}/{manifest.MARKER}", headers={"Cache-Control": "no-cache"})
    try:
        with indexnow.http_open(request) as response:
            value = response.read(42)
            if response.status == 200 and len(value) == 41 and value.endswith(b"\n"):
                commit = value.decode("ascii")
                if manifest.SHA.fullmatch(commit[:-1]):
                    return commit[:-1]
    except HTTPError as error:
        error.close()
        if error.code == 404:
            return None
        raise indexnow.IndexNowError(f"Production version marker returned HTTP {error.code}.") from None
    except (OSError, HTTPException, UnicodeError):
        raise indexnow.IndexNowError("Could not read the production version marker.") from None
    raise indexnow.IndexNowError("Production version marker is invalid.")


def wait_until(check):
    for delay in PROPAGATION_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            return check()
        except indexnow.IndexNowError as error:
            message = str(error)
    raise indexnow.IndexNowError(message)


def require_live_commit(commit):
    if published_commit() != commit:
        raise indexnow.IndexNowError("Production is not serving the expected deployment commit.")


def record_deployment(state, current):
    deployment = state["deployment"]
    previous = deployment["published"]
    counts = dict.fromkeys(COUNT_NAMES, 0)
    initialized = previous is None
    if previous is not None and previous["commit"] == current["commit"]:
        if previous != current:
            raise indexnow.IndexNowError("A recorded commit has a different published manifest.")
    elif previous is not None:
        affected, counts = manifest.changes(previous, current)
        for url, kind in affected.items():
            proof = previous if kind == "historical" else current
            if url not in proof["articles"]:
                raise indexnow.IndexNowError("Notification URL lacks trusted publication evidence.")
            state["notifications"]["pending"][url] = {
                "event": current["commit"], "proof": proof["commit"], "kind": kind, "blocked": False,
            }
    deployment["published"] = current
    deployment["candidates"].clear()
    return initialized, counts


def prepare(store, state, current):
    deployment = state["deployment"]
    candidates = deployment["candidates"]

    def previous_commit():
        live = published_commit()
        if live is None and deployment["published"] is not None:
            raise indexnow.IndexNowError("The recorded production version marker is temporarily missing.")
        return live

    live = wait_until(previous_commit)
    if live is not None:
        if store.revision is None:
            raise indexnow.IndexNowError("Production has a marker but the IndexNow state branch is missing.")
        if live in candidates:
            old = (deployment["published"] or {}).get("commit", "none")
            record_deployment(state, candidates[live])
            print(f"Recovered live deployment {live} after {old}.")
        elif live != (deployment["published"] or {}).get("commit"):
            raise indexnow.IndexNowError("Live deployment is unknown to IndexNow state. Recover state before sending.")
    if current["commit"] in candidates and candidates[current["commit"]] != current:
        raise indexnow.IndexNowError("An existing deployment candidate has a different manifest.")
    # Record the candidate before Pages serves it. A later run can repair an
    # interrupted post-deploy job if it finds this commit already live.
    if deployment["published"] != current:
        candidates[current["commit"]] = current
    store.save(state)


def validate_pending(current, pending, deployed):
    for url, record in pending.items():
        manifest.validate_article_url(url)
        present = record["kind"] == "current"
        if (url in current["articles"]) != present:
            raise indexnow.IndexNowError("Pending notification conflicts with the current manifest.")
        if (url in deployed) != present:
            raise indexnow.IndexNowError("Production sitemap has not caught up with the deployed article changes.")


def preflight(commit, current, pending, key):
    require_live_commit(commit)
    indexnow.verify_key(key)
    deployed = set(indexnow.deployed_urls())
    if indexnow.BASE + "/" not in deployed:
        raise indexnow.IndexNowError("Production sitemap is missing its canonical homepage.")
    validate_pending(current, pending, deployed)


def deliver(store, state, current, report, *, paused=False, retry_blocked=False):
    commit = current["commit"]
    pending = state["notifications"]["pending"]
    report["pending_total"] = len(pending)
    report["status"] = "production verification failed; existing state retained"
    wait_until(lambda: require_live_commit(commit))
    report["status"] = "deployment state could not be validated; no submission attempted"
    if store.revision is None:
        raise indexnow.IndexNowError("IndexNow state is missing. Restore or explicitly initialize it before sending.")
    candidate = state["deployment"]["candidates"].get(commit)
    if candidate is None and state["deployment"]["published"] != current:
        raise indexnow.IndexNowError("This deployment was not staged. Recover its verified manifest before sending.")
    if candidate is not None and candidate != current:
        raise indexnow.IndexNowError("Deployed manifest differs from the staged deployment candidate.")
    report["initialized"], counts = record_deployment(state, current)
    report.update(counts)
    report["pending_total"] = len(pending)
    report["status"] = "deployment state could not be saved; no submission attempted"
    store.save(state)
    ready = {url: record for url, record in pending.items() if retry_blocked or not record["blocked"]}
    report["deduplicated_urls"] = len(ready)
    if paused or not ready:
        report["status"] = "paused" if paused else ("blocked entries retained" if pending else "no changes or pending URLs")
        return

    report["status"] = "preflight failed; pending entries retained"
    key = indexnow.find_key(store.root)
    if not key:
        raise indexnow.IndexNowError("Public key file missing from the site root.")
    wait_until(lambda: preflight(commit, current, ready, key))
    log = store.root / indexnow.LOG_PATH
    log.parent.mkdir(parents=True, exist_ok=True)
    log.touch()
    accepted = state["notifications"]["accepted"]
    for urls in indexnow.batches(sorted(ready), BATCH_SIZE):
        result = indexnow.submit_batch(key, urls)
        status, label, retries, detail = result
        report["responses"].append(f"{status or 'network error'} / {retries} retries")
        if status in (200, 202):
            report["accepted"] += len(urls)
            for url in urls:
                record = pending.pop(url)
                record.pop("blocked")
                record.pop("last_failure", None)
                accepted[url] = dict(record, http_status=status, result=label,
                                     retry_count=retries, timestamp=datetime.now(timezone.utc).isoformat())
        else:
            report["failed"] += len(urls)
            for url in urls:
                pending[url]["blocked"] = status in (400, 422)
                pending[url]["last_failure"] = {
                    "http_status": status, "result": label, "retry_count": retries,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
        report["status"] = "batch state write failed; delivery outcome may be uncertain"
        store.save(state)
        report["pending_total"] = len(pending)
        report["status"] = "batch recorded; local log write failed"
        indexnow.log_batch(log, urls, status, label, retries, detail)
        if status not in (200, 202):
            report["status"] = "batch failed; remaining entries retained"
            raise indexnow.IndexNowError(detail or "IndexNow rejected a notification batch.")
    report["status"] = "accepted by IndexNow; blocked entries retained" if pending else "accepted by IndexNow"


def summary(report):
    rows = (
        ("Previous deployment", report["previous"]), ("Current deployment", report["current"]),
        ("Baseline initialized", str(report["initialized"]).lower()),
        ("Added articles", report["added"]), ("Updated articles", report["updated"]),
        ("Deleted or unpublished articles", report["deleted"]), ("Changed canonical URLs (pairs)", report["renamed"]),
        ("Unique changed URLs", report["changed_urls"]), ("Eligible deduplicated URLs", report["deduplicated_urls"]),
        ("Pending notifications", report["pending_total"]), ("HTTP status / retries per batch", ", ".join(report["responses"]) or "none"),
        ("Accepted URLs", report["accepted"]), ("Failed URLs", report["failed"]), ("Status", report["status"]),
        ("Failure detail", report.get("error") or "none"),
    )
    return "## IndexNow production notifications\n\n| Result | Value |\n| --- | --- |\n" + "".join(
        f"| {label} | {value} |\n" for label, value in rows
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "notify", "initialize", "recover"))
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--paused", action="store_true")
    parser.add_argument("--retry-blocked", action="store_true")
    args = parser.parse_args()
    report = dict.fromkeys(COUNT_NAMES, 0)
    report.update(previous="unknown", current="unknown", initialized=False, deduplicated_urls=0,
                  pending_total="unknown", responses=[], accepted=0, failed=0, status="state or manifest unavailable")
    try:
        current = json.loads(args.manifest.read_bytes())
        manifest.validate_manifest(current)
        if current["commit"] != args.commit:
            raise indexnow.IndexNowError("Manifest commit differs from the workflow commit.")
        report["current"] = args.commit
        store = indexnow_state.GitState(indexnow.ROOT)
        state = store.load()
        report["previous"] = (state["deployment"]["published"] or {}).get("commit", "none")
        if args.stage == "prepare":
            prepare(store, state, current)
        elif args.stage in ("initialize", "recover"):
            if (args.stage == "recover") != (store.revision is not None):
                raise indexnow.IndexNowError("Use initialize for a missing state branch or recover for an existing one.")
            wait_until(lambda: require_live_commit(current["commit"]))
            record_deployment(state, current)
            store.save(state)
            print("Recorded the verified live manifest without submitting any URLs.")
        else:
            deliver(store, state, current, report, paused=args.paused, retry_blocked=args.retry_blocked)
    except (OSError, ValueError, indexnow.IndexNowError) as error:
        detail = str(error) if isinstance(error, indexnow.IndexNowError) else "IndexNow could not read or write a local file."
        report["error"] = detail
        print(f"::warning::{detail}")
        return 1
    finally:
        if args.stage == "notify":
            text = summary(report)
            print(text)
            if path := os.environ.get("GITHUB_STEP_SUMMARY"):
                with Path(path).open("a", encoding="utf-8") as file:
                    file.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
