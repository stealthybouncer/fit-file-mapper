"""
FIT File Mapper - A Python application for mapping FIT file GPS data on USGS maps.

This package provides functionality for:
- Parsing FIT files from GPS devices
- Processing GPS and workout data
- Downloading and stitching USGS map tiles
- Creating visualizations overlaying workout routes on maps
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .fit_parser import FITParser
from .gps_processor import GPSProcessor
from .map_downloader import USGSMapDownloader
from .map_stitcher import MapStitcher
from .visualizer import MapVisualizer

__all__ = [
    "FITParser",
    "GPSProcessor", 
    "USGSMapDownloader",
    "MapStitcher",
    "MapVisualizer"
]
