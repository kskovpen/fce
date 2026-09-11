"""Cut-flow with several Selection boxes: graph compilation, per-cut counts, stages."""
import os
import sys
import types

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ui.graph as graph
from ui.state import REGISTRY
from engine.path_filter import filter_raw_event_data, make_cache_acc, save_cache
from engine.cutflow_plotter import cutflow_stages


# ---------------------------------------------------------------------------
# Graph compilation (no GUI: dpg widget reads are served from a dict)
# ---------------------------------------------------------------------------

@pytest.fixture
def compile_graph(monkeypatch):
    def _compile(nodes, links, exprs, hists, names=None):
        values = {"cb_energy_0": "160 GeV", "cb_detector_0": "IDEA"}
        values.update({f"txt_sel_{n}": e for n, e in exprs.items()})
        for obs, hist in hists:
            values.update({f"txt_obs_{obs}": "met.pt", f"cb_target_{hist}": "None",
                           f"txt_bins_{hist}": 40, f"txt_range_min_{hist}": 0.0,
                           f"txt_range_max_{hist}": 150.0})
        monkeypatch.setattr(REGISTRY, "nodes", dict(nodes))
        monkeypatch.setattr(REGISTRY, "node_names", dict(names or {}))
        monkeypatch.setattr(REGISTRY, "slot_node", {})
        monkeypatch.setattr(REGISTRY, "links", {})
        for nid in nodes:
            REGISTRY.slot_node[f"slot_out_{nid}"] = nid
            REGISTRY.slot_node[f"slot_in_{nid}"] = nid
        for i, (s, d) in enumerate(links):
            REGISTRY.links[i] = (f"slot_out_{s}", f"slot_in_{d}")
        monkeypatch.setattr(graph, "dpg", types.SimpleNamespace(
            get_value=lambda tag: values[tag],
            does_item_exist=lambda tag: tag in values,
        ))
        return graph.compile_graph_topology()
    return _compile


def test_chained_boxes_each_get_a_stage(compile_graph):
    # Data -> A -> B -> C -> Observable -> Histogram
    cfg = compile_graph(
        {0: "DataSource", 1: "Selection", 2: "Selection", 3: "Selection",
         4: "ObsCustom", 5: "Histogram"},
        [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
        {1: "nlep >= 2", 2: "l1.pt > 20", 3: "l2.pt > 10"}, [(4, 5)])
    (sel,) = cfg["selections"]
    assert sel["sel_exprs"] == ["nlep >= 2", "l1.pt > 20", "l2.pt > 10"]
    assert sel["prefix_nids"] == [1, 2, 3]
    assert sel["prefix_names"] == ["Selection 1", "Selection 2", "Selection 3"]
    assert sel["prefix_n_exprs"] == [1, 2, 3]
    assert sel["node_name"] == "Selection 3"


def test_sibling_branches_do_not_share_cuts(compile_graph):
    # Data -> A; A -> B -> Obs(4) -> Hist(5); A -> C -> Obs(6) -> Hist(7)
    cfg = compile_graph(
        {0: "DataSource", 1: "Selection", 2: "Selection", 3: "Selection",
         4: "ObsCustom", 5: "Histogram", 6: "ObsCustom", 7: "Histogram"},
        [(0, 1), (1, 2), (1, 3), (2, 4), (4, 5), (3, 6), (6, 7)],
        {1: "nlep >= 2", 2: "l1.pt > 20", 3: "l2.pt > 10"}, [(4, 5), (6, 7)])
    by_nid = {s["nid"]: s for s in cfg["selections"]}
    assert by_nid[2]["sel_exprs"] == ["nlep >= 2", "l1.pt > 20"]
    assert by_nid[3]["sel_exprs"] == ["nlep >= 2", "l2.pt > 10"]
    assert by_nid[3]["prefix_nids"] == [1, 3]


def test_custom_box_names_are_used(compile_graph):
    cfg = compile_graph(
        {0: "DataSource", 1: "Selection", 2: "Selection", 3: "ObsCustom", 4: "Histogram"},
        [(0, 1), (1, 2), (2, 3), (3, 4)],
        {1: "nlep >= 2", 2: "l1.pt > 20"}, [(3, 4)], names={1: "Two leptons"})
    (sel,) = cfg["selections"]
    assert sel["prefix_names"] == ["Two leptons", "Selection 2"]


# ---------------------------------------------------------------------------
# Per-cut counts recorded while filtering
# ---------------------------------------------------------------------------

def _muon_events(pts):
    return {
        "weight": np.ones(len(pts)), "MET_pt": np.zeros(len(pts)),
        "muon_pt": pts, "muon_eta": [[0.0] * len(p) for p in pts],
        "muon_phi": [[0.0] * len(p) for p in pts], "muon_e": [[50.0] * len(p) for p in pts],
    }


def test_filter_records_cumulative_cut_counts(tmp_path):
    arrays = _muon_events([[30.0, 15.0], [25.0], [12.0], []])
    cfg = {"mult_cuts": [], "sel_exprs": ["nlep >= 1", "l1.pt > 20", "nlep >= 2"]}
    acc = make_cache_acc()
    filter_raw_event_data(arrays, 4, cfg, None, "", cache_acc=acc)
    assert acc["_cutflow"] == [4, 3, 2, 1]
    assert acc["_n"] == 1

    cache_file = str(tmp_path / "sel.npz")
    save_cache(cache_file, acc)
    assert np.load(cache_file)["cutflow"].tolist() == [4, 3, 2, 1]


# ---------------------------------------------------------------------------
# Cut-flow stages built from caches
# ---------------------------------------------------------------------------

def _write_cache(hdir, h5_sel, sample, n_pass, cutflow=None):
    acc = make_cache_acc()
    acc["_n"] = n_pass
    if cutflow is not None:
        acc["_cutflow"] = cutflow
    os.makedirs(os.path.join(hdir, "cache"), exist_ok=True)
    save_cache(os.path.join(hdir, "cache", f"sel_{h5_sel}_{sample}.npz"), acc)


def test_stages_include_intermediate_chained_boxes(tmp_path):
    hdir = str(tmp_path)
    _write_cache(hdir, "abc", "X1", 5, [80, 40, 20, 5])
    _write_cache(hdir, "abc", "X2", 1, [50, 10, 4, 1])
    selections = [{
        "h5_sel": "abc", "sel_exprs": ["a", "b", "c"], "node_name": "Selection 3",
        "prefix_nids": [1, 2, 3], "prefix_names": ["Selection 1", "Selection 2", "Selection 3"],
        "prefix_n_exprs": [1, 2, 3],
    }]
    stages = cutflow_stages(hdir, ["X1", "X2"], {"X1": 100, "X2": 60}, selections)
    assert stages == [
        ("Total", {"X1": 100, "X2": 60}),
        ("Selection 1", {"X1": 40, "X2": 10}),
        ("Selection 2", {"X1": 20, "X2": 4}),
        ("Selection 3", {"X1": 5, "X2": 1}),
    ]


def test_shared_box_is_counted_once(tmp_path):
    # A -> Obs and A -> B -> Obs: A appears in both entries but is one stage.
    hdir = str(tmp_path)
    _write_cache(hdir, "a", "X1", 40, [80, 40])
    _write_cache(hdir, "ab", "X1", 20, [80, 40, 20])
    selections = [
        {"h5_sel": "a", "sel_exprs": ["a"], "node_name": "Selection 1",
         "prefix_nids": [1], "prefix_names": ["Selection 1"], "prefix_n_exprs": [1]},
        {"h5_sel": "ab", "sel_exprs": ["a", "b"], "node_name": "Selection 2",
         "prefix_nids": [1, 2], "prefix_names": ["Selection 1", "Selection 2"],
         "prefix_n_exprs": [1, 2]},
    ]
    stages = cutflow_stages(hdir, ["X1"], {"X1": 100}, selections)
    assert [name for name, _ in stages] == ["Total", "Selection 1", "Selection 2"]
    assert stages[2][1] == {"X1": 20}


def test_cache_without_cut_counts_keeps_final_stage(tmp_path):
    hdir = str(tmp_path)
    _write_cache(hdir, "ab", "X1", 20)  # older cache format: no per-cut counts
    selections = [{
        "h5_sel": "ab", "sel_exprs": ["a", "b"], "node_name": "Selection 2",
        "prefix_nids": [1, 2], "prefix_names": ["Selection 1", "Selection 2"],
        "prefix_n_exprs": [1, 2],
    }]
    stages = cutflow_stages(hdir, ["X1"], {"X1": 100}, selections)
    assert stages == [("Total", {"X1": 100}), ("Selection 2", {"X1": 20})]
