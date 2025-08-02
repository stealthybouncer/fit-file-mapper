"""
FIT Parser Service

Microservice for parsing FIT files and storing data in DuckDB.
Handles multiple activity types with data validation and processing.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

# Add shared modules to path
sys.path.append('/workspace/shared')
sys.path.append('../shared')

import pandas as pd
import fitparse
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from shared.database import get_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FIT Parser Service", version="1.0.0")


class FITParserService:
    """
    Service for parsing FIT files and extracting workout data.
    """
    
    def __init__(self):
        self.db = get_database()
        self.supported_activity_types = [
            'running', 'hiking', 'cycling', 'kayaking', 
            'swimming', 'walking', 'generic'
        ]
    
    def parse_fit_file(self, file_path: Path) -> Dict:
        """
        Parse a FIT file and extract workout data.
        
        Args:
            file_path: Path to the FIT file
            
        Returns:
            Dictionary with parsed workout data
        """
        try:
            # Parse FIT file
            fitfile = fitparse.FitFile(str(file_path))
            
            # Extract workout metadata
            workout_metadata = self._extract_workout_metadata(fitfile)
            
            # Extract GPS points
            gps_data = self._extract_gps_data(fitfile)
            
            # Calculate derived metrics
            workout_metadata.update(self._calculate_workout_metrics(gps_data))
            
            # Add file information
            workout_metadata.update({
                'file_name': file_path.name,
                'file_path': str(file_path),
                'file_size_bytes': file_path.stat().st_size,
                'parsed_at': datetime.now(timezone.utc)
            })
            
            return {
                'metadata': workout_metadata,
                'gps_data': gps_data
            }
            
        except Exception as e:
            logger.error(f"Error parsing FIT file {file_path}: {e}")
            raise
    
    def _extract_workout_metadata(self, fitfile) -> Dict:
        """Extract basic workout metadata from FIT file."""
        metadata = {
            'activity_type': 'generic',
            'device_name': None,
            'start_time': None,
            'end_time': None,
            'total_timer_time': None,
            'sport': None
        }
        
        # Extract session information
        for record in fitfile.get_messages('session'):
            data = record.get_values()
            
            # Activity type detection
            if 'sport' in data:
                sport = str(data['sport']).lower()
                metadata['sport'] = sport
                metadata['activity_type'] = self._map_sport_to_activity_type(sport)
            
            # Timing information
            if 'start_time' in data:
                metadata['start_time'] = data['start_time']
            if 'timestamp' in data:
                metadata['end_time'] = data['timestamp']
            if 'total_timer_time' in data:
                metadata['total_timer_time'] = data['total_timer_time']
        
        # Extract device information
        for record in fitfile.get_messages('device_info'):
            data = record.get_values()
            if 'device_type' in data and data.get('device_type') != 'unknown':
                metadata['device_name'] = str(data.get('manufacturer', 'Unknown'))
                break
        
        return metadata
    
    def _extract_gps_data(self, fitfile) -> pd.DataFrame:
        """Extract GPS coordinates and metrics from FIT file."""
        gps_records = []
        
        for record in fitfile.get_messages('record'):
            data = record.get_values()
            
            # Skip records without GPS coordinates
            if 'position_lat' not in data or 'position_long' not in data:
                continue
            
            if data['position_lat'] is None or data['position_long'] is None:
                continue
            
            # Convert semicircles to degrees
            lat = data['position_lat'] * (180.0 / 2**31)
            lon = data['position_long'] * (180.0 / 2**31)
            
            # Extract record data
            gps_record = {
                'timestamp': data.get('timestamp'),
                'latitude': lat,
                'longitude': lon,
                'elevation': data.get('enhanced_altitude') or data.get('altitude'),
                'speed': self._convert_speed(data.get('enhanced_speed') or data.get('speed')),
                'heart_rate': data.get('heart_rate'),
                'cadence': data.get('cadence'),
                'power': data.get('power'),
                'temperature': data.get('temperature'),
                'distance': self._convert_distance(data.get('distance'))
            }
            
            gps_records.append(gps_record)
        
        df = pd.DataFrame(gps_records)
        
        # Data cleaning and validation
        if not df.empty:
            df = self._clean_gps_data(df)
        
        return df
    
    def _clean_gps_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate GPS data."""
        # Remove invalid coordinates
        df = df.dropna(subset=['latitude', 'longitude'])
        
        # Filter reasonable coordinate ranges
        df = df[
            (df['latitude'].between(-90, 90)) &
            (df['longitude'].between(-180, 180))
        ]
        
        # Remove duplicate timestamps
        df = df.drop_duplicates(subset=['timestamp'])
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    
    def _calculate_workout_metrics(self, gps_data: pd.DataFrame) -> Dict:
        """Calculate derived workout metrics."""
        if gps_data.empty:
            return {}
        
        # Basic timing
        start_time = gps_data['timestamp'].min()
        end_time = gps_data['timestamp'].max()
        duration_seconds = (end_time - start_time).total_seconds() if start_time and end_time else 0
        
        # Distance and speed
        total_distance_km = gps_data['distance'].max() if 'distance' in gps_data.columns else 0
        avg_speed_kmh = gps_data['speed'].mean() if 'speed' in gps_data.columns else 0
        max_speed_kmh = gps_data['speed'].max() if 'speed' in gps_data.columns else 0
        
        # Elevation
        elevation_gain_m = 0
        if 'elevation' in gps_data.columns and not gps_data['elevation'].isna().all():
            elevation_diff = gps_data['elevation'].diff()
            elevation_gain_m = elevation_diff[elevation_diff > 0].sum()
        
        # Heart rate
        avg_heart_rate = gps_data['heart_rate'].mean() if 'heart_rate' in gps_data.columns else None
        max_heart_rate = gps_data['heart_rate'].max() if 'heart_rate' in gps_data.columns else None
        
        return {
            'start_time': start_time,
            'end_time': end_time,
            'duration_seconds': int(duration_seconds),
            'total_distance_km': round(total_distance_km, 3) if total_distance_km else 0,
            'total_elevation_gain_m': round(elevation_gain_m, 1) if elevation_gain_m else 0,
            'avg_speed_kmh': round(avg_speed_kmh, 2) if avg_speed_kmh else 0,
            'max_speed_kmh': round(max_speed_kmh, 2) if max_speed_kmh else 0,
            'avg_heart_rate': int(avg_heart_rate) if avg_heart_rate and not pd.isna(avg_heart_rate) else None,
            'max_heart_rate': int(max_heart_rate) if max_heart_rate and not pd.isna(max_heart_rate) else None,
            'point_count': len(gps_data)
        }
    
    def _map_sport_to_activity_type(self, sport: str) -> str:
        """Map FIT file sport to activity type."""
        sport_mapping = {
            'running': 'running',
            'cycling': 'cycling',
            'walking': 'hiking',
            'hiking': 'hiking',
            'mountaineering': 'hiking',
            'kayaking': 'kayaking',
            'canoeing': 'kayaking',
            'rowing': 'kayaking',
            'swimming': 'swimming',
            'open_water_swimming': 'swimming'
        }
        
        return sport_mapping.get(sport.lower(), 'generic')
    
    def _convert_speed(self, speed_ms: Optional[float]) -> Optional[float]:
        """Convert speed from m/s to km/h."""
        if speed_ms is None:
            return None
        return speed_ms * 3.6
    
    def _convert_distance(self, distance_m: Optional[float]) -> Optional[float]:
        """Convert distance from meters to kilometers."""
        if distance_m is None:
            return None
        return distance_m / 1000.0
    
    def store_workout(self, parsed_data: Dict) -> str:
        """Store parsed workout data in database."""
        try:
            # Store workout metadata
            workout_id = self.db.insert_workout(parsed_data['metadata'])
            
            # Store GPS points
            if not parsed_data['gps_data'].empty:
                self.db.insert_gps_points(workout_id, parsed_data['gps_data'])
            
            logger.info(f"Stored workout {workout_id} with {len(parsed_data['gps_data'])} GPS points")
            return workout_id
            
        except Exception as e:
            logger.error(f"Error storing workout data: {e}")
            raise


# Initialize service
fit_parser_service = FITParserService()


@app.post("/parse-file")
async def parse_file(file: UploadFile = File(...)):
    """Parse uploaded FIT file and store in database."""
    try:
        # Save uploaded file temporarily
        temp_file = Path(f"/tmp/{file.filename}")
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Parse FIT file
        parsed_data = fit_parser_service.parse_fit_file(temp_file)
        
        # Store in database
        workout_id = fit_parser_service.store_workout(parsed_data)
        
        # Clean up temp file
        temp_file.unlink()
        
        return {
            "status": "success",
            "workout_id": workout_id,
            "message": f"Successfully parsed and stored {file.filename}",
            "metadata": parsed_data['metadata'],
            "gps_point_count": len(parsed_data['gps_data'])
        }
        
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workout/{workout_id}")
async def get_workout(workout_id: str):
    """Get workout metadata by ID."""
    try:
        workout = fit_parser_service.db.get_workout_by_id(workout_id)
        if not workout:
            raise HTTPException(status_code=404, detail="Workout not found")
        
        return workout
    except Exception as e:
        logger.error(f"Error retrieving workout {workout_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workout/{workout_id}/gps")
async def get_workout_gps(workout_id: str):
    """Get GPS data for a workout."""
    try:
        gps_data = fit_parser_service.db.get_workout_gps_data(workout_id)
        
        return {
            "workout_id": workout_id,
            "point_count": len(gps_data),
            "gps_data": gps_data.to_dict('records')
        }
    except Exception as e:
        logger.error(f"Error retrieving GPS data for {workout_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "fit-parser"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
