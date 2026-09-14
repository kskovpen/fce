import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.export import png_export_name, export_png


def test_png_export_name_uses_detector_energy_and_observable():
    cfg = {"detector": "IDEA", "energy": "91 GeV",
           "histograms": [{"plot_idx": 0, "observable": "met.pt"},
                          {"plot_idx": 1, "observable": "(l1.p4 + l2.p4).mass"}]}
    assert png_export_name(cfg, 0) == "IDEA_91GeV_met_pt.png"
    assert png_export_name(cfg, 1) == "IDEA_91GeV_l1_p4_l2_p4_mass.png"
    assert png_export_name(cfg, None) == "IDEA_91GeV_cutflow.png"


def test_png_export_name_before_any_run():
    assert png_export_name(None, 2) == "plot3.png"
    assert png_export_name(None, None) == "cutflow.png"


def test_export_png_copies_and_fixes_extension(tmp_path):
    src = tmp_path / "hist_0.png"
    src.write_bytes(b"\x89PNG fake")
    out = export_png(str(src), str(tmp_path / "my_plot"))
    assert out == str(tmp_path / "my_plot.png")
    assert (tmp_path / "my_plot.png").read_bytes() == b"\x89PNG fake"
    assert export_png(str(src), str(tmp_path / "other.*")) == str(tmp_path / "other.png")
    assert export_png(str(src), str(tmp_path / "kept.PNG")) == str(tmp_path / "kept.PNG")
