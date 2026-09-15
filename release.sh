#!/usr/bin/env bash
set -e

# Always run from the project root (where this script lives)
cd "$(dirname "$0")"

VERSION="$1"

# ── Validate input ─────────────────────────────────────────────────────────────
if [[ -z "$VERSION" ]]; then
    echo "Usage: ./release.sh <version>   (e.g. ./release.sh 0.0.7)"
    exit 1
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: version must be in X.Y.Z format"
    exit 1
fi

# ── Check git repo and remote ──────────────────────────────────────────────────
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: not a git repository."
    echo "Run once to initialise:"
    echo "  git init"
    echo "  git remote add origin https://github.com/kskovpen/fce.git"
    exit 1
fi

if ! git remote get-url origin > /dev/null 2>&1; then
    echo "Error: no remote 'origin' configured."
    echo "  git remote add origin https://github.com/kskovpen/fce.git"
    exit 1
fi

# ── Check tag does not already exist ──────────────────────────────────────────
if git rev-parse "v$VERSION" > /dev/null 2>&1; then
    echo "Error: tag v$VERSION already exists."
    exit 1
fi

# ── Bump version in __init__.py ───────────────────────────────────────────────
python3 - <<EOF
import re
path = "__init__.py"
content = open(path).read()
content = re.sub(r'__version__ = "[^"]*"', '__version__ = "$VERSION"', content)
open(path, "w").write(content)
EOF

echo "Bumped __init__.py → $VERSION"

# ── Commit, tag, push ─────────────────────────────────────────────────────────
git add -u
if ! git diff --cached --quiet; then
    git commit -m "Release $VERSION"
fi
git tag "v$VERSION"

# Each push is checked on its own. `git push && git push --tags` hid a failure:
# set -e does not apply to any command in an && list except the last one, so a
# rejected first push fell straight through to the success banner and reported a
# release that never left the machine.
# Only the release tag is pushed. --tags pushes every local tag, and has already
# published local-only backup tags by accident.
if ! git push; then
    echo ""
    echo "Error: could not push to origin."
    echo "The release commit and the tag v$VERSION exist locally, but nothing was"
    echo "published and no build was triggered. Fix the push, then finish with:"
    echo "  git push && git push origin v$VERSION"
    exit 1
fi

if ! git push origin "v$VERSION"; then
    echo ""
    echo "Error: the release commit was pushed, but the tag v$VERSION was not."
    echo "GitHub Actions builds on the tag, so nothing was published. Finish with:"
    echo "  git push origin v$VERSION"
    exit 1
fi

echo ""
echo "Released v$VERSION."
echo "GitHub Actions will build and upload to PyPI automatically."
echo "Track progress: https://github.com/kskovpen/fce/actions"
