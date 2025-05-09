from roibaview.plugins.base import BasePlugin
from roibaview.gui_utils import SimpleInputDialog
from PyQt6.QtWidgets import QMessageBox, QLabel
from PyQt6.QtCore import Qt
import numpy as np
import pyqtgraph as pg


class CutRegionPlugin(BasePlugin):
    name = "Cut ROI Region"
    category = "tool"
    shortcut = "Ctrl+Shift+X"

    def __init__(self, config=None, parent=None):
        self.config = config
        self.parent = parent

    def apply(self, *_):
        controller = getattr(self.parent, "controller", None)
        if not controller or not controller.selected_data_sets:
            QMessageBox.warning(self.parent, "Cut Region", "No data set selected.")
            return

        name = controller.selected_data_sets[0]
        dtype = controller.selected_data_sets_type[0]
        roi = controller.current_roi_idx

        data = controller.data_handler.get_data_set(dtype, name)
        meta = controller.data_handler.get_data_set_meta_data(dtype, name)
        trace = data[:, roi]
        fr = meta["sampling_rate"]
        t = np.linspace(0, trace.shape[0] / fr, trace.shape[0])

        region = pg.LinearRegionItem([t[100], t[200]], movable=True, brush=(255, 0, 0, 50))
        region.setZValue(10)
        controller.data_plotter.master_plot.addItem(region)

        # Show info label
        label = QLabel("Cut Region: Adjust with mouse. Press ⏎ to confirm, Esc to cancel", self.parent)
        label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 10pt;
            }
        """)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        label.setFixedSize(label.sizeHint())
        label.move(120, 100)
        label.show()

        # Key handler
        def on_key_press(event):
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                finalize_cut()
            elif event.key() == Qt.Key.Key_Escape:
                cleanup()

        self.parent.key_pressed.connect(on_key_press)

        def finalize_cut():
            try:
                min_x, max_x = region.getRegion()
                start = int(min_x * fr)
                end = int(max_x * fr)
                cut_trace = trace[start:end]

                dialog = SimpleInputDialog("Cut Region", "New dataset name:")
                if dialog.exec() != dialog.DialogCode.Accepted:
                    cleanup()
                    return

                new_name = dialog.get_input()
                if not new_name:
                    QMessageBox.warning(self.parent, "Cut Region", "Dataset name cannot be empty.")
                    cleanup()
                    return

                new_data = cut_trace[:, np.newaxis]
                controller.data_handler.add_new_data_set(
                    data_set_type=dtype,
                    data_set_name=new_name,
                    data=new_data,
                    sampling_rate=fr,
                    time_offset=0,
                    y_offset=0,
                    header=[f"{name}_cut"]
                )
                controller.add_data_set_to_list(dtype, new_name)
            finally:
                cleanup()

        def cleanup():
            controller.data_plotter.master_plot.removeItem(region)
            label.deleteLater()
            try:
                self.parent.key_pressed.disconnect(on_key_press)
            except TypeError:
                pass  # already disconnected
