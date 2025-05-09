import pyqtgraph as pg
import numpy as np
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QVBoxLayout, QSlider, QLabel, QSpacerItem, QSizePolicy, QMessageBox, QDialog, QPushButton
from scipy import signal
from roibaview.gui_utils import BrowseFileDialog
import pandas as pd
from roibaview.plugins.base import BasePlugin


class PeakDetectionPlugin(BasePlugin):
    name = "Peak Detection"
    category = "tool"
    shortcut = "Ctrl+Shift+P"

    def __init__(self, config=None, parent=None):
        self.config = config
        self.parent = parent
        self.roi_signal = getattr(parent, "signal_roi_idx_changed", None)  # Optional

    def apply(self, *_):
        try:
            # Get controller-level references from the GUI
            controller = getattr(self.parent, "controller", None)
            if not controller:
                raise RuntimeError("Controller not found in GUI context.")

            if not controller.selected_data_sets:
                raise RuntimeError("No dataset selected.")

            # Get current dataset and metadata
            name = controller.selected_data_sets[0]
            dtype = controller.selected_data_sets_type[0]
            roi = controller.current_roi_idx

            data = controller.data_handler.get_data_set(dtype, name)
            meta = controller.data_handler.get_data_set_meta_data(dtype, name)
            fr = meta["sampling_rate"]

            # Get the main data plot
            master_plot = controller.data_plotter.master_plot

            # Create the peak detection dialog
            dialog = PeakDetection(
                data=data + meta["y_offset"],  # match old behavior
                fr=fr,
                master_plot=master_plot,
                roi=roi,
                parent=self.parent
            )

            # Sync with ROI selection signal
            if self.roi_signal:
                self.roi_signal.connect(dialog.roi_changed)
                dialog.finished.connect(lambda: self.roi_signal.disconnect(dialog.roi_changed))

            dialog.exec()

        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self.parent, "Peak Detection Error", str(e))


# class PeakDetection(QWidget):
class PeakDetection(QDialog):

    signal_roi_changed = pyqtSignal(int)
    main_window_closing = pyqtSignal()

    def __init__(self, data, fr, master_plot, roi, parent=None, **kwargs):
        super().__init__(parent)

        self.roi_idx = roi
        self.data = data  # this is the data set
        self.data_trace = self.data[:, self.roi_idx]  # this is the roi trace
        self.fr = fr
        self.time_axis = self.compute_time_axis(self.data_trace.shape[0], self.fr)
        self.master_plot = master_plot
        self.parameters = dict()
        self.parameters_range = dict()
        self.peaks = dict()
        self.set_parameters()
        self.min_range = 0
        self.max_range = 1000
        # self.set_parameters_range()
        self._init_ui()
        self.main_window_running = True
        self.signal_roi_changed.connect(self.roi_changed)
        self.main_window_closing.connect(self.main_window_is_closing)

    def export_peaks(self):
        file_browser = BrowseFileDialog(self)
        file_dir = file_browser.save_file_name('csv file, (*.csv)')
        if file_dir:
            result = pd.DataFrame()
            result['Time'] = self.peaks['times']
            result['ID'] = self.peaks['idx']
            for k in self.peaks['props']:
                result[k] = self.peaks['props'][k]
            result.to_csv(file_dir)

    @staticmethod
    def compute_time_axis(data_size, fr):
        max_time = data_size / fr
        return np.linspace(0, max_time, data_size)

    def main_window_is_closing(self):
        self.main_window_running = False
        self.close()

    def roi_changed(self, new_roi_idx):
        print('ROI CHANGED')
        self.roi_idx = new_roi_idx
        self.data_trace = self.data[:, self.roi_idx]
        self.peaks['times'], self.peaks['idx'], self.peaks['props'] = self.find_peaks(parameters=self.parameters)
        self.update_plot()

    def _init_ui(self):
        layout = QVBoxLayout()
        self.parameters_labels = dict()
        for param_name in self.parameters.keys():
            label = QLabel(param_name)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(self.min_range)
            slider.setMaximum(self.max_range)
            slider.setValue(0)  # Initial value
            slider.setTickInterval(1)
            slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            slider.setTickPosition(QSlider.TickPosition.NoTicks)

            self.parameters_labels[param_name] = QLabel('0')

            # Connect slider signal to update function
            slider.valueChanged.connect(lambda value, param=param_name: self.update_parameter(param, value))

            layout.addWidget(label)
            layout.addWidget(slider)
            layout.addWidget(self.parameters_labels[param_name])
            # Add spacer (width, height)
            spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
            layout.addItem(spacer)

        self.export_button = QPushButton('Export...')
        self.export_button.clicked.connect(self.export_peaks)
        layout.addWidget(self.export_button)

        self.setLayout(layout)
        self.setWindowTitle("Peak Detection Parameters")
        # self.show()

    def update_parameter(self, param_name, value):
        # Update parameter value
        if value == 0:
            self.parameters[param_name] = None
        else:
            self.parameters[param_name] = value

        parameters = self.parameters
        if value is not None:
            if param_name == 'height':
                parameters[param_name] = self.map_range(value, self.min_range, self.max_range, 0, np.max(self.data_trace))
            if param_name == 'threshold':
                parameters[param_name] = self.map_range(value, self.min_range, self.max_range, 0, np.max(self.data_trace)*0.1)
            if param_name == 'prominence':
                parameters[param_name] = self.map_range(value, self.min_range, self.max_range, 0, np.max(self.data_trace)*0.25)
            if param_name == 'distance':
                parameters[param_name] = self.map_range(value, self.min_range, self.max_range, 1, self.data_trace.shape[0]*0.5)
            if param_name == 'width':
                parameters[param_name] = self.map_range(value, self.min_range, self.max_range, 1, self.data_trace.shape[0]*0.05)
        else:
            parameters[param_name] = None

        # Update Value Label
        self.parameters_labels[param_name].setText(f'{parameters[param_name]:.2f}')

        # Update find peaks
        self.peaks['times'], self.peaks['idx'], self.peaks['props'] = self.find_peaks(parameters)

        # Update Plot
        self.update_plot()

    def clear_plot(self):
        # check if there is already roi data plotted and remove it
        item_list = self.master_plot.items.copy()
        for item in item_list:
            if item.name() is not None:
                if item.name().startswith('peaks'):
                    self.master_plot.removeItem(item)

    def update_plot(self):
        # Check if there is already roi data plotted and remove it
        self.clear_plot()

        # Create new  plot item
        plot_data_item = pg.ScatterPlotItem(
            # self.peaks['times'], self.data_trace[self.peaks['idx']],
            self.time_axis[self.peaks['idx']], self.data_trace[self.peaks['idx']],
            pen=pg.mkPen(color=(255, 0, 0)),
            brush=pg.mkBrush(color=(255, 0, 0)),
            size=50,
            symbol='arrow_down',
            name=f'peaks',
            skipFiniteCheck=True,
            tip=None,
            hoverable=True,
            hoverSize=100
        )
        # Add plot item to the plot widget
        self.master_plot.addItem(plot_data_item)

    def set_parameters(self):
        self.parameters['height'] = None
        self.parameters['threshold'] = None
        self.parameters['distance'] = None
        self.parameters['prominence'] = None
        # self.parameters['prominence_wlen'] = None
        self.parameters['width'] = None
        # self.parameters['width_rel_height'] = None
        # self.parameters['plateau_size'] = None

    @staticmethod
    def map_range(value, from_min, from_max, to_min, to_max):
        # First, scale the value from the input range to a 0-1 range
        scaled_value = (value - from_min) / (from_max - from_min)

        # Then, scale the value to fit within the output range
        mapped_value = to_min + (to_max - to_min) * scaled_value

        return mapped_value

    def find_peaks(self, parameters):
        peaks, props = signal.find_peaks(self.data_trace, **parameters)
        peaks_time = peaks / self.fr
        return peaks_time, peaks, props

    def closeEvent(self, event):
        if self.main_window_running:
            reply = QMessageBox.question(
                self, 'Message',
                "Are you sure to quit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._cleanup_on_close()
                self.done(QDialog.DialogCode.Accepted)
                event.accept()
            else:
                event.ignore()
        else:
            self._cleanup_on_close()
            self.done(QDialog.DialogCode.Accepted)
            event.accept()

    def _cleanup_on_close(self):
        """Disconnects signals and clears peak visuals."""
        try:
            self.signal_roi_changed.disconnect(self.roi_changed)
        except Exception:
            pass

        try:
            self.main_window_closing.disconnect()
        except Exception:
            pass

        self.clear_plot()