"""
FIT Parser Service

Microservice for parsing FIT files and storing data in DuckDB.
Handles multiple activity types with comprehensive data extraction and validation.
"""

import os
import sys
import logging
import tempfile
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid
import glob

# Add shared modules to path
sys.path.append('/workspace/shared')
sys.path.append('../shared')

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

# Import our comprehensive FIT parser
from fit_parser_utils import FitFileParser, parse_fit_file_data
from shared.database import get_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FIT Parser Service", 
    version="1.0.0",
    description="Advanced FIT file parsing service with GPS data extraction and workout analysis"
)


class FITParserService:
    """
    Advanced service for parsing FIT files and extracting comprehensive workout data.
    """
    
    def __init__(self):
        self._db = None  # Lazy database connection
        self.upload_dir = Path("/tmp/fit_uploads")
        self.upload_dir.mkdir(exist_ok=True)
        
        # Batch processing status tracking
        self.batch_jobs = {}  # job_id -> status info
    
    @property
    def db(self):
        """Lazy database connection."""
        if self._db is None:
            self._db = get_database()
        return self._db
    
    async def process_fit_file(self, file: UploadFile) -> Dict[str, Any]:
        """
        Process an uploaded FIT file completely.
        
        Args:
            file: Uploaded FIT file
            
        Returns:
            Complete parsing results including metadata and GPS data
        """
        # Validate file
        if not file.filename.lower().endswith('.fit'):
            raise HTTPException(
                status_code=400, 
                detail="File must be a .fit file"
            )
        
        # Save file temporarily
        temp_file_path = self.upload_dir / f"{uuid.uuid4()}_{file.filename}"
        
        try:
            # Save uploaded file
            content = await file.read()
            with open(temp_file_path, "wb") as f:
                f.write(content)
            
            # Parse FIT file using our comprehensive parser
            parsed_data = parse_fit_file_data(str(temp_file_path))
            
            # Store in database
            workout_id = self.store_workout_data(parsed_data)
            
            # Add workout_id to response
            parsed_data['workout_id'] = workout_id
            
            logger.info(f"Successfully processed FIT file: {file.filename}")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error processing FIT file {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process FIT file: {str(e)}")
        finally:
            # Clean up temporary file
            if temp_file_path.exists():
                temp_file_path.unlink()
    
    def process_fit_file_from_path(self, file_path: Path) -> Dict[str, Any]:
        """
        Process a FIT file from a given file path.
        
        Args:
            file_path: Path to the FIT file
            
        Returns:
            Complete parsing results including metadata and GPS data
        """
        try:
            # Parse FIT file using our comprehensive parser
            parsed_data = parse_fit_file_data(str(file_path))
            
            # Store in database
            workout_id = self.store_workout_data(parsed_data)
            
            # Add workout_id to response
            parsed_data['workout_id'] = workout_id
            
            logger.info(f"Successfully processed FIT file: {file_path.name}")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error processing FIT file {file_path}: {e}")
            raise ValueError(f"Failed to process FIT file {file_path.name}: {str(e)}")
    
    async def batch_process_folder(self, folder_path: str, job_id: str):
        """
        Background task to process all FIT files in a folder.
        
        Args:
            folder_path: Path to folder containing FIT files
            job_id: Unique identifier for this batch job
        """
        try:
            # Initialize job status
            self.batch_jobs[job_id] = {
                'status': 'running',
                'started_at': datetime.now(timezone.utc).isoformat(),
                'folder_path': folder_path,
                'total_files': 0,
                'processed_files': 0,
                'successful_files': 0,
                'failed_files': 0,
                'results': [],
                'errors': []
            }
            
            # Find all FIT files in the folder
            folder = Path(folder_path)
            if not folder.exists():
                self.batch_jobs[job_id]['status'] = 'failed'
                self.batch_jobs[job_id]['error'] = f"Folder does not exist: {folder_path}"
                return
            
            # Get all .fit files (case-insensitive)
            fit_files = []
            for pattern in ['*.fit', '*.FIT']:
                fit_files.extend(folder.glob(pattern))
                fit_files.extend(folder.rglob(pattern))  # Include subdirectories
            
            # Remove duplicates
            fit_files = list(set(fit_files))
            
            self.batch_jobs[job_id]['total_files'] = len(fit_files)
            
            if len(fit_files) == 0:
                self.batch_jobs[job_id]['status'] = 'completed'
                self.batch_jobs[job_id]['message'] = 'No FIT files found in the specified folder'
                return
            
            logger.info(f"Starting batch processing of {len(fit_files)} FIT files in {folder_path}")
            
            # Process each file
            for file_path in fit_files:
                try:
                    # Update progress
                    self.batch_jobs[job_id]['current_file'] = str(file_path)
                    
                    # Process the file
                    result = self.process_fit_file_from_path(file_path)
                    
                    # Add to results
                    self.batch_jobs[job_id]['results'].append({
                        'file_name': file_path.name,
                        'file_path': str(file_path),
                        'workout_id': result['workout_id'],
                        'activity_type': result['workout_metadata'].get('activity_type', 'unknown'),
                        'duration_minutes': round(result['workout_metadata'].get('duration_seconds', 0) / 60, 1),
                        'gps_points': len(result.get('gps_points', [])),
                        'status': 'success'
                    })
                    
                    self.batch_jobs[job_id]['successful_files'] += 1
                    
                except Exception as e:
                    # Log error but continue processing
                    error_info = {
                        'file_name': file_path.name,
                        'file_path': str(file_path),
                        'error': str(e),
                        'status': 'failed'
                    }
                    self.batch_jobs[job_id]['errors'].append(error_info)
                    self.batch_jobs[job_id]['failed_files'] += 1
                    logger.error(f"Failed to process {file_path}: {e}")
                
                finally:
                    self.batch_jobs[job_id]['processed_files'] += 1
                    
                # Add small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)
            
            # Mark job as completed
            self.batch_jobs[job_id]['status'] = 'completed'
            self.batch_jobs[job_id]['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Batch processing completed: {self.batch_jobs[job_id]['successful_files']} successful, {self.batch_jobs[job_id]['failed_files']} failed")
            
        except Exception as e:
            # Mark job as failed
            self.batch_jobs[job_id]['status'] = 'failed'
            self.batch_jobs[job_id]['error'] = str(e)
            self.batch_jobs[job_id]['failed_at'] = datetime.now(timezone.utc).isoformat()
            logger.error(f"Batch processing job {job_id} failed: {e}")
    
    def get_batch_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a batch processing job."""
        if job_id not in self.batch_jobs:
            raise HTTPException(status_code=404, detail="Batch job not found")
        
        return self.batch_jobs[job_id]
    
    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about all processed FIT files."""
        try:
            # Get activity summary from database
            summary_df = self.db.get_activity_summary()
            
            if summary_df.empty:
                return {
                    "status": "success",
                    "total_workouts": 0,
                    "message": "No workouts found in database"
                }
            
            # Convert DataFrame to list of dictionaries for processing
            workouts = summary_df.to_dict('records')
            
            # Calculate statistics
            total_workouts = len(workouts)
            total_duration_hours = sum(w.get('duration_seconds', 0) for w in workouts) / 3600
            total_distance_km = sum(w.get('total_distance_km', 0) for w in workouts)
            total_calories = sum(w.get('calories', 0) for w in workouts)
            
            # Activity type breakdown
            activity_types = {}
            for workout in workouts:
                activity_type = workout.get('activity_type', 'unknown')
                activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
            
            # Date range
            dates = [w.get('start_time', '') for w in workouts if w.get('start_time')]
            date_range = {
                'earliest': min(dates) if dates else None,
                'latest': max(dates) if dates else None
            }
            
            return {
                "status": "success",
                "summary": {
                    "total_workouts": total_workouts,
                    "total_duration_hours": round(total_duration_hours, 2),
                    "total_distance_km": round(total_distance_km, 2),
                    "total_calories": total_calories,
                    "date_range": date_range
                },
                "activity_breakdown": activity_types,
                "database_info": {
                    "service_name": "fit-parser",
                    "database_type": "DuckDB"
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting comprehensive statistics: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
    
    def store_workout_data(self, parsed_data: Dict[str, Any]) -> str:
        """
        Store parsed workout data in DuckDB database.
        
        Args:
            parsed_data: Complete parsed workout data
            
        Returns:
            Generated workout_id
        """
        try:
            # Extract metadata for workout table
            workout_metadata = parsed_data['workout_metadata']
            
            # Store workout metadata
            workout_id = self.db.insert_workout(workout_metadata)
            
            # Store GPS points if available
            gps_points = parsed_data.get('gps_points', [])
            if gps_points:
                # Convert to DataFrame for database insertion
                import pandas as pd
                gps_df = pd.DataFrame(gps_points)
                self.db.insert_gps_points(workout_id, gps_df)
            
            logger.info(f"Stored workout {workout_id} with {len(gps_points)} GPS points")
            return workout_id
            
        except Exception as e:
            logger.error(f"Error storing workout data: {e}")
            raise HTTPException(status_code=500, detail=f"Database storage failed: {str(e)}")
    
    def get_workout_summary(self, workout_id: str) -> Dict[str, Any]:
        """Get workout summary with metadata and GPS statistics."""
        try:
            # Get workout metadata
            workout = self.db.get_workout_by_id(workout_id)
            if not workout:
                raise HTTPException(status_code=404, detail="Workout not found")
            
            # Get GPS data summary
            gps_data = self.db.get_workout_gps_data(workout_id)
            
            # Add GPS statistics to summary
            summary = dict(workout)
            summary['gps_statistics'] = {
                'total_points': len(gps_data),
                'has_elevation': not gps_data['elevation_m'].isna().all() if 'elevation_m' in gps_data.columns else False,
                'has_heart_rate': not gps_data['heart_rate'].isna().all() if 'heart_rate' in gps_data.columns else False,
                'has_power': not gps_data['power_watts'].isna().all() if 'power_watts' in gps_data.columns else False,
            }
            
            if len(gps_data) > 0:
                summary['gps_statistics'].update({
                    'first_point_time': gps_data['timestamp'].min() if 'timestamp' in gps_data.columns else None,
                    'last_point_time': gps_data['timestamp'].max() if 'timestamp' in gps_data.columns else None,
                })
            
            return summary
            
        except Exception as e:
            logger.error(f"Error retrieving workout summary {workout_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# Initialize service
fit_parser_service = FITParserService()


@app.post("/parse", summary="Parse FIT File", tags=["FIT Parsing"])
async def parse_fit_file(
    file: UploadFile = File(..., description="FIT file to parse"),
    store_in_db: bool = Query(True, description="Whether to store results in database")
):
    """
    Parse a FIT file and extract comprehensive workout data.
    
    - **file**: FIT file from GPS device (Garmin, Polar, etc.)
    - **store_in_db**: Whether to automatically store results in database
    
    Returns detailed workout metadata, GPS points, and device information.
    """
    try:
        # Process the FIT file
        parsed_data = await fit_parser_service.process_fit_file(file)
        
        # Get workout summary for response
        workout_summary = FitFileParser().get_workout_summary() if hasattr(FitFileParser(), 'workout_data') else {}
        
        return {
            "status": "success",
            "message": f"Successfully parsed {file.filename}",
            "workout_id": parsed_data.get('workout_id'),
            "file_info": {
                "name": file.filename,
                "size_bytes": len(await file.read()) if hasattr(file, 'read') else None,
                "parsed_at": parsed_data.get('parsed_at')
            },
            "workout_summary": {
                "activity_type": parsed_data['workout_metadata'].get('activity_type', 'unknown'),
                "duration_minutes": round(parsed_data['workout_metadata'].get('duration_seconds', 0) / 60, 1),
                "distance_km": round(parsed_data['workout_metadata'].get('total_distance_km', 0), 2),
                "gps_points": len(parsed_data.get('gps_points', [])),
                "device": f"{parsed_data['device_info'].get('manufacturer', 'Unknown')} {parsed_data['device_info'].get('product', '')}"
            },
            "data": parsed_data if not store_in_db else {"workout_id": parsed_data.get('workout_id')}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing FIT file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during FIT file parsing")


@app.get("/workout/{workout_id}", summary="Get Workout", tags=["Workout Data"])
async def get_workout(workout_id: str):
    """
    Get comprehensive workout metadata by ID.
    
    Returns detailed workout information including metrics, device info, and activity details.
    """
    try:
        summary = fit_parser_service.get_workout_summary(workout_id)
        return {
            "status": "success",
            "workout_id": workout_id,
            "data": summary
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving workout {workout_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve workout")


@app.get("/workout/{workout_id}/gps", summary="Get GPS Data", tags=["Workout Data"])
async def get_workout_gps(
    workout_id: str,
    limit: int = Query(None, description="Limit number of GPS points returned"),
    format: str = Query("json", description="Response format: json or geojson")
):
    """
    Get GPS data for a workout.
    
    - **workout_id**: ID of the workout
    - **limit**: Maximum number of GPS points to return
    - **format**: Response format (json or geojson)
    
    Returns GPS coordinates and associated metrics for mapping and analysis.
    """
    try:
        gps_data = fit_parser_service.db.get_workout_gps_data(workout_id)
        
        if len(gps_data) == 0:
            return {
                "status": "success",
                "workout_id": workout_id,
                "message": "No GPS data found for this workout",
                "point_count": 0,
                "data": []
            }
        
        # Apply limit if specified
        if limit and limit > 0:
            gps_data = gps_data.head(limit)
        
        # Format response
        if format.lower() == "geojson":
            # Convert to GeoJSON format
            features = []
            for idx, row in gps_data.iterrows():
                if pd.notna(row.get('latitude')) and pd.notna(row.get('longitude')):
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [row['longitude'], row['latitude']]
                        },
                        "properties": {
                            "timestamp": row.get('timestamp'),
                            "elevation_m": row.get('elevation_m'),
                            "speed_kmh": row.get('speed_kmh'),
                            "heart_rate": row.get('heart_rate'),
                            "sequence": idx
                        }
                    }
                    features.append(feature)
            
            return {
                "type": "FeatureCollection",
                "workout_id": workout_id,
                "point_count": len(features),
                "features": features
            }
        else:
            # Standard JSON format
            return {
                "status": "success",
                "workout_id": workout_id,
                "point_count": len(gps_data),
                "data": gps_data.to_dict('records')
            }
            
    except Exception as e:
        logger.error(f"Error retrieving GPS data for {workout_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve GPS data")


@app.get("/workouts", summary="List Workouts", tags=["Workout Data"])
async def list_workouts(
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    limit: int = Query(50, description="Maximum number of workouts to return"),
    offset: int = Query(0, description="Number of workouts to skip")
):
    """
    List workouts with optional filtering.
    
    Returns a list of workouts with basic metadata for browsing and selection.
    """
    try:
        # This would require implementing a list_workouts method in the database
        # For now, return a simple response
        return {
            "status": "success",
            "message": "Workout listing endpoint - implementation pending",
            "filters": {
                "activity_type": activity_type,
                "limit": limit,
                "offset": offset
            }
        }
    except Exception as e:
        logger.error(f"Error listing workouts: {e}")
        raise HTTPException(status_code=500, detail="Failed to list workouts")


@app.get("/stats", summary="Parser Statistics", tags=["Service Info"])
async def get_parser_stats():
    """
    Get FIT parser service statistics.
    
    Returns information about parsed workouts, supported activity types, and service health.
    """
    try:
        # Get activity summary from database
        activity_summary = fit_parser_service.db.get_activity_summary()
        
        return {
            "status": "healthy",
            "service": "fit-parser",
            "version": "1.0.0",
            "supported_activities": list(FitFileParser.ACTIVITY_TYPE_MAPPING.values()),
            "statistics": {
                "total_activities": activity_summary['workout_count'].sum() if len(activity_summary) > 0 else 0,
                "activity_breakdown": activity_summary.to_dict('records') if len(activity_summary) > 0 else [],
                "database_status": "connected"
            }
        }
    except Exception as e:
        logger.error(f"Error getting parser stats: {e}")
        return {
            "status": "degraded",
            "service": "fit-parser",
            "error": str(e)
        }


@app.post("/parse/batch", summary="Process all FIT files in a folder")
async def batch_parse_fit_files(
    folder_path: str,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Start batch processing of all FIT files in a specified folder.
    
    Args:
        folder_path: Path to folder containing FIT files
        background_tasks: FastAPI background tasks manager
    
    Returns:
        Job information including job_id for tracking progress
    """
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Validate folder path
    folder = Path(folder_path)
    if not folder.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Folder does not exist: {folder_path}"
        )
    
    if not folder.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a directory: {folder_path}"
        )
    
    # Start background processing
    background_tasks.add_task(
        fit_parser_service.batch_process_folder,
        folder_path,
        job_id
    )
    
    return {
        "job_id": job_id,
        "status": "started",
        "message": f"Batch processing started for folder: {folder_path}",
        "folder_path": folder_path,
        "check_status_url": f"/parse/batch/{job_id}/status"
    }


@app.get("/parse/batch/{job_id}/status", summary="Get batch processing job status")
async def get_batch_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status and progress of a batch processing job.
    
    Args:
        job_id: Unique identifier for the batch job
    
    Returns:
        Detailed status information including progress and results
    """
    try:
        status = fit_parser_service.get_batch_job_status(job_id)
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch job status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )


@app.get("/parse/batch/{job_id}/results", summary="Get batch processing results")
async def get_batch_job_results(job_id: str) -> Dict[str, Any]:
    """
    Get the detailed results of a completed batch processing job.
    
    Args:
        job_id: Unique identifier for the batch job
    
    Returns:
        Complete results including all processed files and any errors
    """
    try:
        status = fit_parser_service.get_batch_job_status(job_id)
        
        if status['status'] == 'running':
            return {
                "job_id": job_id,
                "status": "running",
                "message": "Job is still running. Check status endpoint for progress.",
                "progress": {
                    "processed": status.get('processed_files', 0),
                    "total": status.get('total_files', 0),
                    "current_file": status.get('current_file')
                }
            }
        
        return {
            "job_id": job_id,
            "status": status['status'],
            "summary": {
                "total_files": status.get('total_files', 0),
                "successful_files": status.get('successful_files', 0),
                "failed_files": status.get('failed_files', 0),
                "processing_time": status.get('completed_at', status.get('failed_at'))
            },
            "successful_results": status.get('results', []),
            "errors": status.get('errors', [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch job results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job results: {str(e)}"
        )


@app.delete("/parse/batch/{job_id}", summary="Cancel or delete a batch processing job")
async def delete_batch_job(job_id: str) -> Dict[str, str]:
    """
    Cancel a running batch job or delete completed job data.
    
    Args:
        job_id: Unique identifier for the batch job
    
    Returns:
        Confirmation message
    """
    try:
        if job_id in fit_parser_service.batch_jobs:
            del fit_parser_service.batch_jobs[job_id]
            return {"message": f"Batch job {job_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Batch job not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting batch job: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete job: {str(e)}"
        )


@app.get("/statistics", summary="Get comprehensive FIT file processing statistics")
async def get_statistics() -> Dict[str, Any]:
    """
    Get comprehensive statistics about all processed FIT files.
    
    Returns:
        Detailed statistics including activity breakdown and performance metrics
    """
    try:
        stats = fit_parser_service.get_comprehensive_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )


@app.get("/health", summary="Health Check", tags=["Service Info"])
async def health_check():
    """Health check endpoint for service monitoring."""
    try:
        # Test database connection
        _ = fit_parser_service.db.get_activity_summary()
        return {
            "status": "healthy",
            "service": "fit-parser",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "fit-parser",
            "error": str(e)
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
