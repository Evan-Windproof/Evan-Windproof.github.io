"""Describe published articles using the blog generator's resolved posts."""

from collections import defaultdict
import hashlib
from html.parser import HTMLParser
import json
import re

if __package__:
    from . import indexnow
else:
    import indexnow


VERSION = 1
SHA = re.compile(r"[0-9a-f]{40}")
FINGERPRINT = re.compile(r"[0-9a-f]{64}")
ARTICLE_PATH = re.compile(r"/blog/(?!tags/)[a-z0-9]+(?:-[a-z0-9]+)*/")
METADATA = ("title", "description", "date", "updated", "category", "language", "tags")
MARKER = "indexnow-deployment.txt"


class ArticleBody(HTMLParser):
    """Discard HTML serialization differences while retaining code whitespace."""

    def __init__(self, body):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.preformatted = 0
        self.feed(body)
        self.close()

    def handle_starttag(self, tag, attrs):
        self.parts.append(("start", tag, sorted(attrs)))
        if tag in {"pre", "code"}:
            self.preformatted += 1

    def handle_endtag(self, tag):
        self.parts.append(("end", tag))
        if tag in {"pre", "code"}:
            self.preformatted = max(0, self.preformatted - 1)

    def handle_data(self, data):
        self.parts.append(("text", data if self.preformatted else re.sub(r"[ \t\r\n\f]+", " ", data)))


def encode(document):
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def generate(posts, base, commit):
    articles = {}
    for post in posts:
        metadata = {field: post[field] for field in METADATA}
        fingerprint = hashlib.sha256(encode([metadata, ArticleBody(post["body"]).parts])).hexdigest()
        articles[base + post["url"]] = {
            "source": post["source_path"], "fingerprint": fingerprint, "metadata": metadata,
        }
    manifest = {"schema_version": VERSION, "commit": commit, "articles": articles}
    validate_manifest(manifest)
    return manifest


def validate_article_url(url):
    indexnow.validate_url(url)
    if not ARTICLE_PATH.fullmatch(url.removeprefix(indexnow.BASE)):
        raise indexnow.IndexNowError("Expected a canonical production article URL.")


def validate_manifest(manifest):
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != VERSION
        or not SHA.fullmatch(str(manifest.get("commit")))
        or not isinstance(manifest.get("articles"), dict)
    ):
        raise indexnow.IndexNowError("Invalid IndexNow manifest schema or commit.")
    sources = set()
    for url, article in manifest["articles"].items():
        validate_article_url(url)
        if (
            not isinstance(article, dict)
            or not FINGERPRINT.fullmatch(str(article.get("fingerprint")))
            or not isinstance(article.get("metadata"), dict)
            or set(article["metadata"]) != set(METADATA)
        ):
            raise indexnow.IndexNowError("Invalid IndexNow article record.")
        source = article.get("source")
        if not isinstance(source, str) or not source.startswith("content/blog/") or not source.endswith(".md"):
            raise indexnow.IndexNowError("Invalid IndexNow article source.")
        if source in sources or any(part in {"", ".", ".."} for part in source.split("/")):
            raise indexnow.IndexNowError("Duplicate or invalid IndexNow article source.")
        sources.add(source)


def changes(previous, current):
    before = previous["articles"]
    after = current["articles"]
    old = before.keys() - after.keys()
    new = after.keys() - before.keys()
    updated = {url for url in before.keys() & after.keys()
               if before[url]["fingerprint"] != after[url]["fingerprint"]}
    old_sources = {before[url]["source"]: url for url in old}
    new_sources = {after[url]["source"]: url for url in new}
    renamed = {old_sources[path]: new_sources[path] for path in old_sources.keys() & new_sources.keys()}
    # A simultaneous file move and slug change still submits both URLs. Identify
    # it as a rename in the summary if the article content gives a unique match.
    unmatched_old = old - renamed.keys()
    unmatched_new = new - set(renamed.values())
    old_hashes, new_hashes = defaultdict(list), defaultdict(list)
    for url in unmatched_old:
        old_hashes[before[url]["fingerprint"]].append(url)
    for url in unmatched_new:
        new_hashes[after[url]["fingerprint"]].append(url)
    for fingerprint, same_old in old_hashes.items():
        same_new = new_hashes[fingerprint]
        if len(same_old) == len(same_new) == 1:
            renamed[same_old[0]] = same_new[0]
    affected = {url: "historical" for url in sorted(old)}
    affected.update({url: "current" for url in sorted(new | updated)})
    counts = {
        "added": len(new - set(renamed.values())), "updated": len(updated),
        "deleted": len(old - renamed.keys()), "renamed": len(renamed),
        "changed_urls": len(affected),
    }
    return affected, counts
