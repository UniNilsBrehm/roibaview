# RoiBaView

[![PyPI version](https://badge.fury.io/py/roibaview.svg)](https://pypi.org/project/roibaview/)  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**RoiBaView** is an **interactive Python tool for plotting, analyzing, and exploring ROI-based signals** from experiments like **Calcium Imaging** and **Biomedical Data Acquisition**.  
Visualize, detect peaks, sync data with videos, and manage your datasets with an intuitive graphical interface.

[Try RoiBaView Online (Docs & Demo)](https://uninilsbrehm.github.io/roibaview/)  
[Install from PyPI](https://pypi.org/project/roibaview/)

---

## Features

- Import and visualize ROI-based time-series data (from CSV files)
- Peak detection with adjustable parameters and live preview
- Video viewer for syncing recorded videos (or TIFF stacks) with data traces
- CSV file format converter (handle different separators)
- Built-in video converter powered by **ffmpeg**
- Easy-to-use interface for data management and export
- Designed for experiments like **calcium imaging**, **electrophysiology**, and more

---

## Installation

1. Create a new environment (e.g., using Anaconda):

    ```bash
    conda create -n roibaview
    ```

2. Activate the environment and ensure pip is installed:

    ```bash
    conda activate roibaview
    conda install pip
    ```

3. Install RoiBaView via PyPI:

    ```bash
    pip install roibaview
    ```

---

## Importing Data

You can import data from **CSV files**:

- Go to **File → Import CSV file...**
- Supported structure:

| ROI_1 | ROI_2 | ... | ROI_n |
|------|------|-----|------|
| x₀ | x₀ | ... | x₀ |
| x₁ | x₁ | ... | x₁ |
| ... | ... | ... | ... |

- Specify the sampling rate (Hz) when prompted.
- If the dataset is **global** (same trace across ROIs), check the **Global Dataset** option.

**Note:** Only CSVs with **comma (`,`) separator** are supported.  
Need to convert from another separator? Use:  
**Tools → Convert CSV files**

---

## Plotting and Data Analysis

- After importing, your datasets appear on the left sidebar.
- **Left-click** to activate a dataset.
- **Right-click** for more options (rename, modify, etc.)

---

## Peak Detection

- Activate a dataset, then click **Detect Peaks**.
- Customize detection parameters and watch live detection updates.
- Export detected peak information to CSV.

---

## Video Viewer & Converter

- Open the **Video Viewer** under **Tools → Open Video Viewer**.
- Connect video frames to ROI data for synchronized viewing.
- **Video Converter** (Tools → Open Video Converter) lets you:
  - Convert between formats using **FFmpeg** (you must have it installed).

Download FFmpeg from [https://ffmpeg.org/](https://ffmpeg.org/).

---

## Documentation & Links

- [PyPI Project Page](https://pypi.org/project/roibaview/)
- [Live Documentation + Website](https://uninilsbrehm.github.io/roibaview/)
- [Source Code on GitHub](https://github.com/UniNilsBrehm/roibaview)

---

## Author

Developed by **Nils Brehm** (2025)  
License: [MIT License](https://opensource.org/licenses/MIT)

---

**Keywords**: Python ROI viewer, Calcium Imaging Visualization, Biomedical Signal Viewer, Interactive Data Analysis, Open-Source Visualization
