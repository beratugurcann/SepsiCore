#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export QT_API=pyqt6
# PyQt6 kullanilir; PyQt5/PySide paketleri build'e dahil edilmez.
python3 -m PyInstaller --noconfirm --clean --windowed --name SepsiCore \
    --add-data "assets:assets" \
    --add-data "data:data" \
    --exclude-module qtpy \
    --exclude-module PyQt5 \
    --exclude-module PySide2 \
    --exclude-module PySide6 \
    --exclude-module torch \
    --exclude-module PIL \
    --exclude-module numpy \
    --exclude-module scipy \
    --exclude-module pyarrow \
    --exclude-module fsspec \
    --exclude-module numba \
    --exclude-module llvmlite \
    --exclude-module openpyxl \
    --exclude-module tables \
    --exclude-module sqlalchemy \
    --exclude-module dask \
    --exclude-module distributed \
    --exclude-module xarray \
    --exclude-module bokeh \
    --exclude-module panel \
    --exclude-module plotly \
    --exclude-module skimage \
    --exclude-module sklearn \
    --exclude-module astropy \
    --exclude-module cv2 \
    --exclude-module notebook \
    --exclude-module jupyterlab \
    --exclude-module altair \
    --exclude-module intake \
    --exclude-module statsmodels \
    --exclude-module IPython \
    --exclude-module pytest \
    --exclude-module sphinx \
    main.py
echo "Build tamamlandi: dist/SepsiCore/SepsiCore"
