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
git push && git push --tags

echo ""
echo "Released v$VERSION."
echo "GitHub Actions will build and upload to PyPI automatically."
echo "Track progress: https://github.com/kskovpen/fce/actions"
