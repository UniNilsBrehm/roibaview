from setuptools import setup, find_packages

setup(
    name="roibaview",
    version="0.2.0",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "PyQt6",
        "pyqtgraph",
        "numpy",
        "pandas",
        "scipy",
        "h5py",
        "tifftools",
        "tifffile",
        "opencv-python",
        "ffmpy",
        "joblib",
        "platformdirs",
        "roifile"
    ],
    entry_points={
        "gui_scripts": [
            "roibaview = roibaview.main:main",
        ],
    },
    python_requires=">=3.7",
    author="Nils",
    author_email="your.email@example.com",
    description="A PyQt6-based application for ROI visualization.",
    url="https://github.com/UniNilsBrehm/roibaview",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)