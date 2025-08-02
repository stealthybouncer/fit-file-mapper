"""
Example Usage and Workflow for FIT File Mapper

This module demonstrates the intended workflow and usage patterns
for the FIT File Mapper application. Use these examples to understand
the project's goals and implementation approach.
"""

from pathlib import Path
import pandas as pd
from src.fit_parser import FITParser
from src.gps_processor import GPSProcessor
from src.map_downloader import USGSMapDownloader
from src.map_stitcher import MapStitcher
from src.visualizer import MapVisualizer


def example_single_workout():
    """Example: Process and visualize a single workout FIT file."""
    
    # Step 1: Parse FIT file
    parser = FITParser()
    workout_data = parser.parse_file("data/fit_files/central_park_run.fit")
    
    # Step 2: Clean and process GPS data
    processor = GPSProcessor()
    cleaned_data = processor.clean_coordinates(workout_data)
    
    # Step 3: Download required map tiles
    downloader = USGSMapDownloader()
    route_bounds = processor.calculate_route_bounds(
        list(zip(cleaned_data['latitude'], cleaned_data['longitude']))
    )
    tiles = downloader.download_area(route_bounds, zoom=16, map_type="satellite")
    
    # Step 4: Stitch map tiles
    stitcher = MapStitcher()
    base_map = stitcher.stitch_tiles(tiles)
    
    # Step 5: Create visualization
    visualizer = MapVisualizer()
    final_map = visualizer.create_route_overlay(
        list(zip(cleaned_data['latitude'], cleaned_data['longitude'])),
        base_map,
        route_bounds
    )
    
    # Step 6: Save output
    visualizer.save_visualization(final_map, Path("output/central_park_run.png"))


def example_multi_workout_overlay():
    """Example: Overlay multiple workouts on the same map."""
    
    # Parse multiple FIT files
    parser = FITParser()
    workouts = parser.parse_multiple_files([
        "data/fit_files/morning_run.fit",
        "data/fit_files/evening_run.fit",
        "data/fit_files/weekend_hike.fit"
    ])
    
    # Process each workout
    processor = GPSProcessor()
    processed_workouts = []
    for name, data in workouts.items():
        cleaned = processor.clean_coordinates(data)
        processed_workouts.append({
            'name': name,
            'data': cleaned,
            'coordinates': list(zip(cleaned['latitude'], cleaned['longitude']))
        })
    
    # Calculate combined bounds
    all_coords = []
    for workout in processed_workouts:
        all_coords.extend(workout['coordinates'])
    combined_bounds = processor.calculate_route_bounds(all_coords)
    
    # Download and stitch map
    downloader = USGSMapDownloader()
    tiles = downloader.download_area(combined_bounds, zoom=15, map_type="satellite")
    stitcher = MapStitcher()
    base_map = stitcher.stitch_tiles(tiles)
    
    # Create multi-workout visualization
    visualizer = MapVisualizer()
    multi_map = visualizer.create_multi_workout_overlay(
        processed_workouts, base_map, combined_bounds
    )
    
    visualizer.save_visualization(multi_map, Path("output/multi_workout_overlay.png"))


def example_multi_day_adventure():
    """Example: Stitch together a multi-day hiking adventure."""
    
    # Parse multi-day FIT files
    parser = FITParser()
    daily_files = [
        "data/fit_files/appalachian_day1.fit",
        "data/fit_files/appalachian_day2.fit",
        "data/fit_files/appalachian_day3.fit"
    ]
    
    daily_workouts = []
    for file_path in daily_files:
        data = parser.parse_file(file_path)
        daily_workouts.append(data)
    
    # Stitch workouts together
    stitched_route = parser.stitch_workouts(daily_workouts, max_gap_minutes=720)  # 12 hours
    
    # Process stitched route
    processor = GPSProcessor()
    cleaned_route = processor.clean_coordinates(stitched_route)
    route_coords = list(zip(cleaned_route['latitude'], cleaned_route['longitude']))
    
    # Download map tiles for entire route
    downloader = USGSMapDownloader()
    route_bounds = processor.calculate_route_bounds(route_coords, buffer_km=2.0)
    tiles = downloader.download_area(route_bounds, zoom=14, map_type="satellite")
    
    # Create multi-day stitched visualization
    stitcher = MapStitcher()
    base_map = stitcher.stitch_route_map(route_coords, tiles, zoom=14)
    
    visualizer = MapVisualizer()
    final_map = visualizer.stitch_workout_visualization(
        daily_workouts, base_map, segment_colors=["#FF0000", "#00FF00", "#0000FF"]
    )
    
    # Add elevation profile
    elevations = cleaned_route['elevation'].tolist()
    elevation_chart = visualizer.create_elevation_profile(route_coords, elevations)
    
    # Save outputs
    visualizer.save_visualization(final_map, Path("output/appalachian_3day_route.png"))
    elevation_chart.savefig("output/appalachian_elevation_profile.png", dpi=300)


def example_nyc_area_runs():
    """Example: Create heat map of frequent running routes in NYC area."""
    
    # Parse all NYC area running files
    parser = FITParser()
    nyc_fit_files = list(Path("data/fit_files/nyc_runs").glob("*.fit"))
    
    all_workouts = []
    for file_path in nyc_fit_files:
        try:
            data = parser.parse_file(file_path)
            # Filter for NYC area coordinates
            nyc_data = data[
                (data['latitude'].between(40.4774, 40.9176)) &
                (data['longitude'].between(-74.2591, -73.7004))
            ]
            if not nyc_data.empty:
                all_workouts.append(nyc_data)
        except Exception as e:
            print(f"Skipping {file_path}: {e}")
    
    # Create heat map
    processor = GPSProcessor()
    nyc_bounds = (40.4774, -74.2591, 40.9176, -73.7004)  # NYC metro bounds
    
    downloader = USGSMapDownloader()
    tiles = downloader.download_area(nyc_bounds, zoom=12, map_type="satellite")
    
    stitcher = MapStitcher()
    base_map = stitcher.stitch_tiles(tiles)
    
    visualizer = MapVisualizer()
    heat_map = visualizer.create_heat_map(all_workouts, nyc_bounds, grid_size=200)
    
    # Overlay heat map on satellite imagery
    # Implementation would blend heat map with base map
    
    visualizer.save_visualization(base_map, Path("output/nyc_running_heat_map.png"))


def example_elevation_analysis():
    """Example: Detailed elevation analysis for mountain biking route."""
    
    parser = FITParser()
    workout_data = parser.parse_file("data/fit_files/mountain_bike_trail.fit")
    
    processor = GPSProcessor()
    cleaned_data = processor.clean_coordinates(workout_data)
    
    # Calculate detailed metrics
    coordinates = list(zip(cleaned_data['latitude'], cleaned_data['longitude']))
    distances = processor.calculate_distances(coordinates)
    elevations = cleaned_data['elevation'].tolist()
    
    # Create comprehensive visualization
    visualizer = MapVisualizer()
    summary_viz = visualizer.create_workout_summary_viz(cleaned_data)
    
    # Individual components
    elevation_profile = visualizer.create_elevation_profile(coordinates, elevations, distances)
    
    # Save all outputs
    summary_viz.savefig("output/mountain_bike_summary.png", dpi=300, bbox_inches='tight')
    elevation_profile.savefig("output/mountain_bike_elevation.png", dpi=300)


def example_batch_processing():
    """Example: Batch process multiple FIT files for analysis."""
    
    # Get all FIT files in directory
    fit_files = list(Path("data/fit_files").glob("**/*.fit"))
    
    parser = FITParser()
    processor = GPSProcessor()
    
    # Process each file and collect metrics
    workout_summary = []
    
    for file_path in fit_files:
        try:
            # Parse and process
            data = parser.parse_file(file_path)
            cleaned_data = processor.clean_coordinates(data)
            
            # Calculate metrics
            coordinates = list(zip(cleaned_data['latitude'], cleaned_data['longitude']))
            total_distance = processor.calculate_distances(coordinates)[-1]
            duration = (cleaned_data['timestamp'].iloc[-1] - cleaned_data['timestamp'].iloc[0]).total_seconds() / 3600
            
            # Store summary
            workout_summary.append({
                'file': file_path.name,
                'activity_type': parser.detect_activity_type(cleaned_data),
                'distance_km': total_distance,
                'duration_hours': duration,
                'avg_speed_kmh': total_distance / duration if duration > 0 else 0,
                'coordinates': coordinates
            })
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Create summary report
    summary_df = pd.DataFrame(workout_summary)
    summary_df.to_csv("output/workout_analysis_summary.csv", index=False)
    
    print(f"Processed {len(workout_summary)} workouts successfully")
    return summary_df


if __name__ == "__main__":
    print("FIT File Mapper - Example Usage")
    print("=" * 40)
    
    # Run examples (commented out for safety)
    # example_single_workout()
    # example_multi_workout_overlay()
    # example_multi_day_adventure()
    # example_nyc_area_runs()
    # example_elevation_analysis()
    # summary = example_batch_processing()
    
    print("Example usage patterns defined. Uncomment function calls to run.")
