"""Tests for engine.fitter.run_fit.

All tests in this module are guarded with pytest.importorskip for pyhf and
uproot, so the full suite passes (skips) in environments without those deps.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_th1(f, name, values, variation_keys=None):
    """Write a TH1-equivalent object to an uproot WritableFile.

    Parameters
    ----------
    f : uproot WritableFile
        Open writable ROOT file.
    name : str
        Histogram name inside the file.
    values : list of float
        Bin contents (no under/overflow needed).
    variation_keys : dict[str, list[float]] or None
        Extra histograms to write alongside the nominal, keyed by name.
    """
    import boost_histogram as bh

    n = len(values)
    ax = bh.axis.Regular(n, 0, n)
    h = bh.Histogram(ax)
    h.view()[:] = values
    f[name] = h

    if variation_keys:
        for vname, vvals in variation_keys.items():
            vh = bh.Histogram(ax)
            vh.view()[:] = vvals
            f[vname] = vh


def _make_samples(en="91GeV"):
    """Return a minimal samples dict shaped as {en: {name: {...}}}."""
    return {
        en: {
            "signal": {"label": "Signal", "color": "red"},
            "bkg": {"label": "Background", "color": "blue"},
            "data": {"label": "Data", "color": "black"},
        }
    }


# ---------------------------------------------------------------------------
# Test: run_fit end-to-end with variation templates
# ---------------------------------------------------------------------------

def test_run_fit_returns_finite_with_syst(tmp_path, monkeypatch):
    """run_fit should return finite (mu, significance) when all three
    h_{src}_up variation templates are present in the ROOT files."""
    pyhf = pytest.importorskip("pyhf")      # noqa: F841
    uproot = pytest.importorskip("uproot")
    pytest.importorskip("boost_histogram")  # needed inside _write_th1

    # Point FCE home at the tmp directory so fitter reads from there.
    monkeypatch.setenv("FCE_HOME", str(tmp_path))
    import paths
    paths._fce_home = None  # reset cached value

    en = "91GeV"
    hist_idx = 0
    out_dir = os.path.join(str(tmp_path), "output")
    os.makedirs(out_dir, exist_ok=True)

    samples = _make_samples(en)

    # Bin contents: 10 bins
    sig_nom = [5.0] * 10
    bkg_nom = [20.0] * 10
    data_obs = [b + s for b, s in zip(bkg_nom, sig_nom)]

    # UP variations (slightly inflated)
    def _up(nom, factor):
        return [v * factor for v in nom]

    variations = {
        "h_jec_up": _up(sig_nom, 1.03),
        "h_lep_up": _up(sig_nom, 1.01),
        "h_btag_up": _up(sig_nom, 1.02),
    }
    bkg_variations = {
        "h_jec_up": _up(bkg_nom, 1.03),
        "h_lep_up": _up(bkg_nom, 1.01),
        "h_btag_up": _up(bkg_nom, 1.02),
    }

    sig_path = os.path.join(out_dir, f"hist{hist_idx}_signal.root")
    bkg_path = os.path.join(out_dir, f"hist{hist_idx}_bkg.root")
    data_path = os.path.join(out_dir, f"hist{hist_idx}_data.root")

    with uproot.recreate(sig_path) as f:
        _write_th1(f, "h", sig_nom, variations)
    with uproot.recreate(bkg_path) as f:
        _write_th1(f, "h", bkg_nom, bkg_variations)
    with uproot.recreate(data_path) as f:
        _write_th1(f, "h", data_obs)

    import engine.fitter as fitter
    monkeypatch.setattr(fitter, "hdir", str(tmp_path))

    cfg = {"target": "signal"}
    mu, sig = fitter.run_fit(cfg, samples, en, hist_idx=hist_idx)

    assert mu is not None, "run_fit returned None for mu"
    assert sig is not None, "run_fit returned None for significance"
    assert np.isfinite(mu), f"mu is not finite: {mu}"
    assert np.isfinite(sig), f"significance is not finite: {sig}"
    assert sig >= 0.0, f"significance is negative: {sig}"

    # Reset cached FCE home
    paths._fce_home = None


# ---------------------------------------------------------------------------
# Test: significance with systematics <= significance stat-only
# ---------------------------------------------------------------------------

def test_syst_significance_leq_stat_only(tmp_path, monkeypatch):
    """Significance WITH systematics should be <= stat-only significance.

    We run the fitter twice:
    - syst run: includes h_{src}_up variation templates for all sources
    - stat run: same nominal histos, NO variation templates (only lumi normsys
      and shapesys from bkg_unc apply)

    Systematics add extra uncertainty, so the syst significance cannot exceed
    the stat-only significance.  We allow a small tolerance for numerical noise.
    """
    pyhf = pytest.importorskip("pyhf")   # noqa: F841
    uproot = pytest.importorskip("uproot")
    pytest.importorskip("boost_histogram")  # needed inside _write_th1

    en = "91GeV"
    hist_idx = 0

    def _run(subdir, include_syst):
        out_dir = os.path.join(str(tmp_path), subdir, "output")
        os.makedirs(out_dir, exist_ok=True)

        monkeypatch.setenv("FCE_HOME", os.path.join(str(tmp_path), subdir))
        import paths
        paths._fce_home = None

        sig_nom = [10.0] * 8
        bkg_nom = [40.0] * 8
        data_obs = [b + s for b, s in zip(bkg_nom, sig_nom)]

        variations = {
            "h_jec_up": [v * 1.10 for v in sig_nom],
            "h_lep_up": [v * 1.05 for v in sig_nom],
            "h_btag_up": [v * 1.08 for v in sig_nom],
        }
        bkg_variations = {
            "h_jec_up": [v * 1.10 for v in bkg_nom],
            "h_lep_up": [v * 1.05 for v in bkg_nom],
            "h_btag_up": [v * 1.08 for v in bkg_nom],
        }

        sig_path = os.path.join(out_dir, f"hist{hist_idx}_signal.root")
        bkg_path = os.path.join(out_dir, f"hist{hist_idx}_bkg.root")
        data_path = os.path.join(out_dir, f"hist{hist_idx}_data.root")

        with uproot.recreate(sig_path) as f:
            _write_th1(f, "h", sig_nom,
                       variations if include_syst else None)
        with uproot.recreate(bkg_path) as f:
            _write_th1(f, "h", bkg_nom,
                       bkg_variations if include_syst else None)
        with uproot.recreate(data_path) as f:
            _write_th1(f, "h", data_obs)

        # fitter.hdir is fixed at import, so FCE_HOME alone would leave both
        # runs reading whichever directory the module was first imported with.
        import engine.fitter as fitter
        monkeypatch.setattr(fitter, "hdir", os.path.join(str(tmp_path), subdir))
        cfg = {"target": "signal"}
        mu, sig_val = fitter.run_fit(cfg, _make_samples(en), en, hist_idx=hist_idx)
        paths._fce_home = None
        return mu, sig_val

    _, sig_with_syst = _run("syst", include_syst=True)
    _, sig_stat_only = _run("stat", include_syst=False)

    assert sig_with_syst is not None
    assert sig_stat_only is not None
    # Systematics must cost significance. Strict on purpose: the s/sqrt(b)
    # fallback ignores them and returns the same value for both runs.
    assert sig_with_syst < sig_stat_only - 0.1, (
        f"Syst significance ({sig_with_syst}) not below stat-only ({sig_stat_only})"
    )


# ---------------------------------------------------------------------------
# The pyhf fit actually runs, and the New Physics excess test
# ---------------------------------------------------------------------------

def _fit_dir(tmp_path, monkeypatch, hists, hist_idx=0):
    """Write {sample: bin values} histograms and point the fitter at them."""
    uproot = pytest.importorskip("uproot")
    pytest.importorskip("boost_histogram")
    import engine.fitter as fitter

    out_dir = tmp_path / "output"
    out_dir.mkdir(exist_ok=True)
    for name, vals in hists.items():
        with uproot.recreate(str(out_dir / f"hist{hist_idx}_{name}.root")) as f:
            _write_th1(f, "h", vals)
    monkeypatch.setattr(fitter, "hdir", str(tmp_path))
    return fitter


def _np_samples():
    return {"91GeV": {"X1": {}, "X2": {}, "data": {}}}


def test_run_fit_is_a_real_pyhf_fit(tmp_path, monkeypatch):
    """pyhf must accept the model; a rejected spec used to fall back silently."""
    pytest.importorskip("pyhf")
    fitter = _fit_dir(tmp_path, monkeypatch, {
        "signal": [5.0] * 10, "bkg": [20.0] * 10, "data": [25.0] * 10})

    calls = []
    real = fitter._fit_and_test

    def spy(spec):
        out = real(spec)          # raises if pyhf rejects the spec
        calls.append(out)
        return out

    monkeypatch.setattr(fitter, "_fit_and_test", spy)
    mu, sig = fitter.run_fit({"target": "signal"}, _make_samples(), "91GeV")

    assert calls, "pyhf rejected the model and run_fit fell back to s/sqrt(b)"
    assert abs(mu - 1.0) < 0.01
    # s/sqrt(b) gives 3.54 here; the MC-statistical and luminosity
    # uncertainties of the real fit bring it well below that.
    assert sig < 3.0


def test_new_physics_measures_the_excess_over_all_samples(tmp_path, monkeypatch):
    pytest.importorskip("pyhf")
    # 1000 expected from two samples, 1300 observed: 300 events none describes.
    fitter = _fit_dir(tmp_path, monkeypatch, {
        "X1": [60.0] * 10, "X2": [40.0] * 10, "data": [130.0] * 10})
    excess, sig = fitter.run_fit({"target": fitter.NEW_PHYSICS}, _np_samples(), "91GeV")
    assert abs(excess - 300.0) < 1.0
    assert 3.0 < sig < 10.0


def test_new_physics_without_excess_is_not_significant(tmp_path, monkeypatch):
    pytest.importorskip("pyhf")
    fitter = _fit_dir(tmp_path, monkeypatch, {
        "X1": [60.0] * 10, "X2": [40.0] * 10, "data": [100.0] * 10})
    excess, sig = fitter.run_fit({"target": fitter.NEW_PHYSICS}, _np_samples(), "91GeV")
    assert excess < 1.0
    assert sig < 0.5


def test_new_physics_deficit_reads_as_no_signal(tmp_path, monkeypatch):
    pytest.importorskip("pyhf")
    fitter = _fit_dir(tmp_path, monkeypatch, {
        "X1": [60.0] * 10, "X2": [40.0] * 10, "data": [90.0] * 10})
    excess, sig = fitter.run_fit({"target": fitter.NEW_PHYSICS}, _np_samples(), "91GeV")
    assert excess == 0.0
    assert sig == 0.0


def test_new_physics_needs_data(tmp_path, monkeypatch):
    fitter = _fit_dir(tmp_path, monkeypatch, {"X1": [60.0] * 10, "X2": [40.0] * 10})
    assert fitter.run_fit({"target": fitter.NEW_PHYSICS}, _np_samples(), "91GeV") == (None, None)


def test_poisson_excess_significance():
    from engine.fitter import _poisson_excess_significance
    assert _poisson_excess_significance(100.0, 100.0) == 0.0
    assert _poisson_excess_significance(90.0, 100.0) == 0.0
    assert _poisson_excess_significance(5.0, 0.0) == 0.0
    # sqrt(2 * (130 ln(1.3) - 30)) = 2.866
    assert abs(_poisson_excess_significance(130.0, 100.0) - 2.866) < 1e-3
