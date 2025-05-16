import json
import os
import math
import subprocess
import cv2
from tifffile import imwrite
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLabel, QCheckBox, QComboBox, QApplication, QDoubleSpinBox, QLineEdit,
    QGroupBox, QFormLayout, QTextEdit
)
import ffmpy
from roibaview.plugins.base import BasePlugin


class VideoConverterPlugin(BasePlugin):
    name = "Video Converter"
    category = "utils"

    def __init__(self, config=None, parent=None):
        self.config = config
        self.parent = parent

    def apply(self, *_):
        self.window = VideoConverter(self.config)
        self.window.show()


class VideoConverter(QMainWindow):

    ffmpeg_dir_set = pyqtSignal()

    def __init__(self, convert_settings):
        super().__init__()

        self.settings = convert_settings
        self.input_file = None
        self.output_file = None

        self.crf_value = 17
        self.preset = 'superfast'
        self.output_frame_rate = 0

        self.use_gpu = False
        self.supress_terminal_output = True
        self.rescale_video_state = False

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        # Widgets
        self.browse_button = QPushButton("Browse Files")
        self.browse_button.clicked.connect(self.browse_files)

        self.input_file_label = QLabel('Input File not selected')
        self.output_file_label = QLabel('Output File not selected')

        self.start_button = QPushButton("Convert Video")
        self.start_button.clicked.connect(self.start_converting)

        self.extract_frames_button = QPushButton("Extract Frames")
        self.extract_frames_button.clicked.connect(self.start_extracting_frames)

        self.batch_button = QPushButton("Batch Processing ...")
        self.batch_button.clicked.connect(self.batch_processing)

        self.change_ffmpeg_dir_button = QPushButton("Set ffmpeg directory")
        self.change_ffmpeg_dir_button.clicked.connect(self.browse_file_ffmpeg)

        self.ffmpeg_dir_label = QLabel(f'ffmpeg at: {self.settings["FFMPEG"]["dir"]}')

        self.gpu_check_box = QCheckBox()
        self.gpu_check_box.setCheckState(Qt.CheckState.Unchecked)
        self.gpu_check_box.stateChanged.connect(self.get_gpu_state)
        self.gpu_check_box_label = QLabel('Use GPU')

        self.supress_terminal_output_check_box = QCheckBox()
        self.supress_terminal_output_check_box.setCheckState(Qt.CheckState.Checked)
        self.supress_terminal_output_check_box.stateChanged.connect(self.get_supress_state)
        self.supress_terminal_output_label = QLabel('Suppress Terminal Output')

        self.quality_combo_box = QComboBox()
        self.quality_combo_box.addItems(['veryslow', 'slower', 'slow', 'medium', 'fast', 'faster', 'veryfast'])
        self.quality_combo_box_label = QLabel('Compression Preset')

        self.constant_rate_factor = QDoubleSpinBox()
        self.constant_rate_factor.setValue(self.crf_value)
        self.constant_rate_factor_label = QLabel('Video Quality: CRF (0-51, visually lossless=17)')

        self.change_frame_rate = QDoubleSpinBox()
        self.change_frame_rate.setValue(0)
        self.change_frame_rate_label = QLabel('Output Frame Rate (Hz, 0 to ignore)')

        self.rescale_check_box = QCheckBox()
        self.rescale_check_box.setCheckState(Qt.CheckState.Unchecked)
        self.rescale_check_box.stateChanged.connect(self.get_rescale_state)
        self.rescale_check_box_label = QLabel('Rescale Video')
        self.rescale_user_input = QLineEdit('WidthxHeight')

        self.status_label = QLabel('Ready')

        # --- Group Layouts ---
        io_group = QGroupBox("File Selection")
        io_layout = QVBoxLayout()
        io_layout.addWidget(self.browse_button)
        io_layout.addWidget(self.input_file_label)
        io_layout.addWidget(self.output_file_label)
        io_layout.addWidget(self.change_ffmpeg_dir_button)
        io_layout.addWidget(self.ffmpeg_dir_label)
        io_group.setLayout(io_layout)

        options_group = QGroupBox("Conversion Options")
        options_layout = QFormLayout()
        options_layout.addRow(self.gpu_check_box_label, self.gpu_check_box)
        options_layout.addRow(self.supress_terminal_output_label, self.supress_terminal_output_check_box)
        options_layout.addRow(self.quality_combo_box_label, self.quality_combo_box)
        options_layout.addRow(self.constant_rate_factor_label, self.constant_rate_factor)
        options_layout.addRow(self.change_frame_rate_label, self.change_frame_rate)
        rescale_layout = QHBoxLayout()
        rescale_layout.addWidget(self.rescale_check_box)
        rescale_layout.addWidget(self.rescale_user_input)
        options_layout.addRow(self.rescale_check_box_label, rescale_layout)
        options_group.setLayout(options_layout)

        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        self.load_config_button = QPushButton("Load Config")
        self.save_config_button = QPushButton("Save Config")
        self.load_config_button.clicked.connect(self.load_config)
        self.save_config_button.clicked.connect(self.save_config)
        actions_layout.addWidget(self.start_button)
        actions_layout.addWidget(self.extract_frames_button)
        actions_layout.addWidget(self.batch_button)
        actions_layout.addWidget(self.load_config_button)
        actions_layout.addWidget(self.save_config_button)
        actions_group.setLayout(actions_layout)

        layout.addWidget(io_group)
        layout.addWidget(options_group)
        layout.addWidget(actions_group)
        layout.addWidget(self.status_label)

        # Logging area
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.log_box.clear)
        layout.addWidget(self.clear_log_button)

        self.setCentralWidget(central_widget)
        self.setWindowTitle("Video Converter")

        if self.settings['FFMPEG']['dir'] == 'NaN':
            self.browse_file_ffmpeg()
        self.ffmpeg_dir = self.settings['FFMPEG']['dir']
        self.ffmpeg_probe = f'{os.path.split(self.ffmpeg_dir)[0]}/ffprobe.exe'
        self._define_ffmpeg_settings()

    def log(self, message):
        self.log_box.append(message)

    def save_config(self):
        config_data = {
            "use_gpu": self.use_gpu,
            "suppress_output": self.supress_terminal_output,
            "preset": self.quality_combo_box.currentText(),
            "crf": self.constant_rate_factor.value(),
            "frame_rate": self.change_frame_rate.value(),
            "rescale": self.rescale_video_state,
            "rescale_size": self.rescale_user_input.text(),
        }
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Config", "", "JSON Files (*.json)")
        if file_name:
            with open(file_name, 'w') as f:
                json.dump(config_data, f, indent=4)
            self.status_label.setText('Configuration saved.')
            self.log('Configuration saved.')

    def load_config(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Config", "", "JSON Files (*.json)")
        if file_name:
            with open(file_name, 'r') as f:
                config_data = json.load(f)
            self.gpu_check_box.setChecked(config_data.get("use_gpu", False))
            self.supress_terminal_output_check_box.setChecked(config_data.get("suppress_output", True))
            self.constant_rate_factor.setValue(config_data.get("crf", 17))
            self.change_frame_rate.setValue(config_data.get("frame_rate", 0))
            self.rescale_check_box.setChecked(config_data.get("rescale", False))
            self.rescale_user_input.setText(config_data.get("rescale_size", 'WidthxHeight'))
            preset = config_data.get("preset", "medium")
            index = self.quality_combo_box.findText(preset)
            if index != -1:
                self.quality_combo_box.setCurrentIndex(index)
            self.status_label.setText('Configuration loaded.')
            self.log('Configuration loaded.')

    def batch_processing(self):
        input_dir = QFileDialog.getExistingDirectory(self)
        if input_dir:
            # Get Files
            self.log("++++ BATCH PROCESSING ++++")
            self.input_file_label.setText("Batch Processing ...")
            file_list = os.listdir(input_dir)
            for f_name in file_list:
                self.input_file = f'{input_dir}/{f_name}'
                self.output_file = f'{input_dir}/{f_name[:-4]}_batch.mp4'
                self.log(f"++++ STARTING: {self.input_file} ++++")
                self._define_ffmpeg_settings()
                self.please_wait_status()
                QApplication.processEvents()
                self.convert_video(self.input_file, self.output_file)
                self.finished_status()

    def convert_to_tiff_stack(self):
        input_video = self.input_file
        output_tiff = self.output_file
        chunk_size = 300

        cap = cv2.VideoCapture(input_video)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        num_chunks = math.ceil(total_frames / chunk_size)

        for chunk_idx, start_frame in enumerate(range(0, total_frames, chunk_size)):
            frames = []
            cap_chunk = cv2.VideoCapture(input_video)
            cap_chunk.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            for _ in range(chunk_size):
                ret, frame = cap_chunk.read()
                if ret:
                    frames.append(frame)
                else:
                    break

            imwrite(output_tiff, frames, append=True, bigtiff=True, compression='deflate')
            self.log(f"Processed chunk {chunk_idx + 1}/{num_chunks}")

            cap_chunk.release()  # Release the video capture object

        cap.release()  # Release the main video capture object

    def _define_ffmpeg_settings(self):
        self.ffmpeg_input_opt = {'gpu': ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'], 'cpu': None}

        # Get Values
        self.crf_value = int(self.constant_rate_factor.value())
        self.preset = self.quality_combo_box.currentText()
        self.output_frame_rate = int(self.change_frame_rate.value())

        if self.crf_value > 51:
            self.crf_value = 51

        # First define the basic settings
        self.ffmpeg_output_opt = {
            'gpu': ['-c:v', 'h264_nvenc', '-preset', self.preset, '-qp', str(self.crf_value)],
            'cpu': ['-c:v', 'libx264', '-preset', self.preset, '-crf', str(self.crf_value)],
            'avi': ['-an', '-vcodec', 'rawvideo', '-y']
        }

        # Now add more settings if desired
        # Change frame rate
        if self.output_frame_rate > 0:
            self.ffmpeg_output_opt['gpu'].extend(['-filter:v', f'fps={self.output_frame_rate}'])
            self.ffmpeg_output_opt['cpu'].extend(['-filter:v', f'fps={self.output_frame_rate}'])
            self.ffmpeg_output_opt['avi'].extend(['-filter:v', f'fps={self.output_frame_rate}'])

        # Change size
        if self.rescale_video_state:
            # Get Video Size in Pixel
            video_size = self.rescale_user_input.text()
            video_size = video_size.split('x')
            if len(video_size) == 2:
                self.log(f'New Video Size: {video_size[0]} x {video_size[1]} pixel')
            else:
                self.log('Input incorrect!')
                return None
            self.ffmpeg_output_opt['gpu'].extend(['-vf', f'scale_cuda={video_size[0]}:{video_size[1]}'])
            self.ffmpeg_output_opt['cpu'].extend(['-vf', f'scale={video_size[0]}:{video_size[1]}'])
            self.ffmpeg_output_opt['avi'].extend(['-vf', f'scale={video_size[0]}:{video_size[1]}'])

        self.ffmpeg_global_opt = {
            'supress': ['-y', '-loglevel', 'quiet'],
            'show': ['-y'],
        }

    def get_rescale_state(self):
        if self.rescale_check_box.checkState() == Qt.CheckState.Checked:
            self.rescale_video_state = True
        else:
            self.rescale_video_state = False

    def get_gpu_state(self):
        if self.gpu_check_box.checkState() == Qt.CheckState.Checked:
            self.use_gpu = True
            # change presets
            self.quality_combo_box.clear()
            self.quality_combo_box.addItem('slow')
            self.quality_combo_box.addItem('medium')
            self.quality_combo_box.addItem('fast')
        else:
            self.use_gpu = False
            # change presets
            self.quality_combo_box.clear()
            self.quality_combo_box.addItem('veryslow')
            self.quality_combo_box.addItem('slower')
            self.quality_combo_box.addItem('slow')
            self.quality_combo_box.addItem('medium')
            self.quality_combo_box.addItem('fast')
            self.quality_combo_box.addItem('faster')
            self.quality_combo_box.addItem('veryfast')

    def get_supress_state(self):
        if self.supress_terminal_output_check_box.checkState() == Qt.CheckState.Checked:
            self.supress_terminal_output = True
        else:
            self.supress_terminal_output = False

    def get_video_info(self, filename):
        result = subprocess.run([self.ffmpeg_probe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                                 "stream=duration:stream=avg_frame_rate", "-of",
                                 "default=noprint_wrappers=1:nokey=1", filename],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        output = result.stdout.decode("utf-8").split('\r\n')
        frame_rate = float(output[0].split('/')[0])  # Extracting the first part before '/'
        duration = float(output[1])

        return frame_rate, duration

    def extract_frames(self, input_file, save_dir):
        if self.ffmpeg_dir is not None:
            # ffmpeg -i input.mp4 -vf fps=1 %04d.png
            video_frame_rate, video_duration = self.get_video_info(input_file)

            if self.output_frame_rate > 0:
                output_cmd = ['-vf', f'fps={self.output_frame_rate}']
                fr = self.output_frame_rate
            else:
                output_cmd = None
                fr = video_frame_rate

            number_of_frames = int(fr * video_duration)
            self.log(f'++++ Expecting to Store {number_of_frames} Frames to HDD+++')
            counter = len(str(number_of_frames)) + 1
            output_dir = f'{save_dir}/%0{counter}d.jpg'
            if self.supress_terminal_output:
                global_settings = self.ffmpeg_global_opt['supress']
            else:
                global_settings = self.ffmpeg_global_opt['show']

            ff = ffmpy.FFmpeg(
                executable=self.ffmpeg_dir,
                global_options=global_settings,
                inputs={input_file: None},
                outputs={output_dir: output_cmd}
            )
            ff.run()

    def start_extracting_frames(self):
        file_dir = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if self.input_file is not None and file_dir is not None:
            self.log('START EXTRACTING')
            # self._define_ffmpeg_settings()
            self.output_frame_rate = int(self.change_frame_rate.value())
            self.please_wait_status()
            QApplication.processEvents()
            self.extract_frames(self.input_file, file_dir)
            self.finished_status()

    def convert_video(self, input_file, output_file):
        if self.ffmpeg_dir is not None:
            if output_file[-3:] == 'tif':
                self.log('CONVERT TO TIFF')
                self.convert_to_tiff_stack()
            else:
                # check settings
                if self.use_gpu:
                    hw = 'gpu'
                else:
                    hw = 'cpu'

                if output_file[-3:] == 'avi':
                    # Use no compression for avi file (otherwise you can not open it in imagej)
                    input_cmd = self.ffmpeg_input_opt['cpu']
                    output_cmd = self.ffmpeg_output_opt['avi']
                else:
                    input_cmd = self.ffmpeg_input_opt[hw]
                    output_cmd = self.ffmpeg_output_opt[hw]

                if self.supress_terminal_output:
                    global_settings = self.ffmpeg_global_opt['supress']
                else:
                    global_settings = self.ffmpeg_global_opt['show']
                    # Print ffmpeg settings to terminal
                    self.log("FFMPEG COMMAND:")
                    self.log(f'INPUT: {input_cmd}')
                    self.log(f'OUTPUT: {output_cmd}')

                ff = ffmpy.FFmpeg(
                    executable=self.ffmpeg_dir,
                    global_options=global_settings,
                    inputs={input_file: input_cmd},
                    outputs={output_file: output_cmd}
                )
                if self.supress_terminal_output:
                    out, err = ff.run(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self.log(out.decode('utf-8'))
                    self.log(err.decode('utf-8'))
                else:
                    ff.run()

    def browse_file_ffmpeg(self):
        self.ffmpeg_dir, _ = QFileDialog.getOpenFileName(self, "Select FFMPEG .exe", "", "ffmpeg (*.exe)")
        # self.settings.modify_setting('ffmpeg', self.ffmpeg_dir)
        self.settings['FFMPEG']['dir'] = self.ffmpeg_dir
        with open('roibaview/config.ini', 'w') as configfile:
            self.settings.write(configfile)
        self.ffmpeg_dir_label.setText(f'ffmpeg at: {self.ffmpeg_dir}')

    def please_wait_status(self):
        self.status_label.setText('Please wait ... ')
        self.log('Please wait ...')
        self.browse_button.setDisabled(True)
        self.change_ffmpeg_dir_button.setDisabled(True)

    def finished_status(self):
        self.status_label.setText('Converting finished!')
        self.browse_button.setDisabled(False)
        self.change_ffmpeg_dir_button.setDisabled(False)
        if not self.supress_terminal_output:
            self.log(f"++++ FINISHED: {os.path.split(self.input_file)[1]} --> {os.path.split(self.output_file)[1]} ++++")

    def browse_files(self):
        input_file, _ = QFileDialog.getOpenFileName(
            self, "Select Input File", "", "Video Files (*.mp4; *.avi; *.mkv; *.mpeg; *.mpg)")
        if input_file:
            self.input_file = input_file
            self.input_file_label.setText(input_file)

    def start_converting(self):
        output_file, _ = QFileDialog.getSaveFileName(
            self, "Select Output File", "", "MP4, (*.mp4);; AVI, (*.avi);; MKV, (*.mkv);; TIF, (*.tif)")
        if output_file:
            self.output_file = output_file
            self.output_file_label.setText(output_file)

        if self.input_file is not None and self.output_file is not None:
            self._define_ffmpeg_settings()
            self.log('==== START CONVERTING VIDEO ====')
            self.please_wait_status()
            QApplication.processEvents()
            self.convert_video(self.input_file, self.output_file)
            self.finished_status()
