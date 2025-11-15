#!/usr/bin/env python3
"""
Dynamic Database Schema Explorer (using curl)
Connects to the live FIT File Mapper database and shows actual schema and data
"""

import subprocess
import json
import sys
from typing import Dict, List, Any, Optional

def query_database(sql: str) -> Optional[Dict[str, Any]]:
    """Execute SQL query via curl to the API endpoint."""
    try:
        cmd = [
            "curl", "-s", "-X", "POST", 
            "http://localhost:8001/query",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"sql": sql})
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"❌ curl command failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ Query timed out")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON response: {e}")
        print(f"Response: {result.stdout}")
        return None
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        return None

def check_service_health() -> bool:
    """Check if the database service is responding."""
    try:
        cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8001/health"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return result.stdout == "200"
    except:
        return False

def show_live_schema():
    """Show the actual database schema by querying the live database."""
    
    print("🗄️  LIVE DATABASE SCHEMA EXPLORER")
    print("=" * 60)
    print("📡 Connecting to: http://localhost:8001")
    print()
    
    # Check if service is available
    if check_service_health():
        print("✅ Database service is online")
    else:
        print("❌ Cannot connect to database service")
        print("   Make sure the service is running:")
        print("   docker-compose -f .devcontainer/docker-compose.yml up -d")
        return
    
    print()
    
    # Get all tables
    print("📊 DISCOVERING TABLES...")
    tables_result = query_database("SHOW TABLES")
    
    if not tables_result or tables_result.get('status') != 'success':
        print("❌ Failed to retrieve tables")
        if tables_result:
            print(f"   Error: {tables_result.get('detail', 'Unknown error')}")
        return
    
    tables = [row[0] for row in tables_result['data']]
    print(f"   Found {len(tables)} tables: {', '.join(tables)}")
    print()
    
    # Analyze each table
    total_rows = 0
    table_info = {}
    
    for table_name in tables:
        print(f"📋 TABLE: {table_name.upper()}")
        print("-" * 50)
        
        # Get table schema
        schema_result = query_database(f"DESCRIBE {table_name}")
        if schema_result and schema_result.get('status') == 'success':
            print("   COLUMNS:")
            for row in schema_result['data']:
                col_name, col_type = row[0], row[1]
                print(f"     {col_name:<25} {col_type}")
        
        # Get row count
        count_result = query_database(f"SELECT COUNT(*) FROM {table_name}")
        row_count = 0
        if count_result and count_result.get('status') == 'success':
            row_count = count_result['data'][0][0]
            total_rows += row_count
            table_info[table_name] = row_count
            print(f"   ROWS: {row_count:,}")
        
        # Show sample data if table has data
        if row_count > 0:
            sample_result = query_database(f"SELECT * FROM {table_name} LIMIT 2")
            if sample_result and sample_result.get('status') == 'success':
                print("   SAMPLE DATA:")
                columns = sample_result['columns']
                for i, row in enumerate(sample_result['data']):
                    print(f"     Row {i+1}:")
                    for col, val in zip(columns, row):
                        # Truncate long values
                        val_str = str(val) if val is not None else "NULL"
                        if len(val_str) > 50:
                            val_str = val_str[:47] + "..."
                        print(f"       {col}: {val_str}")
        else:
            print("   (No data in this table)")
        
        print()
    
    # Database summary
    print("📈 DATABASE SUMMARY")
    print("-" * 30)
    
    for table_name, count in table_info.items():
        print(f"   {table_name:<20} {count:>10,} rows")
    
    print(f"   {'TOTAL':<20} {total_rows:>10,} rows")
    print()
    
    # Show specific insights based on actual data
    if table_info.get('workouts', 0) > 0:
        print("🏃‍♂️ WORKOUT DATA INSIGHTS:")
        print("-" * 30)
        
        # Activity breakdown
        activity_result = query_database("""
            SELECT activity_type, COUNT(*) as count 
            FROM workouts 
            GROUP BY activity_type 
            ORDER BY count DESC
        """)
        
        if activity_result and activity_result.get('status') == 'success':
            print("   Activity Types:")
            for row in activity_result['data']:
                activity, count = row[0] or 'unknown', row[1]
                print(f"     {activity:<15} {count:>5,} workouts")
        
        print()
    
    if table_info.get('gps_points', 0) > 0:
        print("�️  GPS DATA INSIGHTS:")
        print("-" * 25)
        
        # GPS density
        gps_result = query_database("""
            SELECT workout_id, COUNT(*) as gps_points 
            FROM gps_points 
            GROUP BY workout_id 
            ORDER BY gps_points DESC 
            LIMIT 5
        """)
        
        if gps_result and gps_result.get('status') == 'success':
            print("   Top workouts by GPS points:")
            for row in gps_result['data']:
                workout_id, points = row[0], row[1]
                # Truncate workout ID for display
                display_id = workout_id[:30] + "..." if len(workout_id) > 30 else workout_id
                print(f"     {display_id:<35} {points:>6,} points")
        
        print()
    
    # Show example queries
    print("🔍 EXAMPLE QUERIES TO TRY:")
    print("-" * 30)
    
    queries = []
    
    if table_info.get('workouts', 0) > 0:
        queries.extend([
            "SELECT COUNT(*) as total_workouts FROM workouts",
            "SELECT activity_type, COUNT(*) FROM workouts GROUP BY activity_type",
            "SELECT file_name, total_distance_km FROM workouts WHERE total_distance_km > 0 ORDER BY total_distance_km DESC LIMIT 5"
        ])
    
    if table_info.get('gps_points', 0) > 0:
        queries.extend([
            "SELECT COUNT(*) as total_gps_points FROM gps_points",
            "SELECT workout_id, COUNT(*) as points FROM gps_points GROUP BY workout_id ORDER BY points DESC LIMIT 3"
        ])
    
    if not queries:
        queries = ["SHOW TABLES", "DESCRIBE workouts"]
    
    for i, query in enumerate(queries[:5], 1):
        print(f"   {i}. {query}")
    
    print()
    print("💡 To execute any query:")
    print(f"   python3 {sys.argv[0]} \"YOUR_SQL_QUERY_HERE\"")
    print("   OR")
    print("   curl -X POST 'http://localhost:8001/query' \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"sql\": \"YOUR_QUERY_HERE\"}'")

def execute_custom_query():
    """Execute a custom SQL query provided as command line argument."""
    if len(sys.argv) < 2:
        print("Usage: python3 live_schema.py \"SQL_QUERY\"")
        print("Example: python3 live_schema.py \"SELECT COUNT(*) FROM workouts\"")
        return
    
    sql = " ".join(sys.argv[1:])
    print(f"🔍 Executing: {sql}")
    print("-" * 50)
    
    result = query_database(sql)
    if result and result.get('status') == 'success':
        columns = result['columns']
        data = result['data']
        
        print(f"✅ Query successful: {len(data)} rows returned")
        print()
        
        if data:
            # Print header
            header = " | ".join(f"{col:<20}" for col in columns)
            print(header)
            print("-" * len(header))
            
            # Print data rows
            for row in data[:20]:  # Limit to first 20 rows
                row_str = " | ".join(f"{str(val) if val is not None else 'NULL':<20}" for val in row)
                print(row_str)
            
            if len(data) > 20:
                print(f"... and {len(data) - 20} more rows")
        else:
            print("✅ Query executed successfully (no data returned)")
    else:
        if result:
            print(f"❌ Query failed: {result.get('detail', 'Unknown error')}")
        else:
            print("❌ Could not execute query - check if service is running")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        execute_custom_query()
    else:
        show_live_schema()