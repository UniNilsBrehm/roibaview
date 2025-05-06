# plugins/filter_zap.py
from roibaview.plugins.base import BasePlugin
import numpy as np

class ZapFilter(BasePlugin):
    name = "Zap Noise Filter"

    def apply(self, data, sampling_rate):
        return np.where(data > 1, 0, data)