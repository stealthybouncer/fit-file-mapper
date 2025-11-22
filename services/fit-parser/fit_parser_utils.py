"""
FIT File Parser Utilities

Comprehensive FIT file parsing using fitparse library to extract
GPS coordinates, workout metrics, and metadata for mapping and analysis.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from fitparse import FitFile
from fitparse.records import DataMessage
import pytz
from dateutil import tz

logger = logging.getLogger(__name__)


class FitFileParser:
    """
    Comprehensive FIT file parser for extracting workout data and GPS coordinates.
    
    Supports various activity types including running, hiking, cycling, and water sports.
    Extracts detailed metrics for visualization and analysis.
    """
    
    # Activity type mapping from FIT file sport values
    ACTIVITY_TYPE_MAPPING = {
        0: 'generic',
        1: 'running',
        2: 'cycling',
        3: 'transition',  # multisport transition
        4: 'fitness_equipment',
        5: 'swimming',
        6: 'basketball',
        7: 'soccer',
        8: 'tennis',
        9: 'american_football',
        10: 'training',
        11: 'walking',
        12: 'cross_country_skiing',
        13: 'alpine_skiing',
        14: 'snowboarding',
        15: 'rowing',
        16: 'mountaineering',
        17: 'hiking',
        18: 'multisport',
        19: 'paddling',
        20: 'flying',
        21: 'e_biking',
        22: 'motorcycling',
        23: 'boating',
        24: 'driving',
        25: 'golf',
        26: 'hang_gliding',
        27: 'horseback_riding',
        28: 'hunting',
        29: 'fishing',
        30: 'inline_skating',
        31: 'rock_climbing',
        32: 'sailing',
        33: 'ice_skating',
        34: 'sky_diving',
        35: 'snowshoeing',
        36: 'snowmobiling',
        37: 'stand_up_paddleboarding',
        38: 'surfing',
        39: 'wakeboarding',
        40: 'water_skiing',
        41: 'kayaking',
        42: 'rafting',
        43: 'windsurfing',
        44: 'kitesurfing'
    }
    
    def __init__(self):
        self.fitfile = None
        self.workout_data = {}
        self.gps_points = []
        self.device_info = {}

    def semicircles_to_degrees(self, semicircles: float) -> float:
        return semicircles * (180.0 / 2**31)

    def fit_altitude_to_meters(self, fit_value: float) -> float:
        return fit_value / 5.0 - 500.0

    def meters_per_second_to_kmh(self, mps: float) -> float:
        return mps * 3.6

    def fit_distance_to_km(self, fit_value: float) -> float:
        return fit_value / 100000.0
        
    def parse_fit_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a FIT file and extract all relevant data.
        
        Args:
            file_path: Path to the FIT file
            
        Returns:
            Dictionary containing workout metadata, GPS points, and device info
        """
        try:
            # Load FIT file
            self.fitfile = FitFile(file_path)
            
            # Initialize data containers
            self.workout_data = {}
            self.gps_points = []
            self.device_info = {}
            
            # Parse different message types
            self._parse_file_id()
            self._parse_session_data()
            self._parse_device_info()
            self._parse_gps_records()
            self._parse_lap_data()
            
            # Calculate derived metrics
            self._calculate_derived_metrics()
            
            # Add file information to workout metadata
            self.workout_data['file_path'] = file_path
            self.workout_data['file_name'] = Path(file_path).name
            self.workout_data['parsed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Compile final result
            result = {
                'workout_metadata': self.workout_data,
                'gps_points': self.gps_points,
                'device_info': self.device_info
            }
            
            logger.info(f"Successfully parsed FIT file: {file_path}")
            logger.info(f"Found {len(self.gps_points)} GPS points")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse FIT file {file_path}: {e}")
            raise ValueError(f"Invalid FIT file format: {e}")
    
    def _parse_file_id(self):
        for record in self.fitfile.get_messages('file_id'):
            for field in record:
                if field.name == 'type':
                    self.workout_data['file_type'] = field.value
                elif field.name == 'manufacturer':
                    self.device_info['manufacturer'] = field.value
                elif field.name == 'product':
                    self.device_info['product'] = field.value
                elif field.name == 'serial_number':
                    self.device_info['serial_number'] = field.value
                elif field.name == 'time_created':
                    if field.value:
                        self.workout_data['file_created'] = self._convert_timestamp(field.value)
    
    def _parse_session_data(self):
        for record in self.fitfile.get_messages('session'):
            for field in record:
                field_name = field.name
                field_value = field.value
                
                if field_name == 'sport':
                    self.workout_data['activity_type'] = self.ACTIVITY_TYPE_MAPPING.get(
                        field_value, 'unknown'
                    )
                elif field_name == 'start_time':
                    if field_value:
                        self.workout_data['start_time'] = self._convert_timestamp(field_value)
                elif field_name == 'timestamp':
                    if field_value:
                        self.workout_data['end_time'] = self._convert_timestamp(field_value)
                elif field_name == 'total_elapsed_time':
                    if field_value:
                        self.workout_data['duration_seconds'] = int(field_value)
                elif field_name == 'total_timer_time':
                    if field_value:
                        self.workout_data['moving_time_seconds'] = int(field_value)
                elif field_name == 'total_distance':
                    if field_value:
                        self.workout_data['total_distance_km'] = self.fit_distance_to_km(field_value)
                elif field_name == 'total_ascent':
                    if field_value:
                        self.workout_data['total_elevation_gain_m'] = field_value
                elif field_name == 'total_descent':
                    if field_value:
                        self.workout_data['total_elevation_loss_m'] = field_value
                elif field_name == 'avg_speed':
                    if field_value:
                        self.workout_data['avg_speed_kmh'] = self.meters_per_second_to_kmh(field_value)
                elif field_name == 'max_speed':
                    if field_value:
                        self.workout_data['max_speed_kmh'] = self.meters_per_second_to_kmh(field_value)
                elif field_name == 'avg_heart_rate':
                    if field_value:
                        self.workout_data['avg_heart_rate'] = field_value
                elif field_name == 'max_heart_rate':
                    if field_value:
                        self.workout_data['max_heart_rate'] = field_value
                elif field_name == 'total_calories':
                    if field_value:
                        self.workout_data['calories'] = field_value
                elif field_name == 'avg_cadence':
                    if field_value:
                        self.workout_data['avg_cadence'] = field_value
                elif field_name == 'max_cadence':
                    if field_value:
                        self.workout_data['max_cadence'] = field_value
                elif field_name == 'avg_power':
                    if field_value:
                        self.workout_data['avg_power_watts'] = field_value
                elif field_name == 'max_power':
                    if field_value:
                        self.workout_data['max_power_watts'] = field_value
    
    def _parse_device_info(self):
        for record in self.fitfile.get_messages('device_info'):
            for field in record:
                if field.name == 'device_index' and field.value == 0:  # Primary device
                    continue
                elif field.name == 'manufacturer':
                    self.device_info['manufacturer'] = field.value
                elif field.name == 'product':
                    self.device_info['product'] = field.value
                elif field.name == 'serial_number':
                    self.device_info['serial_number'] = field.value
                elif field.name == 'software_version':
                    self.device_info['software_version'] = field.value
                elif field.name == 'hardware_version':
                    self.device_info['hardware_version'] = field.value
                elif field.name == 'device_type':
                    self.device_info['device_type'] = field.value
    
    def _parse_gps_records(self):
        gps_data = []
        distance = 0.0
        
        for record in self.fitfile.get_messages('record'):
            if not hasattr(record, 'fields'):
                continue
                
            point = {}
            
            # Extract data from record fields
            for field in record:
                field_name = field.name
                field_value = field.value
                
                if field_name == 'timestamp':
                    if field_value:
                        point['timestamp'] = self._convert_timestamp(field_value)
                elif field_name == 'position_lat':
                    if field_value is not None:
                        point['latitude'] = self.semicircles_to_degrees(field_value)
                elif field_name == 'position_long':
                    if field_value is not None:
                        point['longitude'] = self.semicircles_to_degrees(field_value)
                elif field_name == 'altitude':
                    if field_value is not None:
                        point['elevation_m'] = self.fit_altitude_to_meters(field_value)
                elif field_name == 'enhanced_altitude':
                    if field_value is not None:
                        point['elevation_m'] = self.fit_altitude_to_meters(field_value)
                elif field_name == 'speed':
                    if field_value is not None:
                        point['speed_kmh'] = self.meters_per_second_to_kmh(field_value)
                elif field_name == 'enhanced_speed':
                    if field_value is not None:
                        point['speed_kmh'] = self.meters_per_second_to_kmh(field_value)
                elif field_name == 'heart_rate':
                    if field_value is not None:
                        point['heart_rate'] = field_value
                elif field_name == 'cadence':
                    if field_value is not None:
                        point['cadence'] = field_value
                elif field_name == 'power':
                    if field_value is not None:
                        point['power_watts'] = field_value
                elif field_name == 'temperature':
                    if field_value is not None:
                        point['temperature_c'] = field_value
                elif field_name == 'distance':
                    if field_value is not None:
                        distance = self.fit_distance_to_km(field_value)
                        point['distance_km'] = distance
            
            # Only add points with valid GPS coordinates
            if 'latitude' in point and 'longitude' in point:
                # Validate GPS coordinates
                if self._is_valid_gps_coordinate(point['latitude'], point['longitude']):
                    gps_data.append(point)
        
        self.gps_points = gps_data
        logger.info(f"Extracted {len(self.gps_points)} valid GPS points")
    
    def _parse_lap_data(self):
        laps = []
        
        for record in self.fitfile.get_messages('lap'):
            lap = {}
            
            for field in record:
                if field.name == 'start_time':
                    if field.value:
                        lap['start_time'] = self._convert_timestamp(field.value)
                elif field.name == 'timestamp':
                    if field.value:
                        lap['end_time'] = self._convert_timestamp(field.value)
                elif field.name == 'total_elapsed_time':
                    if field.value:
                        lap['duration_seconds'] = int(field.value)
                elif field.name == 'total_distance':
                    if field.value:
                        lap['distance_km'] = self.fit_distance_to_km(field.value)
                elif field.name == 'avg_speed':
                    if field.value:
                        lap['avg_speed_kmh'] = self.meters_per_second_to_kmh(field.value)
                elif field.name == 'avg_heart_rate':
                    if field.value:
                        lap['avg_heart_rate'] = field.value
            
            if lap:
                laps.append(lap)
        
        if laps:
            self.workout_data['laps'] = laps
    
    def _calculate_derived_metrics(self):
        if not self.gps_points:
            return
        
        # Calculate workout bounds
        latitudes = [p['latitude'] for p in self.gps_points if 'latitude' in p]
        longitudes = [p['longitude'] for p in self.gps_points if 'longitude' in p]
        
        if latitudes and longitudes:
            self.workout_data['bounds'] = {
                'min_lat': min(latitudes),
                'max_lat': max(latitudes),
                'min_lon': min(longitudes),
                'max_lon': max(longitudes),
                'center_lat': sum(latitudes) / len(latitudes),
                'center_lon': sum(longitudes) / len(longitudes)
            }
        
        # Calculate elevation profile
        elevations = [p['elevation_m'] for p in self.gps_points 
                     if 'elevation_m' in p and p['elevation_m'] is not None]
        
        if elevations:
            self.workout_data['elevation_profile'] = {
                'min_elevation_m': min(elevations),
                'max_elevation_m': max(elevations),
                'elevation_range_m': max(elevations) - min(elevations)
            }
        
        # Calculate workout statistics
        speeds = [p['speed_kmh'] for p in self.gps_points 
                 if 'speed_kmh' in p and p['speed_kmh'] is not None and p['speed_kmh'] > 0]
        
        if speeds:
            self.workout_data['speed_stats'] = {
                'avg_moving_speed_kmh': sum(speeds) / len(speeds),
                'speed_75th_percentile_kmh': np.percentile(speeds, 75),
                'speed_95th_percentile_kmh': np.percentile(speeds, 95)
            }
    
    def _convert_timestamp(self, fit_timestamp) -> str:
        try:
            # FIT timestamps are seconds since UTC 00:00 Dec 31 1989
            fit_epoch = datetime(1989, 12, 31, tzinfo=timezone.utc)
            dt = fit_epoch + pd.Timedelta(seconds=fit_timestamp)
            return dt.isoformat()
        except Exception as e:
            logger.warning(f"Failed to convert timestamp {fit_timestamp}: {e}")
            return datetime.now(timezone.utc).isoformat()
    
    def _is_valid_gps_coordinate(self, lat: float, lon: float) -> bool:
        return (
            -90 <= lat <= 90 and
            -180 <= lon <= 180 and
            not (lat == 0 and lon == 0)
        )
    
    def get_workout_summary(self) -> Dict[str, Any]:
        """Get a summary of the parsed workout data."""
        if not self.workout_data:
            return {}
        
        summary = {
            'activity_type': self.workout_data.get('activity_type', 'unknown'),
            'duration_minutes': round(self.workout_data.get('duration_seconds', 0) / 60, 1),
            'distance_km': round(self.workout_data.get('total_distance_km', 0), 2),
            'gps_points_count': len(self.gps_points),
            'has_heart_rate': any('heart_rate' in p for p in self.gps_points),
            'has_elevation': any('elevation_m' in p for p in self.gps_points),
            'has_power': any('power_watts' in p for p in self.gps_points),
            'device': f"{self.device_info.get('manufacturer', 'Unknown')} {self.device_info.get('product', '')}"
        }
        
        if 'bounds' in self.workout_data:
            bounds = self.workout_data['bounds']
            summary['geographic_center'] = {
                'latitude': round(bounds['center_lat'], 6),
                'longitude': round(bounds['center_lon'], 6)
            }
        
        return summary


def parse_fit_file_data(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to parse a FIT file and return structured data.
    
    Args:
        file_path: Path to the FIT file
        
    Returns:
        Parsed workout data including metadata and GPS points
    """
    parser = FitFileParser()
    return parser.parse_fit_file(file_path)