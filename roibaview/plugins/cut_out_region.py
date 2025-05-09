from roibaview.plugins.base import BasePlugin
from roibaview.gui_utils import SimpleInputDialog
from PyQt6.QtWidgets import QMessageBox, QLabel
from PyQt6.QtCore import Qt, QObject
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
            QMessageBox.warning(self.parent, "Cut Region", "No data sets selected.")
            return

        # Launch tool
        self.tool = CutRegionTool(controller=controller, parent=self.parent)
        self.tool.start()


class CutRegionTool(QObject):
    def __init__(self, controller, parent):
        super().__init__(parent)
        self.controller = controller
        self.parent = parent
        self.region = None
        self.label = None

    def start(self):
        roi = self.controller.current_roi_idx
        self.selected = list(zip(self.controller.selected_data_sets, self.controller.selected_data_sets_type))

        # Estimate time range
        durations = []
        for name, dtype in self.selected:
            data = self.controller.data_handler.get_data_set(dtype, name)
            meta = self.controller.data_handler.get_data_set_meta_data(dtype, name)
            durations.append(data.shape[0] / meta["sampling_rate"])
        max_duration = max(durations)
        t_vis = np.linspace(0, max_duration, 1000)

        self.region = pg.LinearRegionItem([t_vis[100], t_vis[200]], movable=True, brush=(255, 0, 0, 50))
        self.region.setZValue(10)
        self.controller.data_plotter.master_plot.addItem(self.region)

        # Label
        self.label = QLabel("Cut Region: Adjust with mouse, press ⏎ to confirm, Esc to cancel", self.parent)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 10pt;
            }
        """)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.label.adjustSize()
        self.label.move(120, 100)
        self.label.show()

        self.parent.key_pressed.connect(self._on_key_press)

    def _on_key_press(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._finalize_cut()
        elif event.key() == Qt.Key.Key_Escape:
            self._cleanup()

    def _finalize_cut(self):
        try:
            min_x, max_x = self.region.getRegion()
            if max_x <= min_x:
                QMessageBox.warning(self.parent, "Cut Region", "Invalid region selected.")
                self._cleanup()
                return

            # Ask for suffix
            dialog = SimpleInputDialog("Cut Region", "Suffix for new dataset name:", default_value="cut")
            if dialog.exec() != dialog.DialogCode.Accepted:
                self._cleanup()
                return

            suffix = dialog.get_input().strip()
            if not suffix:
                QMessageBox.warning(self.parent, "Cut Region", "Suffix cannot be empty.")
                self._cleanup()
                return

            for name, dtype in self.selected:
                data = self.controller.data_handler.get_data_set(dtype, name)
                meta = self.controller.data_handler.get_data_set_meta_data(dtype, name)
                fr = meta["sampling_rate"]

                start = int(min_x * fr)
                end = int(max_x * fr)
                if end <= start:
                    continue

                cut_data = data[start:end] if data.ndim == 1 else data[start:end, :]
                new_name = f"{name}_{suffix}"

                self.controller.data_handler.add_new_data_set(
                    data_set_type=dtype,
                    data_set_name=new_name,
                    data=cut_data,
                    sampling_rate=fr,
                    time_offset=0,
                    y_offset=0,
                    header=meta.get("roi_names", list(range(cut_data.shape[1] if cut_data.ndim > 1 else 1)))
                )
                self.controller.add_data_set_to_list(dtype, new_name)
        finally:
            self._cleanup()

    def _cleanup(self):
        if self.region:
            self.controller.data_plotter.master_plot.removeItem(self.region)
        if self.label:
            self.label.deleteLater()
        try:
            self.parent.key_pressed.disconnect(self._on_key_press)
        except Exception:
            pass

    # def __del__(self):
    #     print("CutRegionTool deleted.")
