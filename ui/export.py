"""Saving rendered plots as PNG files (kept free of GUI imports for testing)."""
import re
import shutil


def png_export_name(cfg: dict | None, plot_idx: int | None) -> str:
    """Suggested file name for a plot, e.g. "IDEA_91GeV_met_pt.png".

    cfg is the configuration of the last run; plot_idx None means the cut-flow chart.
    """
    cfg = cfg or {}
    if plot_idx is None:
        what = "cutflow"
    else:
        what = next((h.get("observable", "") for h in cfg.get("histograms", [])
                     if h.get("plot_idx") == plot_idx), "") or f"plot{plot_idx + 1}"
    parts = [cfg.get("detector", ""), cfg.get("energy", "").replace(" ", ""), what]
    name = re.sub(r"[^A-Za-z0-9]+", "_", "_".join(p for p in parts if p)).strip("_")
    return name + ".png"


def export_png(src: str, dest: str) -> str:
    """Copy the rendered PNG src to dest, adding ".png" if missing; return the path written."""
    dest = dest.strip()
    if dest.endswith(".*"):  # the file dialog can append its filter pattern
        dest = dest[:-2]
    if not dest.lower().endswith(".png"):
        dest += ".png"
    shutil.copyfile(src, dest)
    return dest
