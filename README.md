# Future Collider Experiment Studio

The Future Collider Experiment (FCE) project provides a sneak peek
into the particle physics processes that will become available at the
Future Circular Collider (FCC) in a user-friendly environment.

Built with [Dear PyGui](https://github.com/hoffstadt/DearPyGui), it runs natively on **macOS, Windows, and Linux** with no external dependencies beyond Python.

## Main screen interface

![FCE main screen](https://raw.githubusercontent.com/kskovpen/fce/main/fce_studio/fce-screen.png)

---

## Installation

```bash
pip install fce
```

Then launch from a terminal:

```bash
fce
```

### Requirements

- Python ≥ 3.10
- A display (X11/Wayland on Linux, Quartz on macOS, Win32 on Windows)

All Python dependencies are installed automatically by pip.

---

## Releasing a new version

The version is defined in exactly one place — `fce_studio/__init__.py`. A single script bumps it, commits, tags, and pushes; a GitHub Actions workflow then builds the package, uploads it to PyPI, and creates a GitHub Release automatically.

### One command

```bash
./release.sh 0.0.8
```

`release.sh` will:
1. Update the version in `fce_studio/__init__.py`
2. Commit, tag (`v0.0.8`), and push to GitHub
3. GitHub Actions builds `dist/*.tar.gz` and `dist/*.whl`, uploads them to [PyPI](https://pypi.org/project/fce/), and creates a [GitHub Release](https://github.com/kskovpen/fce/releases)

Make the script executable once:

```bash
chmod +x release.sh
```

### One-time git setup (first release only)

```bash
git init
git remote add origin https://github.com/kskovpen/fce.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

### One-time setup: add your PyPI token to GitHub

The workflow reads a secret called `PYPI_API_TOKEN`. You only need to set this once:

1. Go to [PyPI → Account Settings → API tokens](https://pypi.org/manage/account/token/) and create a token scoped to the `fce` project.
2. Go to **https://github.com/kskovpen/fce/settings/secrets/actions** and add a secret named `PYPI_API_TOKEN` with that token as the value.

---

## Manual release (without GitHub Actions)

If you need to publish without pushing a tag, you can do it locally:

```bash
pip install build twine
python -m build
twine upload dist/*
```

`twine` reads credentials from `~/.pypirc`:

```ini
[distutils]
index-servers = pypi

[pypi]
username = __token__
password = pypi-<your-token-here>
```

To do a dry run on TestPyPI first:

```bash
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ fce
```

---

## Development install

Clone the repository and install in editable mode so changes to source files take effect immediately:

```bash
git clone https://github.com/kskovpen/fce.git
cd fce
pip install -e .
fce
```

---

## License

[LGPL-2.1](LICENSE)
