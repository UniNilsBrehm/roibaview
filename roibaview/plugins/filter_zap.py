from roibaview.plugins.base import BasePlugin
import numpy as np

class ZapFilter(BasePlugin):
    name = "Zap Filter"
    category = "filter"

    def __init__(self, **kwargs):  # <--- ADD THIS
        pass

    def apply(self, data, sampling_rate):
        return np.where(data > 1, 0, data)