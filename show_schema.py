#!/usr/bin/env python3
"""
Database Schema Documentation
Shows the complete schema for the FIT File Mapper database
"""

def show_database_schema():
    """Display the complete database schema from the database.py file."""
    
    print("🗄️  FIT FILE MAPPER DATABASE SCHEMA")
    print("=" * 60)
    print()
    
    print("📊 DATABASE: DuckDB (Analytical Database)")
    print("🎯 PURPOSE: High-performance storage and querying of workout data")
    print("🔧 FEATURES: Spatial extensions, columnar storage, ACID transactions")
    print()
    
    tables = {
        "workouts": {
            "description": "Main workout metadata and summary statistics",
            "columns": [
                ("workout_id", "VARCHAR", "PRIMARY KEY", "Unique workout identifier"),
                ("file_name", "VARCHAR", "NOT NULL", "Original FIT file name"),
                ("file_path", "VARCHAR", "", "Full path to FIT file"),
                ("activity_type", "VARCHAR", "", "Type of activity (running, cycling, etc.)"),
                ("start_time", "TIMESTAMP WITH TIME ZONE", "", "Workout start time"),
                ("end_time", "TIMESTAMP WITH TIME ZONE", "", "Workout end time"),
                ("duration_seconds", "INTEGER", "", "Total workout duration"),
                ("total_distance_km", "DOUBLE", "", "Total distance in kilometers"),
                ("total_elevation_gain_m", "DOUBLE", "", "Total elevation gain in meters"),
                ("avg_speed_kmh", "DOUBLE", "", "Average speed in km/h"),
                ("max_speed_kmh", "DOUBLE", "", "Maximum speed in km/h"),
                ("avg_heart_rate", "INTEGER", "", "Average heart rate (BPM)"),
                ("max_heart_rate", "INTEGER", "", "Maximum heart rate (BPM)"),
                ("calories", "INTEGER", "", "Calories burned"),
                ("device_name", "VARCHAR", "", "Recording device name"),
                ("created_at", "TIMESTAMP WITH TIME ZONE", "DEFAULT CURRENT_TIMESTAMP", "Record creation time"),
                ("updated_at", "TIMESTAMP WITH TIME ZONE", "DEFAULT CURRENT_TIMESTAMP", "Record update time"),
                ("metadata", "JSON", "", "Additional workout metadata")
            ]
        },
        
        "gps_points": {
            "description": "Detailed GPS coordinates and sensor data for each workout",
            "columns": [
                ("point_id", "VARCHAR", "PRIMARY KEY", "Unique GPS point identifier"),
                ("workout_id", "VARCHAR", "NOT NULL, FOREIGN KEY", "Reference to workout"),
                ("timestamp", "TIMESTAMP WITH TIME ZONE", "", "GPS point timestamp"),
                ("latitude", "DOUBLE", "", "Latitude coordinate"),
                ("longitude", "DOUBLE", "", "Longitude coordinate"),
                ("elevation_m", "DOUBLE", "", "Elevation in meters"),
                ("speed_kmh", "DOUBLE", "", "Speed at this point (km/h)"),
                ("heart_rate", "INTEGER", "", "Heart rate at this point (BPM)"),
                ("cadence", "INTEGER", "", "Cadence (steps/min or RPM)"),
                ("power_watts", "INTEGER", "", "Power output in watts"),
                ("temperature_c", "DOUBLE", "", "Temperature in Celsius"),
                ("distance_km", "DOUBLE", "", "Cumulative distance"),
                ("point_sequence", "INTEGER", "", "Order of point in workout")
            ]
        },
        
        "map_tiles": {
            "description": "Cached map tiles for offline visualization",
            "columns": [
                ("tile_id", "VARCHAR", "PRIMARY KEY", "Unique tile identifier"),
                ("zoom_level", "INTEGER", "", "Map zoom level"),
                ("tile_x", "INTEGER", "", "Tile X coordinate"),
                ("tile_y", "INTEGER", "", "Tile Y coordinate"),
                ("map_type", "VARCHAR", "", "Map type (satellite, terrain, etc.)"),
                ("tile_data", "BLOB", "", "Binary tile image data"),
                ("download_date", "TIMESTAMP WITH TIME ZONE", "DEFAULT CURRENT_TIMESTAMP", "Tile download time"),
                ("last_accessed", "TIMESTAMP WITH TIME ZONE", "DEFAULT CURRENT_TIMESTAMP", "Last access time"),
                ("file_size_bytes", "INTEGER", "", "Tile file size")
            ]
        },
        
        "workout_segments": {
            "description": "Segments for multi-day or complex workouts",
            "columns": [
                ("segment_id", "VARCHAR", "PRIMARY KEY", "Unique segment identifier"),
                ("workout_id", "VARCHAR", "NOT NULL, FOREIGN KEY", "Reference to workout"),
                ("segment_name", "VARCHAR", "", "Name of the segment"),
                ("start_time", "TIMESTAMP WITH TIME ZONE", "", "Segment start time"),
                ("end_time", "TIMESTAMP WITH TIME ZONE", "", "Segment end time"),
                ("segment_order", "INTEGER", "", "Order of segment in workout"),
                ("distance_km", "DOUBLE", "", "Segment distance"),
                ("elevation_gain_m", "DOUBLE", "", "Segment elevation gain")
            ]
        }
    }
    
    for table_name, table_info in tables.items():
        print(f"📋 {table_name.upper()} TABLE")
        print(f"   {table_info['description']}")
        print("-" * 60)
        
        print(f"{'Column Name':<25} {'Type':<25} {'Constraints':<20} {'Description'}")
        print("-" * 100)
        
        for col_name, col_type, constraints, description in table_info['columns']:
            print(f"{col_name:<25} {col_type:<25} {constraints:<20} {description}")
        
        print()
    
    print("🔍 INDEXES CREATED:")
    print("-" * 30)
    print("• idx_gps_location     ON gps_points (latitude, longitude)   - Spatial queries")
    print("• idx_gps_timestamp    ON gps_points (timestamp)             - Time-based queries")
    print()
    
    print("🔗 RELATIONSHIPS:")
    print("-" * 20)
    print("• gps_points.workout_id        → workouts.workout_id")
    print("• workout_segments.workout_id  → workouts.workout_id")
    print()
    
    print("📈 EXAMPLE QUERIES:")
    print("-" * 20)
    print()
    print("-- Count total workouts")
    print("SELECT COUNT(*) FROM workouts;")
    print()
    print("-- Get workouts with GPS data")
    print("SELECT w.file_name, COUNT(g.point_id) as gps_points")
    print("FROM workouts w")
    print("LEFT JOIN gps_points g ON w.workout_id = g.workout_id")
    print("GROUP BY w.workout_id, w.file_name")
    print("HAVING COUNT(g.point_id) > 0;")
    print()
    print("-- Find workouts in a geographic area")
    print("SELECT DISTINCT w.*")
    print("FROM workouts w")
    print("JOIN gps_points g ON w.workout_id = g.workout_id")
    print("WHERE g.latitude BETWEEN 40.7 AND 40.8")
    print("AND g.longitude BETWEEN -74.0 AND -73.9;")
    print()
    print("-- Get activity summary")
    print("SELECT activity_type, COUNT(*) as count,")
    print("       SUM(total_distance_km) as total_distance")
    print("FROM workouts")
    print("GROUP BY activity_type;")

if __name__ == "__main__":
    show_database_schema()