import os
import sys
import math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.path_filter import (
    _delta_r, _P4Proxy, _ArrayProxy, _delta_r_vec,
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
    from engine.path_filter import _append_event, _P
    acc = make_cache_acc()
    null = _P()
    w_obj = _P(pt=0.0, eta=0.0, phi=0.0, e=0.0)
    # Signature: (acc, nlep, nel, nmu, njets, nphot, nbjets, l1, l2, j1, j2, ph1, ph2, met, w)
    # nbjets=1 is inserted after nphot (new column added for b-tagging systematics)
    _append_event(acc, 2, 1, 1, 0, 0, 1, null, null, null, null, null, null, w_obj, 1.5)

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
    pt, phi = _single_photon_met(12.0, 0.3, 0.5, _RECOIL_MET_E, 30.0, 2.9)
    assert pt == 30.0
    assert abs(phi - (2.9 - math.pi)) < 1e-12


def test_single_photon_met_keeps_multi_particle_recoil():
    # Visible energy (80 GeV) well above |p_miss|: not a single-particle recoil
    assert _single_photon_met(12.0, 0.3, 0.5, 365.0 - 80.0, 30.0, 2.9) == (12.0, 0.3)


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
