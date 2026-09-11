"""Offline tests for engine.downloader, using file:// URLs instead of the network."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine.downloader as downloader


def test_fetch_copies_file(tmp_path):
    src = tmp_path / "src.txt"
    src.write_bytes(b"hello")
    dest = tmp_path / "dest.txt"
    downloader._fetch(src.as_uri(), str(dest))
    assert dest.read_bytes() == b"hello"
    assert not os.path.exists(str(dest) + ".part")


def test_fetch_failure_leaves_no_file(tmp_path):
    dest = tmp_path / "dest.txt"
    with pytest.raises(Exception):
        downloader._fetch((tmp_path / "missing.txt").as_uri(), str(dest))
    assert not dest.exists()
    assert not os.path.exists(str(dest) + ".part")


def test_run_dataset_download_filters_and_skips(tmp_path, monkeypatch):
    server = tmp_path / "server"
    (server / "IDEA" / "91GeV").mkdir(parents=True)
    (server / "CLD" / "91GeV").mkdir(parents=True)
    (server / "IDEA" / "91GeV" / "notes.txt").write_text("idea")
    (server / "CLD" / "91GeV" / "notes.txt").write_text("cld")
    (server / "files.txt").write_text("IDEA/91GeV/notes.txt\nCLD/91GeV/notes.txt\n")

    home = tmp_path / "home"
    monkeypatch.setattr(downloader, "_BASE_URL", server.as_uri() + "/")
    monkeypatch.setattr(downloader, "get_fce_home", lambda: str(home))

    log = "".join(downloader.run_dataset_download(detector="IDEA", energy_gev="91"))
    assert "Done. (0/1 already present)" in log
    assert (home / "datasets" / "IDEA" / "91GeV" / "notes.txt").read_text() == "idea"
    assert not (home / "datasets" / "CLD").exists()

    log = "".join(downloader.run_dataset_download(detector="IDEA", energy_gev="91"))
    assert "Done. (1/1 already present)" in log
