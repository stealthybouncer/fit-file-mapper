"""
Configuration settings for FIT File Mapper application.

This module contains all configurable parameters for the application,
including map settings, data processing parameters, and API configurations.
"""

import os
from pathlib import Path

# Base project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FIT_FILES_DIR = DATA_DIR / "fit_files"
MAPS_DIR = DATA_DIR / "maps"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Ensure directories exist
for directory in [DATA_DIR, FIT_FILES_DIR, MAPS_DIR, OUTPUT_DIR]:
    directory.mkdir(exist_ok=True)

# USGS Map Settings - Optimized for satellite imagery and offline use
USGS_CONFIG = {
    "satellite_url": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile",
    "topo_url": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile",
    "hybrid_url": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer/tile",
    "tile_size": 256,
    "max_zoom": 18,  # Higher resolution for precise mapping
    "min_zoom": 1,
    "cache_enabled": True,
    "cache_ttl_days": 90,  # Longer cache for offline use
    "max_concurrent_downloads": 8,  # Faster downloads
    "request_timeout": 45,
    "offline_mode": False,  # Can be toggled for field use
    "preload_areas": [  # NYC and common park areas
        {"name": "NYC_Metro", "bounds": [40.4774, -74.2591, 40.9176, -73.7004]},
        {"name": "Catskills", "bounds": [41.8, -74.8, 42.3, -73.8]},
        {"name": "Adirondacks", "bounds": [43.0, -75.5, 44.5, -73.5]},
    ]
}

# Map visualization settings - Optimized for multiple overlays and stitching
VISUALIZATION_CONFIG = {
    "default_map_type": "satellite",  # Primary focus on satellite
    "available_map_types": ["satellite", "topo", "hybrid"],
    "default_output_format": "png",
    "high_res_dpi": 300,
    "web_dpi": 150,
    "route_colors": ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF"],
    "route_width": 4,  # Slightly thicker for visibility
    "route_opacity": 0.85,
    "marker_size": 10,
    "start_marker_color": "green",
    "end_marker_color": "red",
    "waypoint_marker_color": "blue",
    "multi_workout_colors": True,
    "auto_stitching": True,
    "stitch_overlap": 0.1,  # 10% overlap for seamless stitching
}

# GPS data processing settings
GPS_CONFIG = {
    "coordinate_system": "WGS84",
    "smoothing_window": 5,
    "min_accuracy_threshold": 10.0,  # meters
    "speed_calculation_method": "haversine",
    "elevation_smoothing": True,
    "remove_outliers": True,
    "outlier_threshold": 3.0,  # standard deviations
}

# FIT file parsing settings - Optimized for multiple activity types
FIT_CONFIG = {
    "required_fields": ["timestamp", "position_lat", "position_long"],
    "optional_fields": ["altitude", "speed", "heart_rate", "cadence", "power", "temperature"],
    "activity_types": ["running", "hiking", "cycling", "kayaking", "swimming"],
    "timezone": "US/Eastern",  # NYC area default
    "skip_invalid_records": True,
    "interpolate_missing_data": True,
    "multi_day_support": True,
    "workout_stitching": {
        "enabled": True,
        "max_gap_minutes": 120,  # Allow 2-hour gaps for rest stops
        "auto_detect_segments": True,
        "preserve_individual_tracks": True,
    }
}

# Performance and caching settings
PERFORMANCE_CONFIG = {
    "max_memory_usage_mb": 1024,
    "enable_multiprocessing": True,
    "max_workers": 4,
    "chunk_size": 1000,
    "enable_progress_bars": True,
}

# Logging configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_enabled": True,
    "log_file": PROJECT_ROOT / "logs" / "fit_mapper.log",
}

# API rate limiting
RATE_LIMITING = {
    "usgs_requests_per_second": 2,
    "max_retries": 3,
    "backoff_factor": 1.0,
}

# Environment-specific overrides
if os.getenv("ENVIRONMENT") == "development":
    LOGGING_CONFIG["level"] = "DEBUG"
    PERFORMANCE_CONFIG["enable_progress_bars"] = True
elif os.getenv("ENVIRONMENT") == "production":
    LOGGING_CONFIG["level"] = "WARNING"
    PERFORMANCE_CONFIG["enable_progress_bars"] = False
