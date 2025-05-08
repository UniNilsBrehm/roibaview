from roibaview.plugins.base import BasePlugin
from roibaview.gui_utils import DynamicInputDialog
from PyQt6.QtWidgets import QDialog
import pandas as pd
import numpy as np
from scipy.signal import decimate


class ZScore(BasePlugin):
    name = "Z Score"
    category = 'transformation'

    def __init__(self, **kwargs):
        pass

    def apply(self, data, sampling_rate):
        # Check if there is only one ROI (Column)
        if data.shape[1] == 1:
            data = data.flatten()
        return (data - np.mean(data, axis=0)) / np.std(data, axis=0)


class MinMaxTransformation(BasePlugin):
    name = "MinMax Transformation"
    category = 'transformation'

    def __init__(self, **kwargs):
        pass

    def apply(self, data, sampling_rate):
        """ Compute min-max normalization to the range [0, 1]

        :param data: numpy array (columns: ROIs, rows: data points over time)
        :return: Data normalize to the range [0, 1]
        """
        return (data - np.min(data, axis=0)) / (np.max(data, axis=0) - np.min(data, axis=0))


class DeltaFOverF(BasePlugin):
    """ Compute delta F over F for raw fluorescence values
    fbs_per: percentile to calculate baseline (0.0 to 1.0)
    window: window size in seconds for computing sliding percentile baseline (if None, no window is used)
    """

    name = "Delta F over F"
    category = 'transformation'

    def __init__(self, **kwargs):
        pass

    def apply(self, data, sampling_rate):
        fields = {
            'window': (100, 'int'),
            'fbs_per': (10, 'int'),
        }

        dialog = DynamicInputDialog(title="Delta F over F", fields=fields)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_inputs()

            # This is using the pandas rolling method, so we need to convert the data to a DataFrame first
            df = pd.DataFrame(data)
            if params['window'] is None:
                fbs = np.percentile(df, params['fbs_per'], axis=0)
            else:
                per_window = int(params['window'] * sampling_rate)
                quant = params['fbs_per'] / 100
                fbs = df.rolling(window=per_window, center=True, min_periods=0).quantile(quant)

            df_over_f = (df - fbs) / fbs
            return df_over_f


class DownSampling(BasePlugin):
    name = "Down Sampling"
    category = 'transformation'

    def __init__(self, **kwargs):
        pass

    def apply(self, data, sampling_rate):
        fields = {
            'ds_factor': (100, 'int'),
        }

        dialog = DynamicInputDialog(title="Down Sampling", fields=fields)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_inputs()

            # New sampling rate
            new_fs = sampling_rate / params['ds_factor']

            # Apply decimate function to downsample the data
            down_sampled_data = decimate(data, params['ds_factor'], axis=0)

            return down_sampled_data, new_fs

