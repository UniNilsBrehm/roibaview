from roibaview.plugins.base import BasePlugin
# from roibaview.gui import SimpleInputDialog
from roibaview.gui_utils import DynamicInputDialog
from PyQt6.QtWidgets import QMessageBox, QDialog
import numpy as np
from scipy.signal import butter, sosfiltfilt

"""
# Basic Structure of a Filter Plugin Class with Dialog Input
class FilterPluginName(BasePlugin):
    name = "Filter Name"
    category = "filter"
    
    def __init__(self, **kwargs):
        self.parent = kwargs.get("parent", None)  # needed for dialog parent
    
    # Every Plugin gets the selected data array (samples, rois) and its sampling rate
    def apply(self, data, sampling_rate): 
        dialog = SimpleInputDialog("Filter", "Enter value:", default_value="1")
        # Handling the Dialog:
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                threshold = float(dialog.get_input())
            except ValueError:
                QMessageBox.warning(self.parent, "Invalid Input", "Please enter a numeric threshold.")
                return None
        else:
            return None  # Cancelled
        
        # Here comes the code of whatever the Filter is doing
        filter_output = ...
        return filter_output
"""


class ZapFilterPrompt(BasePlugin):
    name = "Zap Filter"
    category = "filter"

    def __init__(self, **kwargs):
        self.parent = kwargs.get("parent", None)  # needed for dialog parent

    def apply(self, data, sampling_rate):
        fields = {
            'threshold': (1, 'float'),
        }

        dialog = DynamicInputDialog(title="Zap Filter", fields=fields)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_inputs()
            threshold = params['threshold']
            # Apply threshold-based filtering
            return np.where(data > threshold, 0, data)


class MovingAverageFilter(BasePlugin):
    name = "Moving Average Filter"
    category = "filter"

    # def __init__(self, **kwargs):
    #     pass  # if there is no dialog

    def __init__(self, **kwargs):
        self.parent = kwargs.get("parent", None)  # needed for dialog parent

    def apply(self, data, sampling_rate):
        fields = {
            'window': (100, 'float'),
        }

        dialog = DynamicInputDialog(title="Moving Average Filter", fields=fields)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_inputs()
            # (data, fr, window)
            window = params['window']
            window_size = int(window * sampling_rate)
            # Make sure window size is odd
            if window_size % 2 == 0:
                window_size += 1

            pad_width = window_size // 2

            # Define the kernel
            kernel = np.ones(window_size) / window_size
            filtered_data = np.zeros_like(data)
            for i in range(data.shape[1]):
                trace = data[:, i]
                # Pad the input array symmetrically
                padded_array = np.pad(trace, pad_width, mode='symmetric')
                filtered_data[:, i] = np.convolve(padded_array, kernel, mode='valid')

            return filtered_data


class DifferentiateFilter(BasePlugin):
    name = "Differentiate Filter"
    category = "filter"

    def __init__(self, **kwargs):
        pass

    def apply(self, data, sampling_rate):
        return np.diff(data, append=0, axis=0)


class ButterFilterDesign:
    def __init__(self, filter_type, cutoff, fs, order):
        self.filter_type = filter_type
        self.cutoff = cutoff
        self.fs = fs
        self.order = order

    def butter_filter_design(self):
        nyq = 0.5 * self.fs
        normal_cutoff = self.cutoff / nyq
        if normal_cutoff >= 1:
            normal_cutoff = 0.9999
        sos = butter(self.order, normal_cutoff, btype=self.filter_type, output='sos')
        return sos


class LowPassFilter(BasePlugin):
    name = "Low Pass Filter"
    category = 'filter'

    def __init__(self, **kwargs):
        self.parent = kwargs.get("parent", None)  # needed for dialog parent

    def apply(self, data, sampling_rate):
        fields = {
            'cut_off': (100, 'float'),
        }

        dialog = DynamicInputDialog(title="Low Pass Filter", fields=fields)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_inputs()
            cut_off = params['cut_off']
            sos = ButterFilterDesign('lowpass', cut_off, sampling_rate, order=2).butter_filter_design()
            return sosfiltfilt(sos, data, axis=0)


class HighPassFilter(BasePlugin):
    name = "High Pass Filter"
    category = 'filter'

    def __init__(self, **kwargs):
        self.parent = kwargs.get("parent", None)  # needed for dialog parent

    def apply(self, data, sampling_rate):
        fields = {
            'cut_off': (100, 'float'),
        }

        dialog = DynamicInputDialog(title="Low Pass Filter", fields=fields)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_inputs()
            cut_off = params['cut_off']

            sos = ButterFilterDesign('highpass', cut_off, sampling_rate, order=2).butter_filter_design()
            return sosfiltfilt(sos, data, axis=0)


class EnvelopeFilter(BasePlugin):
    name = "Envelope Filter"
    category = 'filter'

    def __init__(self, **kwargs):
        self.parent = kwargs.get("parent", None)  # needed for dialog parent

    def apply(self, data, sampling_rate):
        fields = {
            'cut_off': (100, 'float'),
        }

        dialog = DynamicInputDialog(title="Low Pass Filter", fields=fields)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_inputs()
            cut_off = params['cut_off']

            # Low pass filter the absolute values of the signal in both forward and reverse directions,
            # resulting in zero-phase filtering.
            sos = ButterFilterDesign('lowpass', cut_off, sampling_rate, order=2).butter_filter_design()
            return (np.sqrt(2) * sosfiltfilt(sos, np.abs(data), axis=0)) ** 2
