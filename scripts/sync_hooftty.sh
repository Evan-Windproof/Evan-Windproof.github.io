#!/usr/bin/env bash
# Stage a one-way update from the main site's checked-out commit.
set -euo pipefail

if [[ $# != 2 ]]; then
  echo "Usage: $0 MAIN_CHECKOUT MIRROR_CHECKOUT" >&2
  exit 2
fi

main=$(git -C "$1" rev-parse --show-toplevel)
mirror=$(git -C "$2" rev-parse --show-toplevel)
page=projects/hooftty
marker=.hooftty-source
source=$(git -C "$main" rev-parse HEAD)
previous=$(git -C "$mirror" show "HEAD:$marker")

if [[ "$main" == "$mirror" || -n $(git -C "$mirror" status --porcelain --untracked-files=all) ||
      -n $(git -C "$mirror" status --porcelain --ignored -- "$page" "$marker") ]]; then
  echo "Use a separate, clean mirror checkout." >&2
  exit 1
fi
if [[ ! "$previous" =~ ^[0-9a-f]{40}$ ]] ||
   ! git -C "$main" merge-base --is-ancestor "$previous" "$source"; then
  echo "The mirror source marker is missing from the selected source history." >&2
  exit 1
fi

old_tree=$(git -C "$main" rev-parse --verify "$previous:$page")
mirror_tree=$(git -C "$mirror" rev-parse --verify "HEAD:$page")
if [[ "$old_tree" != "$mirror_tree" ]]; then
  echo "Mirror files diverged from $previous. Review the changes before syncing." >&2
  exit 1
fi

new_tree=$(git -C "$main" rev-parse --verify "$source:$page")
if [[ "$old_tree" == "$new_tree" ]]; then
  echo "The mirror already matches the page at $source."
  exit 0
fi

git -C "$main" cat-file -e "$source:$page/index.html"
archive=$(mktemp)
trap 'rm -f "$archive"' EXIT
git -C "$main" archive --output="$archive" "$source" "$page"
git -C "$mirror" rm -rq -- "$page"
tar -xf "$archive" -C "$mirror"
printf '%s\n' "$source" > "$mirror/$marker"
git -C "$mirror" add -- "$page" "$marker"
if [[ $(git -C "$mirror" write-tree --prefix="$page/") != "$new_tree" ]]; then
  echo "The staged page tree differs from the source. Do not commit." >&2
  exit 1
fi
