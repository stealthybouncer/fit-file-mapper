#!/usr/bin/env python3
"""
DuckDB Query Tool for FIT File Mapper
Usage: python query_db.py [SQL_QUERY]
"""
import sys
import duckdb
from pathlib import Path

def main():
    db_path = Path("database/workouts_fit-parser.duckdb")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        # Use read-only connection to avoid locks
        conn = duckdb.connect(str(db_path), read_only=True)
        print(f"🦆 Connected to DuckDB: {db_path}")
        print(f"📊 Database size: {db_path.stat().st_size / 1024 / 1024:.1f} MB")
        print("-" * 60)
        
        if len(sys.argv) > 1:
            # Execute provided SQL
            sql = " ".join(sys.argv[1:])
            print(f"🔍 Query: {sql}")
            print("-" * 60)
            results = conn.execute(sql).fetchall()
            for row in results:
                print(row)
        else:
            # Default: Show database overview
            print("📋 TABLES:")
            tables = conn.execute("SHOW TABLES").fetchall()
            for table in tables:
                print(f"  • {table[0]}")
            
            print("\n📊 WORKOUT STATISTICS:")
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_workouts,
                    COUNT(DISTINCT file_name) as unique_files,
                    MIN(timestamp) as earliest_workout,
                    MAX(timestamp) as latest_workout,
                    SUM(total_distance_km) as total_distance_km,
                    SUM(duration_seconds) as total_duration_hours
                FROM workouts
            """).fetchone()
            
            print(f"  • Total workouts: {stats[0]:,}")
            print(f"  • Unique files: {stats[1]:,}")
            print(f"  • Date range: {stats[2]} to {stats[3]}")
            print(f"  • Total distance: {stats[4]:.1f} km")
            print(f"  • Total duration: {stats[5]/3600:.1f} hours")
            
            print("\n🎯 GPS POINTS:")
            gps_stats = conn.execute("SELECT COUNT(*) FROM gps_points").fetchone()
            print(f"  • Total GPS points: {gps_stats[0]:,}")
            
            print("\n💡 SAMPLE QUERIES:")
            print("  python query_db.py \"SELECT * FROM workouts LIMIT 5\"")
            print("  python query_db.py \"SELECT activity_type, COUNT(*) FROM workouts GROUP BY activity_type\"")
            print("  python query_db.py \"SELECT * FROM gps_points WHERE workout_id='your_workout_id' LIMIT 10\"")
    
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("\n🔧 TROUBLESHOOTING:")
        print("  1. Stop all services: docker compose down")
        print("  2. Restart services: docker compose up -d")
        print("  3. Check if database file is corrupted")

if __name__ == "__main__":
    main()