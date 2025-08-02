"""
Shared Database Module using DuckDB

Provides centralized database operations for all FIT File Mapper services.
Uses DuckDB for high-performance analytical queries on workout data.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import duckdb
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)


class WorkoutDatabase:
    """
    DuckDB-based database for storing and querying workout data.
    
    Features:
    - High-performance columnar storage
    - Efficient spatial and temporal queries
    - Support for complex analytical operations
    - ACID transactions
    - Embedded database (no separate server needed)
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize DuckDB connection and create tables."""
        self.db_path = db_path or os.getenv('DUCKDB_PATH', 'database/workouts.duckdb')
        
        # Ensure database directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to DuckDB
        self.conn = duckdb.connect(self.db_path)
        
        # Install and load spatial extension for geographic operations
        self._setup_extensions()
        
        # Create database schema
        self._create_tables()
        
    def _setup_extensions(self):
        """Install and load required DuckDB extensions."""
        try:
            # Install spatial extension for geographic functions
            self.conn.execute("INSTALL spatial;")
            self.conn.execute("LOAD spatial;")
            
            # Install httpfs for potential remote data access
            self.conn.execute("INSTALL httpfs;")
            self.conn.execute("LOAD httpfs;")
            
            logger.info("DuckDB extensions loaded successfully")
        except Exception as e:
            logger.warning(f"Some extensions may not be available: {e}")
    
    def _create_tables(self):
        """Create database tables for workout data."""
        
        # Workouts table - main workout metadata
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                workout_id VARCHAR PRIMARY KEY,
                file_name VARCHAR NOT NULL,
                file_path VARCHAR,
                activity_type VARCHAR,
                start_time TIMESTAMP WITH TIME ZONE,
                end_time TIMESTAMP WITH TIME ZONE,
                duration_seconds INTEGER,
                total_distance_km DOUBLE,
                total_elevation_gain_m DOUBLE,
                avg_speed_kmh DOUBLE,
                max_speed_kmh DOUBLE,
                avg_heart_rate INTEGER,
                max_heart_rate INTEGER,
                calories INTEGER,
                device_name VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                metadata JSON
            );
        """)
        
        # GPS Points table - detailed coordinate data
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS gps_points (
                point_id VARCHAR PRIMARY KEY,
                workout_id VARCHAR NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE,
                latitude DOUBLE,
                longitude DOUBLE,
                elevation_m DOUBLE,
                speed_kmh DOUBLE,
                heart_rate INTEGER,
                cadence INTEGER,
                power_watts INTEGER,
                temperature_c DOUBLE,
                distance_km DOUBLE,
                point_sequence INTEGER,
                FOREIGN KEY (workout_id) REFERENCES workouts(workout_id)
            );
        """)
        
        # Create spatial index for efficient geographic queries
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_gps_location 
            ON gps_points (latitude, longitude);
        """)
        
        # Create temporal index for time-based queries
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_gps_timestamp 
            ON gps_points (timestamp);
        """)
        
        # Map tiles cache table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS map_tiles (
                tile_id VARCHAR PRIMARY KEY,
                zoom_level INTEGER,
                tile_x INTEGER,
                tile_y INTEGER,
                map_type VARCHAR,
                tile_data BLOB,
                download_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                file_size_bytes INTEGER
            );
        """)
        
        # Workout segments for multi-day activities
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS workout_segments (
                segment_id VARCHAR PRIMARY KEY,
                workout_id VARCHAR NOT NULL,
                segment_name VARCHAR,
                start_time TIMESTAMP WITH TIME ZONE,
                end_time TIMESTAMP WITH TIME ZONE,
                segment_order INTEGER,
                distance_km DOUBLE,
                elevation_gain_m DOUBLE,
                FOREIGN KEY (workout_id) REFERENCES workouts(workout_id)
            );
        """)
        
        logger.info("Database tables created successfully")
    
    def insert_workout(self, workout_data: Dict) -> str:
        """
        Insert a new workout record.
        
        Args:
            workout_data: Dictionary containing workout metadata
            
        Returns:
            workout_id of the inserted record
        """
        workout_id = f"workout_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{workout_data.get('file_name', 'unknown').replace('.', '_')}"
        
        # Prepare insert data
        insert_data = {
            'workout_id': workout_id,
            'file_name': workout_data.get('file_name'),
            'file_path': workout_data.get('file_path'),
            'activity_type': workout_data.get('activity_type'),
            'start_time': workout_data.get('start_time'),
            'end_time': workout_data.get('end_time'),
            'duration_seconds': workout_data.get('duration_seconds'),
            'total_distance_km': workout_data.get('total_distance_km'),
            'total_elevation_gain_m': workout_data.get('total_elevation_gain_m'),
            'avg_speed_kmh': workout_data.get('avg_speed_kmh'),
            'max_speed_kmh': workout_data.get('max_speed_kmh'),
            'avg_heart_rate': workout_data.get('avg_heart_rate'),
            'max_heart_rate': workout_data.get('max_heart_rate'),
            'calories': workout_data.get('calories'),
            'device_name': workout_data.get('device_name'),
            'metadata': json.dumps(workout_data.get('metadata', {}))
        }
        
        # Insert workout
        placeholders = ', '.join(['?' for _ in insert_data])
        columns = ', '.join(insert_data.keys())
        
        self.conn.execute(
            f"INSERT INTO workouts ({columns}) VALUES ({placeholders})",
            list(insert_data.values())
        )
        
        logger.info(f"Inserted workout: {workout_id}")
        return workout_id
    
    def insert_gps_points(self, workout_id: str, gps_data: pd.DataFrame):
        """
        Insert GPS points for a workout.
        
        Args:
            workout_id: ID of the parent workout
            gps_data: DataFrame with GPS coordinates and metrics
        """
        # Prepare GPS points data
        gps_points = []
        for idx, row in gps_data.iterrows():
            point_id = f"{workout_id}_point_{idx:06d}"
            gps_points.append({
                'point_id': point_id,
                'workout_id': workout_id,
                'timestamp': row.get('timestamp'),
                'latitude': row.get('latitude'),
                'longitude': row.get('longitude'),
                'elevation_m': row.get('elevation'),
                'speed_kmh': row.get('speed'),
                'heart_rate': row.get('heart_rate'),
                'cadence': row.get('cadence'),
                'power_watts': row.get('power'),
                'temperature_c': row.get('temperature'),
                'distance_km': row.get('distance'),
                'point_sequence': idx
            })
        
        # Batch insert GPS points
        if gps_points:
            df = pd.DataFrame(gps_points)
            self.conn.execute("INSERT INTO gps_points SELECT * FROM df")
            logger.info(f"Inserted {len(gps_points)} GPS points for workout {workout_id}")
    
    def get_workout_by_id(self, workout_id: str) -> Optional[Dict]:
        """Get workout metadata by ID."""
        result = self.conn.execute(
            "SELECT * FROM workouts WHERE workout_id = ?", [workout_id]
        ).fetchone()
        
        if result:
            columns = [desc[0] for desc in self.conn.description]
            return dict(zip(columns, result))
        return None
    
    def get_workout_gps_data(self, workout_id: str) -> pd.DataFrame:
        """Get GPS points for a specific workout."""
        return self.conn.execute("""
            SELECT * FROM gps_points 
            WHERE workout_id = ? 
            ORDER BY point_sequence
        """, [workout_id]).df()
    
    def query_workouts_by_area(self, lat_min: float, lon_min: float, 
                             lat_max: float, lon_max: float) -> pd.DataFrame:
        """
        Query workouts that intersect with a geographic area.
        
        Args:
            lat_min, lon_min, lat_max, lon_max: Bounding box coordinates
            
        Returns:
            DataFrame with workouts in the area
        """
        return self.conn.execute("""
            SELECT DISTINCT w.*
            FROM workouts w
            JOIN gps_points g ON w.workout_id = g.workout_id
            WHERE g.latitude BETWEEN ? AND ?
            AND g.longitude BETWEEN ? AND ?
        """, [lat_min, lat_max, lon_min, lon_max]).df()
    
    def query_workouts_by_date_range(self, start_date: datetime, 
                                   end_date: datetime) -> pd.DataFrame:
        """Query workouts within a date range."""
        return self.conn.execute("""
            SELECT * FROM workouts 
            WHERE start_time BETWEEN ? AND ?
            ORDER BY start_time DESC
        """, [start_date, end_date]).df()
    
    def get_activity_summary(self) -> pd.DataFrame:
        """Get summary statistics by activity type."""
        return self.conn.execute("""
            SELECT 
                activity_type,
                COUNT(*) as workout_count,
                SUM(total_distance_km) as total_distance_km,
                AVG(total_distance_km) as avg_distance_km,
                SUM(duration_seconds) as total_duration_seconds,
                AVG(avg_speed_kmh) as avg_speed_kmh,
                MAX(max_speed_kmh) as max_speed_kmh
            FROM workouts 
            WHERE activity_type IS NOT NULL
            GROUP BY activity_type
            ORDER BY workout_count DESC
        """).df()
    
    def get_heat_map_data(self, lat_min: float, lon_min: float, 
                         lat_max: float, lon_max: float,
                         grid_size: int = 100) -> pd.DataFrame:
        """
        Generate heat map data for a geographic area.
        
        Args:
            lat_min, lon_min, lat_max, lon_max: Bounding box
            grid_size: Number of grid cells per dimension
            
        Returns:
            DataFrame with grid coordinates and activity counts
        """
        lat_step = (lat_max - lat_min) / grid_size
        lon_step = (lon_max - lon_min) / grid_size
        
        return self.conn.execute("""
            SELECT 
                FLOOR((latitude - ?) / ?) * ? + ? as grid_lat,
                FLOOR((longitude - ?) / ?) * ? + ? as grid_lon,
                COUNT(*) as point_count
            FROM gps_points
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
            GROUP BY grid_lat, grid_lon
            HAVING point_count > 0
            ORDER BY point_count DESC
        """, [
            lat_min, lat_step, lat_step, lat_min,
            lon_min, lon_step, lon_step, lon_min,
            lat_min, lat_max, lon_min, lon_max
        ]).df()
    
    def cache_map_tile(self, zoom: int, x: int, y: int, 
                      map_type: str, tile_data: bytes):
        """Cache a map tile in the database."""
        tile_id = f"{map_type}_{zoom}_{x}_{y}"
        
        self.conn.execute("""
            INSERT OR REPLACE INTO map_tiles 
            (tile_id, zoom_level, tile_x, tile_y, map_type, tile_data, file_size_bytes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [tile_id, zoom, x, y, map_type, tile_data, len(tile_data)])
    
    def get_cached_tile(self, zoom: int, x: int, y: int, map_type: str) -> Optional[bytes]:
        """Retrieve a cached map tile."""
        tile_id = f"{map_type}_{zoom}_{x}_{y}"
        
        result = self.conn.execute("""
            SELECT tile_data FROM map_tiles 
            WHERE tile_id = ?
        """, [tile_id]).fetchone()
        
        if result:
            # Update last accessed time
            self.conn.execute("""
                UPDATE map_tiles 
                SET last_accessed = CURRENT_TIMESTAMP 
                WHERE tile_id = ?
            """, [tile_id])
            return result[0]
        
        return None
    
    def cleanup_old_tiles(self, days_old: int = 90):
        """Remove old cached map tiles."""
        self.conn.execute("""
            DELETE FROM map_tiles 
            WHERE last_accessed < CURRENT_TIMESTAMP - INTERVAL ? DAY
        """, [days_old])
        
        deleted_count = self.conn.execute("SELECT changes()").fetchone()[0]
        logger.info(f"Cleaned up {deleted_count} old map tiles")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Global database instance
_db_instance = None

def get_database() -> WorkoutDatabase:
    """Get shared database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = WorkoutDatabase()
    return _db_instance
