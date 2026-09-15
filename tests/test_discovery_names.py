"""Names given to discovered processes follow the process, not the histogram slot."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

components = pytest.importorskip("ui.components")


@pytest.fixture(autouse=True)
def _fresh_names():
    components._NAMED_PROCESSES.clear()
    components._DISCOVERED.clear()
    yield
    components._NAMED_PROCESSES.clear()
    components._DISCOVERED.clear()


def _cfg(energy, *targets):
    hists = [{"plot_idx": k, "target": t} for k, t in enumerate(targets)]
    return {"energy": energy, "histograms": hists, "selections": [{"histograms": hists}]}


def _res(target, sig=6.0, energy="240"):
    return {"sig": sig, "target": target, "energy": energy}


def test_a_name_stays_on_its_process_when_the_histogram_fits_another():
    # X2 is discovered and named on the first histogram, which then fits X1.
    # Keyed by slot, the legend used to call X1 "WW" and X2 plain "X2".
    components._NAMED_PROCESSES[("240", "X2")] = "WW"
    cfg = _cfg("240 GeV", "X1")
    components._apply_process_names(cfg)
    hcfg = cfg["histograms"][0]
    assert hcfg["process_names_map"] == {"X2": "WW"}
    assert "process_name" not in hcfg


def test_a_histogram_fitting_a_named_process_shows_the_name():
    components._NAMED_PROCESSES[("240", "X2")] = "WW"
    cfg = _cfg("240 GeV", "X1", "X2")
    components._apply_process_names(cfg)
    assert "process_name" not in cfg["histograms"][0]
    assert cfg["histograms"][1]["process_name"] == "WW"


def test_names_do_not_cross_energies():
    components._NAMED_PROCESSES[("240", "X1")] = "ZH"
    cfg = _cfg("91 GeV", "X1")
    components._apply_process_names(cfg)
    assert "process_names_map" not in cfg["histograms"][0]
    assert "process_name" not in cfg["histograms"][0]


def test_each_process_gets_its_own_discovery_popup():
    components._DISCOVERED.add(("240", "X2"))
    # The histogram that discovered X2 now fits X1: still a new discovery.
    assert components._new_discoveries({0: _res("X1")}) == [(0, _res("X1"))]
    # X2 was already discovered, and results under 5 sigma never pop up.
    assert components._new_discoveries({0: _res("X2"), 1: _res("X3", 4.9)}) == []
    # Two histograms fitting the same process: one popup.
    assert [p for p, _ in components._new_discoveries({0: _res("X1"), 1: _res("X1")})] == [0]
