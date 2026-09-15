import os
import sys
import math
import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.path_filter import (
    _delta_r, _P4Proxy, _ArrayProxy, _MetProxy, _delta_r_vec, _make_met, _missing_energy,
    make_cache_acc, save_cache, _CACHE_KEYS,
    _single_photon_met, filter_raw_event_data,
)


class _Obj:
    pass


def test_delta_r_zero_same_direction():
    a = _Obj()
    a.eta = 1.0
    a.phi = 0.5
    b = _Obj()
    b.eta = 1.0
    b.phi = 0.5
    assert _delta_r(a, b) == 0.0


def test_delta_r_known_value():
    a = _Obj()
    a.eta = 0.0
    a.phi = 0.0
    b = _Obj()
    b.eta = 1.0
    b.phi = 0.0
    assert abs(_delta_r(a, b) - 1.0) < 1e-10


def test_delta_r_phi_wrap():
    a = _Obj()
    a.eta = 0.0
    a.phi = math.pi - 0.1
    b = _Obj()
    b.eta = 0.0
    b.phi = -math.pi + 0.1
    dr = _delta_r(a, b)
    assert dr < 0.3


def test_p4proxy_mass():
    e = np.array([10.0])
    px = np.array([0.0])
    py = np.array([0.0])
    pz = np.array([0.0])
    p4 = _P4Proxy(e, px, py, pz)
    assert abs(float(p4.mass[0]) - 10.0) < 1e-8


def test_p4proxy_add():
    p4a = _P4Proxy(np.array([5.0]), np.array([3.0]), np.array([0.0]), np.array([0.0]))
    p4b = _P4Proxy(np.array([5.0]), np.array([3.0]), np.array([0.0]), np.array([0.0]))
    combined = p4a + p4b
    assert float(combined._e[0]) == 10.0
    assert float(combined._px[0]) == 6.0


def test_p4proxy_pt():
    p4 = _P4Proxy(np.array([10.0]), np.array([3.0]), np.array([4.0]), np.array([0.0]))
    assert abs(float(p4.pt[0]) - 5.0) < 1e-8


def test_p4proxy_energy_aliases():
    p4 = _P4Proxy(np.array([10.0]), np.array([3.0]), np.array([4.0]), np.array([0.0]))
    for name in ("e", "E", "energy"):
        assert float(getattr(p4, name)[0]) == 10.0


def test_p4proxy_mass_aliases():
    p4 = _P4Proxy(np.array([10.0]), np.array([0.0]), np.array([0.0]), np.array([0.0]))
    for name in ("m", "M", "mass"):
        assert abs(float(getattr(p4, name)[0]) - 10.0) < 1e-8


def test_p4proxy_cartesian_components():
    p4 = _P4Proxy(np.array([10.0]), np.array([3.0]), np.array([4.0]), np.array([12.0]))
    assert float(p4.px[0]) == 3.0
    assert float(p4.py[0]) == 4.0
    assert float(p4.pz[0]) == 12.0
    assert abs(float(p4.p[0]) - 13.0) < 1e-8
    assert abs(float(p4.rho[0]) - 5.0) < 1e-8


def test_p4proxy_sub():
    a = _P4Proxy(np.array([9.0]), np.array([5.0]), np.array([0.0]), np.array([2.0]))
    b = _P4Proxy(np.array([4.0]), np.array([1.0]), np.array([0.0]), np.array([2.0]))
    d = a - b
    assert float(d.e[0]) == 5.0
    assert float(d.px[0]) == 4.0
    assert float(d.pz[0]) == 0.0


def test_p4proxy_matches_vector_obj():
    """The vectorized proxy must expose the same names/values as vector.obj,
    otherwise the fast path silently degrades to the per-event fallback."""
    import vector
    kin = [dict(pt=30.0, eta=0.5, phi=0.3, e=40.0),
           dict(pt=20.0, eta=-0.2, phi=2.0, e=25.0)]
    proxies = [_P4Proxy(np.array([k["e"]]),
                        np.array([k["pt"] * math.cos(k["phi"])]),
                        np.array([k["pt"] * math.sin(k["phi"])]),
                        np.array([k["pt"] * math.sinh(k["eta"])]))
               for k in kin]
    ref = vector.obj(**kin[0]) + vector.obj(**kin[1])
    got = proxies[0] + proxies[1]
    for name in ("e", "E", "energy", "m", "M", "mass", "pt", "eta", "phi", "px", "py", "pz"):
        assert abs(float(getattr(got, name)[0]) - float(getattr(ref, name))) < 1e-8, name


def test_array_proxy_missing_key_returns_sentinel():
    data = {"weight": np.array([1.0, 2.0])}
    proxy = _ArrayProxy("l1", data)
    vals = proxy.nonexistent
    assert all(v == -999.0 for v in vals)


def test_array_proxy_reads_key():
    data = {
        "weight": np.array([1.0, 2.0]),
        "l1_pt": np.array([30.0, 40.0]),
    }
    proxy = _ArrayProxy("l1", data)
    assert float(proxy.pt[0]) == 30.0
    assert float(proxy.pt[1]) == 40.0


def test_delta_r_vec_zero():
    a = _Obj()
    a.eta = np.array([1.0])
    a.phi = np.array([0.5])
    b = _Obj()
    b.eta = np.array([1.0])
    b.phi = np.array([0.5])
    dr = _delta_r_vec(a, b)
    assert abs(float(dr[0])) < 1e-10


def test_make_cache_acc_has_all_keys():
    acc = make_cache_acc()
    for key in _CACHE_KEYS:
        assert key in acc
        assert hasattr(acc[key], "__len__")  # pre-allocated numpy array
    assert acc["_n"] == 0


def test_save_cache_and_reload(tmp_path):
    from engine.path_filter import _append_event, _P, JETS
    acc = make_cache_acc()
    null = _P()
    w_obj = _P(pt=0.0, eta=0.0, phi=0.0, e=0.0)
    # Signature: (acc, nlep, nel, nmu, njets, nphot, nbjets, l1, l2, jets, ph1, ph2, met, w)
    # nbjets=1 is inserted after nphot (new column added for b-tagging systematics)
    _append_event(acc, 2, 1, 1, 0, 0, 1, null, null, [null] * len(JETS), null, null, w_obj, 1.5)

    cache_file = str(tmp_path / "test_cache.npz")
    save_cache(cache_file, acc)
    data = np.load(cache_file)
    assert abs(float(data["weight"][0]) - 1.5) < 1e-5
    assert int(data["nlep"][0]) == 2
    assert int(data["nbjets"][0]) == 1


# MET stored as the recoil of one massless particle (pT 12 GeV, eta 0.5) that is
# not the event's photon; MET_e is 365 GeV minus the visible energy.
_RECOIL_MET_E = 365.0 - 12.0 * math.cosh(0.5)


def test_single_photon_met_replaces_single_particle_recoil():
    pt, phi, eta = _single_photon_met(12.0, 0.3, 0.5, _RECOIL_MET_E, 30.0, 2.9, 1.4)
    assert pt == 30.0
    assert abs(phi - (2.9 - math.pi)) < 1e-12
    assert eta == -1.4          # the recoil points opposite the photon


def test_single_photon_met_keeps_multi_particle_recoil():
    # Visible energy (80 GeV) well above |p_miss|: not a single-particle recoil
    assert _single_photon_met(12.0, 0.3, 0.5, 365.0 - 80.0,
                              30.0, 2.9, 1.4) == (12.0, 0.3, 0.5)


def _jagged(*rows):
    out = np.empty(len(rows), dtype=object)
    for k, r in enumerate(rows):
        out[k] = np.asarray(r, dtype=np.float32)
    return out


def test_filter_balances_met_only_in_photon_only_events():
    # Event 0: a photon and nothing else. Event 1: the same plus a jet.
    arrays = {
        "weight": np.array([1.0, 1.0]),
        "MET_pt": np.array([12.0, 12.0]), "MET_phi": np.array([0.3, 0.3]),
        "MET_eta": np.array([0.5, 0.5]),
        "MET_e": np.array([_RECOIL_MET_E, _RECOIL_MET_E]),
        "photon_pt": _jagged([30.0], [30.0]), "photon_eta": _jagged([0.1], [0.1]),
        "photon_phi": _jagged([2.9], [2.9]), "photon_e": _jagged([30.2], [30.2]),
        "jet_pt": _jagged([], [25.0]), "jet_eta": _jagged([], [0.0]),
        "jet_phi": _jagged([], [1.0]), "jet_e": _jagged([], [26.0]),
    }
    acc = make_cache_acc()
    filter_raw_event_data(arrays, 2, {}, None, "", cache_acc=acc)
    assert acc["_n"] == 2
    assert abs(float(acc["met_pt"][0]) - 30.0) < 1e-4
    assert abs(float(acc["met_phi"][0]) - (2.9 - math.pi)) < 1e-4
    assert abs(float(acc["met_pt"][1]) - 12.0) < 1e-4
    assert abs(float(acc["met_phi"][1]) - 0.3) < 1e-4


# ---------------------------------------------------------------------------
# Missing momentum as a full 4-vector
# ---------------------------------------------------------------------------

def test_missing_energy_removes_the_365_offset():
    # MET_e is stored as 365 - Evis whatever the collision energy, so at 91 GeV
    # an event with 91 GeV of visible energy has no missing energy left.
    assert abs(_missing_energy(365.0 - 91.0, 91.0)) < 1e-9
    assert abs(_missing_energy(365.0 - 60.0, 160.0) - 100.0) < 1e-9
    # At 365 GeV the stored value already is the missing energy.
    assert abs(_missing_energy(42.0, 365.0) - 42.0) < 1e-9


def test_make_met_without_energy_has_no_p4():
    met = _make_met(25.0, 1.2)
    assert met.pt == 25.0
    assert met.phi == 1.2
    assert met.p4 == -999.0      # the _P sentinel, i.e. no 4-vector offered


def test_make_met_with_energy_builds_a_4vector():
    met = _make_met(25.0, 1.2, 0.8, 40.0)
    assert abs(met.p4.pt - 25.0) < 1e-9
    assert abs(met.p4.eta - 0.8) < 1e-9
    assert abs(met.p4.e - 40.0) < 1e-9


def test_lepton_plus_met_invariant_mass():
    """The observable the missing 4-vector exists for."""
    import vector
    lep = vector.obj(pt=30.0, eta=0.5, phi=0.3, e=40.0)
    met = _make_met(30.0, 0.3 + math.pi, -0.5, 40.0)   # exactly back-to-back
    total = lep + met.p4
    assert abs(total.pt) < 1e-9                        # momenta cancel
    assert abs(total.mass - 80.0) < 1e-9               # so m = sum of energies


def test_array_proxy_p4_is_nan_where_unavailable():
    """A missing energy or object must drop out, not give a plausible value."""
    data = {
        "weight": np.array([1.0, 1.0, 1.0]),
        "met_pt": np.array([25.0, 25.0, -999.0]),
        "met_eta": np.array([0.8, 0.8, -999.0]),
        "met_phi": np.array([1.2, 1.2, -999.0]),
        "met_e": np.array([40.0, -999.0, -999.0]),
    }
    p4 = _ArrayProxy("met", data).p4
    assert np.isfinite(p4.mass[0])
    assert np.isnan(p4.mass[1])      # energy unknown
    assert np.isnan(p4.mass[2])      # no missing momentum stored at all


def test_dilepton_quantities_of_a_one_lepton_event_are_nan():
    """(l1.p4 + l2.p4) without an l2 used to give mass 0 and energy E1 - 999."""
    lep = {"pt": 30.0, "eta": 0.5, "phi": 0.3, "e": 40.0}
    data = {"weight": np.ones(2)}
    for k, v in lep.items():
        data[f"l1_{k}"] = np.array([v, v])
    for k, v in {"pt": 20.0, "eta": -0.2, "phi": 2.0, "e": 25.0}.items():
        data[f"l2_{k}"] = np.array([v, -999.0])
    ll = _ArrayProxy("l1", data).p4 + _ArrayProxy("l2", data).p4
    for name in ("mass", "e", "pt", "eta", "phi"):
        vals = getattr(ll, name)
        assert np.isfinite(vals[0]), name
        assert np.isnan(vals[1]), name


def test_missing_energy_is_never_below_the_missing_momentum():
    """E_miss = sqrt(s) - E_vis can come out negative; the missing system cannot."""
    p = 10.0 * math.cosh(0.5)
    met = _make_met(10.0, 0.0, 0.5, -3.0)
    assert abs(met.e - p) < 1e-9
    assert abs(met.p4.mass) < 1e-4                  # raised to massless

    data = {
        "weight": np.ones(3),
        "met_pt": np.array([10.0, 10.0, -999.0]),
        "met_eta": np.array([0.5, 0.5, -999.0]),
        "met_phi": np.zeros(3),
        "met_e": np.array([-3.0, 50.0, -999.0]),
    }
    met = _MetProxy(data)
    assert abs(met.e[0] - p) < 1e-9                 # raised to |p|
    assert met.e[1] == 50.0                         # already physical: untouched
    assert met.e[2] == -999.0                       # no MET stored: sentinel kept
    mass = met.p4.mass
    assert abs(mass[0]) < 1e-4
    assert abs(mass[1] - math.sqrt(50.0**2 - p**2)) < 1e-9
    assert np.isnan(mass[2])


# ---------------------------------------------------------------------------
# Jets beyond the second, and names no event defines
# ---------------------------------------------------------------------------

def _jet_cache(tmp_path):
    """Two events: four jets (pT 80/60/40/25), then two jets (pT 70/50)."""
    from engine.path_filter import _append_event, _P, _make_jet, JETS
    acc = make_cache_acc()
    null = _P()
    met = _P(pt=10.0, phi=0.0, eta=0.0, e=10.0)
    for pts in ([80.0, 60.0, 40.0, 25.0], [70.0, 50.0]):
        jets = [_make_jet({"pt": pt, "eta": 0.1 * k, "phi": 0.5 * k, "e": pt * 1.2, "btag": 0.1})
                for k, pt in enumerate(pts)]
        jets += [null] * (len(JETS) - len(jets))
        _append_event(acc, 0, 0, 0, len(pts), 0, 0, null, null, jets, null, null, met, 1.0)
    path = str(tmp_path / "jets.npz")
    save_cache(path, acc)
    return path


def test_third_and_fourth_jets_are_cached(tmp_path):
    data = np.load(_jet_cache(tmp_path))
    assert list(data["j3_pt"]) == [40.0, -999.0]
    assert list(data["j4_pt"]) == [25.0, -999.0]
    assert float(_ArrayProxy("j3", data).pt[0]) == 40.0


def test_cut_on_the_third_jet_keeps_three_jet_events(tmp_path):
    """j3.pt > -1 used to raise NameError on every event and drop them all."""
    from engine.path_filter import filter_selection_cache
    src = _jet_cache(tmp_path)
    for expr in ("j3.pt > -1", "sqrt(j4.pt) > 0"):   # vectorized, then per-event
        out = str(tmp_path / "out.npz")
        filter_selection_cache(src, [expr], out)
        assert list(np.load(out)["njets"]) == [4.0], expr


def test_observable_on_the_fourth_jet(tmp_path):
    pytest.importorskip("boost_histogram")
    from engine.path_filter import fill_histogram_from_cache
    from engine.analytical_loop import hist
    src = _jet_cache(tmp_path)
    for expr, expected in (("j4.pt", 25.0), ("sqrt(j4.pt) ** 2", 25.0)):   # both paths
        h = hist()
        h.create(bins=100, min_val=0, max_val=100)
        fill_histogram_from_cache(src, h, expr, with_syst=False)
        assert h.h["h"].sum() == 1.0, expr
        assert abs(h.h["h"].axes[0].centers[np.argmax(h.h["h"].values())] - expected) < 1.0


def test_unknown_names_are_reported():
    from engine.path_filter import unknown_names
    assert unknown_names("j3.pt > -1 && j4.btag > 0.7") == []
    assert unknown_names("(l1.p4 + met.p4).mass > abs(-3) and deltaR(j1, j4) > 0.4") == []
    assert unknown_names("j5.pt > 20 || !lep1") == ["j5", "lep1"]
