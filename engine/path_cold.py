import os
import pickle
from ui.state import get_run_state, update_run_state
import uproot

def try_load_cache_stages(cfg, s, hdir, outHist):
    """
    Safely bypasses obsolete cache stages to prevent disk bottlenecks.
    """
    return False, False
