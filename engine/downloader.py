import json
import os
import shutil
import ssl
import urllib.request

import uproot

from paths import get_fce_home

_BASE_URL = "https://homepage.iihe.ac.be/~kskovpen/fce/datasets/"

_hdir = get_fce_home()
_EVENT_COUNTS_FILE = os.path.join(_hdir, "event_counts.json")


def _load_counts() -> dict:
    if os.path.exists(_EVENT_COUNTS_FILE):
        try:
            with open(_EVENT_COUNTS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_counts(counts: dict):
    tmp = _EVENT_COUNTS_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(counts, f)
        os.replace(tmp, _EVENT_COUNTS_FILE)
    except Exception:
        pass


def _ssl_context():
    # python.org builds on macOS ship without CA certificates until
    # "Install Certificates.command" is run; prefer certifi's bundle if present.
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _fetch(url: str, dest: str):
    """Download url to dest in pure Python (wget is not available on macOS).

    Writes to a .part file first so a failed transfer never leaves a partial
    file behind that would later be mistaken for a complete download.
    """
    tmp = dest + ".part"
    try:
        with urllib.request.urlopen(url, timeout=60, context=_ssl_context()) as resp, \
                open(tmp, "wb") as out:
            shutil.copyfileobj(resp, out, 1 << 20)
        os.replace(tmp, dest)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _count_root_file(local_path: str, relative_path: str, counts: dict) -> int | None:
    """Open a ROOT file, read num_entries, store in counts dict. Returns count or None."""
    parts = relative_path.replace("\\", "/").split("/")
    if len(parts) < 3 or not parts[2].endswith(".root"):
        return None
    detector = parts[0]
    energy   = parts[1]          # e.g. "91GeV"
    sample   = parts[2][:-5]     # strip .root
    key      = f"{detector}_{energy}_{sample}"
    if key in counts:
        return counts[key]
    try:
        with uproot.open(local_path) as f_root:
            n = f_root["ntuple"].num_entries
        counts[key] = n
        return n
    except Exception:
        return None


def run_dataset_download(detector=None, energy_gev=None, force=False):
    """
    Download FCC-ee datasets.
    detector:   "IDEA" | "CLD" | None (all detectors)
    energy_gev: "91" | "160" | "240" | "365" | None (all energies)
    force:      re-download even if files already exist
    """
    target_dir = os.path.join(get_fce_home(), "datasets")
    os.makedirs(target_dir, exist_ok=True)

    inventory_path = os.path.join(target_dir, "files.txt")
    inventory_url  = _BASE_URL + "files.txt"

    yield "Fetching file list...\n"
    try:
        _fetch(inventory_url, inventory_path)
    except Exception as e:
        yield f"Error: could not fetch file list — {e}\n"
        return

    try:
        with open(inventory_path) as f:
            all_files = [ln.strip() for ln in f if ln.strip()]
    except Exception as e:
        yield f"Error reading file list: {e}\n"
        return

    # Filter by detector and energy
    def _matches(rel):
        parts = rel.replace("\\", "/").split("/")
        if len(parts) < 2:
            return True
        det_match = (detector is None) or (parts[0] == detector)
        en_str    = f"{energy_gev}GeV" if energy_gev else None
        en_match  = (energy_gev is None) or (len(parts) >= 2 and parts[1] == en_str)
        return det_match and en_match

    file_list = [f for f in all_files if _matches(f)]
    total = len(file_list)
    if total == 0:
        yield "Nothing to download for the selected filter.\n"
        return

    counts  = _load_counts()
    skipped = 0
    for idx, relative_path in enumerate(file_list):
        local_path = os.path.join(target_dir, relative_path.replace("/", os.sep))
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        already_have = (not force
                        and os.path.exists(local_path)
                        and os.path.getsize(local_path) > 0)

        if already_have:
            skipped += 1
            yield f"[{idx+1}/{total}] Already have {relative_path}\n"
        else:
            yield f"[{idx+1}/{total}] Downloading {relative_path}\n"
            file_url = _BASE_URL + relative_path.lstrip("/")
            try:
                _fetch(file_url, local_path)
            except Exception as e:
                yield f"  Warning: {e}\n"
                continue

        # Count events in ROOT files (skip if already cached)
        if relative_path.endswith(".root") and os.path.exists(local_path):
            n = _count_root_file(local_path, relative_path, counts)
            if n is not None:
                _save_counts(counts)
                yield f"  -> {n:,} events\n"

    yield f"Done. ({skipped}/{total} already present)\n"
