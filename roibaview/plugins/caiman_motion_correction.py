try:
    import caiman as cm
    from caiman.motion_correction import MotionCorrect
    from caiman.utils.visualization import inspect_correlation_pnr
    HAS_CAIMAN = True
except ImportError:
    HAS_CAIMAN = False

from roibaview.plugins.base import BasePlugin
from PyQt6.QtWidgets import QFileDialog, QMessageBox
import os


class MotionCorrectionPlugin(BasePlugin):
    name = "Motion Correction (CaImAn)"
    category = "tool"
    unavailable_reason = "CaImAn is not installed. Install it via pip to enable this plugin."

    def __init__(self, config=None, parent=None):
        self.config = config
        self.parent = parent

    @classmethod
    def available(cls):
        return HAS_CAIMAN

    def apply(self, *_):
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Select TIFF file for motion correction",
            "",
            "TIF files (*.tif *.tiff)"
        )

        if not file_path:
            return  # user canceled

        try:
            # Output folder next to original file
            base_dir = os.path.dirname(file_path)
            base_name = os.path.basename(file_path).split('.')[0]
            out_dir = os.path.join(base_dir, base_name + "_mc")
            os.makedirs(out_dir, exist_ok=True)

            # Set up CaImAn motion correction
            mc = MotionCorrect([file_path], dview=None,
                               pw_rigid=True,
                               max_shifts=(6, 6),
                               strides=(48, 48),
                               overlaps=(24, 24),
                               max_deviation_rigid=3,
                               shifts_opencv=True,
                               border_nan='copy')

            mc.motion_correct(save_movie=True)

            corrected_path = mc.fname_tot_els if mc.fname_tot_els else file_path
            QMessageBox.information(
                self.parent,
                "Motion Correction Complete",
                f"Corrected video saved to: {corrected_path}"
            )

        except Exception as e:
            QMessageBox.critical(self.parent, "Motion Correction Error", str(e))
