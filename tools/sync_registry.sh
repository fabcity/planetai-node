#!/usr/bin/env bash
# Vendor a pinned snapshot of the network's source registry into data/sources/.
#
#   tools/sync_registry.sh 5333ffa            # the commit the snapshot is taken from
#
# `awesome-fabcity-data` is where the network decides what can be measured at each pillar and scale.
# The node carries a COPY of it, pinned to one commit, so that it works on a boat, so that every node
# in a release answers the same question the same way, and so that updating it is a commit somebody
# reviewed rather than whatever main happened to say the morning a node rebooted.
#
# Which is why a branch name is refused. A floating pin is a node whose answers change under it.
#
# To update: merge the entry upstream, then run this with the merge commit, commit the diff, and put
# one line in CHANGELOG.md. docs/SOURCES.md is the long version.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

REPO="https://github.com/fabcity/awesome-fabcity-data"
REF="${1:-}"
OUT="data/sources"

case "$REF" in
  "") echo "usage: tools/sync_registry.sh <commit sha>   (7-40 hex chars; today's pin is in $OUT/REGISTRY_VERSION)"; exit 2;;
esac
# A tag moves, a branch moves, `main` moves fastest of all. Only a commit is a pin.
if ! printf '%s' "$REF" | grep -qE '^[0-9a-f]{7,40}$'; then
  echo "x '$REF' is not a commit sha. This pins a snapshot, so a branch or a tag is refused on purpose:"
  echo "  find the commit with:  git -C ../awesome-fabcity-data log -1 --format=%h origin/main"
  exit 2
fi

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
echo "  fetching $REPO @ $REF"
curl -sfL -o "$TMP/r.tar.gz" "$REPO/archive/$REF.tar.gz" \
  || { echo "x could not fetch $REPO/archive/$REF.tar.gz — is the sha on a pushed branch?"; exit 1; }
tar xzf "$TMP/r.tar.gz" -C "$TMP"
# GitHub names the directory with the FULL sha even when asked with a short one, which is where the
# long form below comes from; there is no second request for it.
SRC="$(find "$TMP" -maxdepth 1 -type d -name 'awesome-fabcity-data-*' | head -1)"
[ -n "$SRC" ] || { echo "x the tarball had no awesome-fabcity-data-<sha>/ directory in it"; exit 1; }
FULL="$(basename "$SRC" | sed 's/^awesome-fabcity-data-//')"
[ -d "$SRC/data" ] || { echo "x $REF has no data/ — wrong repository?"; exit 1; }

# Only the entries, the reviews and cells beside them, and the schemas they are validated against. Not
# the upstream README, its CI, or its harvest scripts: the node reads the list, it does not curate it.
rm -rf "$OUT"
mkdir -p "$OUT"
cp -R "$SRC/data" "$OUT/data"
mkdir -p "$OUT/schema"
cp "$SRC/schema/dataset.schema.json" "$OUT/schema/dataset.schema.json"

# reviews/ and cells/ arrived upstream on 2026-09-22 and a pin taken before that has neither, so each
# is copied only when the tarball carries it. `if` rather than `[ -d x ] && cp`, because that idiom
# returns non-zero on the last pin without them and this script runs under `set -e`.
for tree in reviews cells; do
  if [ -d "$SRC/$tree" ]; then cp -R "$SRC/$tree" "$OUT/$tree"; fi
done
for s in review cell; do
  if [ -f "$SRC/schema/$s.schema.json" ]; then cp "$SRC/schema/$s.schema.json" "$OUT/schema/$s.schema.json"; fi
done

N="$(find "$OUT/data" -name '*.yaml' | wc -l | tr -d ' ')"
cat > "$OUT/REGISTRY_VERSION" <<EOF
sha=$FULL
short=$(printf '%s' "$FULL" | cut -c1-7)
synced=$(date -u +%F)
entries=$N
source=$REPO
EOF

python3 tools/build_registry_index.py
echo "  $OUT is $REPO @ $(printf '%s' "$FULL" | cut -c1-7) — $N entries"
