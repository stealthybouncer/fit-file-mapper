"""
API Gateway Service

Central API gateway that orchestrates communication between FIT File Mapper services.
Provides unified endpoints for client applications.
"""

import os
import sys
import logging
from typing import Dict, List, Optional
import json

# Add shared modules to path
sys.path.append('/workspace/shared')
sys.path.append('../shared')

import aiohttp
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from shared.database import get_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FIT File Mapper API Gateway",
    version="1.0.0",
    description="Unified API for FIT file parsing, mapping, and visualization"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class APIGateway:
    """
    Central API gateway coordinating all FIT File Mapper services.
    """
    
    def __init__(self):
        self.db = get_database()
        self.services = {
            'fit_parser': os.getenv('FIT_PARSER_URL', 'http://fit-parser-service:8000'),
            'map_service': os.getenv('MAP_SERVICE_URL', 'http://map-service:8000'),
            'visualization': os.getenv('VISUALIZATION_URL', 'http://visualization-service:8000')
        }
    
    async def call_service(self, service: str, endpoint: str, 
                          method: str = 'GET', data: Optional[Dict] = None,
                          files: Optional[Dict] = None) -> Dict:
        """
        Make HTTP call to a microservice.
        
        Args:
            service: Service name (fit_parser, map_service, visualization)
            endpoint: API endpoint path
            method: HTTP method
            data: JSON data for POST requests
            files: Files for upload
            
        Returns:
            Response data from service
        """
        if service not in self.services:
            raise ValueError(f"Unknown service: {service}")
        
        url = f"{self.services[service]}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == 'GET':
                    async with session.get(url) as response:
                        return await self._handle_response(response)
                
                elif method == 'POST':
                    if files:
                        # Handle file uploads
                        data_obj = aiohttp.FormData()
                        for key, file_data in files.items():
                            data_obj.add_field(key, file_data)
                        
                        async with session.post(url, data=data_obj) as response:
                            return await self._handle_response(response)
                    else:
                        # Handle JSON data
                        async with session.post(url, json=data) as response:
                            return await self._handle_response(response)
                
                elif method == 'DELETE':
                    async with session.delete(url) as response:
                        return await self._handle_response(response)
                        
        except Exception as e:
            logger.error(f"Error calling {service}{endpoint}: {e}")
            raise HTTPException(status_code=503, detail=f"Service {service} unavailable")
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict:
        """Handle HTTP response from service."""
        if response.status == 200:
            return await response.json()
        elif response.status == 404:
            raise HTTPException(status_code=404, detail="Resource not found")
        else:
            error_text = await response.text()
            raise HTTPException(status_code=response.status, detail=error_text)


# Initialize gateway
gateway = APIGateway()


# FIT File Operations
@app.post("/api/upload-fit")
async def upload_fit_file(file: UploadFile = File(...)):
    """Upload and parse a FIT file."""
    try:
        # Read file content
        file_content = await file.read()
        
        # Send to FIT parser service
        result = await gateway.call_service(
            'fit_parser', 
            '/parse-file',
            method='POST',
            files={'file': file_content}
        )
        
        # Download map tiles for the workout
        if result.get('status') == 'success':
            workout_id = result['workout_id']
            
            # Get GPS data
            gps_result = await gateway.call_service(
                'fit_parser',
                f'/workout/{workout_id}/gps'
            )
            
            if gps_result['point_count'] > 0:
                # Extract coordinates
                coordinates = [[point['latitude'], point['longitude']] 
                             for point in gps_result['gps_data'] 
                             if point['latitude'] and point['longitude']]
                
                if coordinates:
                    # Download map tiles
                    await gateway.call_service(
                        'map_service',
                        '/download-route',
                        method='POST',
                        data={
                            'coordinates': coordinates,
                            'zoom': 16,
                            'map_type': 'satellite',
                            'buffer_km': 1.0
                        }
                    )
        
        return result
        
    except Exception as e:
        logger.error(f"Error uploading FIT file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workouts")
async def list_workouts():
    """Get list of all workouts."""
    try:
        workouts = gateway.db.query_workouts_by_date_range(
            start_date=pd.Timestamp('2020-01-01'),
            end_date=pd.Timestamp.now()
        )
        
        return {
            "total_workouts": len(workouts),
            "workouts": workouts.to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Error listing workouts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workout/{workout_id}")
async def get_workout_details(workout_id: str):
    """Get detailed workout information."""
    try:
        # Get workout metadata
        workout = await gateway.call_service('fit_parser', f'/workout/{workout_id}')
        
        # Get GPS data
        gps_data = await gateway.call_service('fit_parser', f'/workout/{workout_id}/gps')
        
        return {
            "workout": workout,
            "gps_data": gps_data
        }
        
    except Exception as e:
        logger.error(f"Error getting workout {workout_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Visualization Operations
@app.post("/api/visualize/single-workout/{workout_id}")
async def create_single_workout_visualization(workout_id: str, options: Dict = None):
    """Create visualization for a single workout."""
    try:
        # Get workout GPS data
        gps_result = await gateway.call_service('fit_parser', f'/workout/{workout_id}/gps')
        
        if gps_result['point_count'] == 0:
            raise HTTPException(status_code=400, detail="No GPS data available for workout")
        
        # Create visualization
        viz_request = {
            'workout_id': workout_id,
            'visualization_type': 'single_route',
            'options': options or {
                'map_type': 'satellite',
                'zoom': 16,
                'route_color': '#FF0000',
                'include_elevation_profile': True
            }
        }
        
        result = await gateway.call_service(
            'visualization',
            '/create-visualization',
            method='POST',
            data=viz_request
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating visualization for {workout_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/visualize/multi-workout")
async def create_multi_workout_visualization(request: Dict):
    """Create visualization overlaying multiple workouts."""
    try:
        workout_ids = request.get('workout_ids', [])
        options = request.get('options', {})
        
        if not workout_ids:
            raise HTTPException(status_code=400, detail="No workout IDs provided")
        
        # Validate workouts exist and have GPS data
        valid_workouts = []
        for workout_id in workout_ids:
            try:
                gps_result = await gateway.call_service('fit_parser', f'/workout/{workout_id}/gps')
                if gps_result['point_count'] > 0:
                    valid_workouts.append(workout_id)
            except:
                logger.warning(f"Skipping invalid workout: {workout_id}")
        
        if not valid_workouts:
            raise HTTPException(status_code=400, detail="No valid workouts with GPS data")
        
        # Create multi-workout visualization
        viz_request = {
            'workout_ids': valid_workouts,
            'visualization_type': 'multi_route_overlay',
            'options': {
                'map_type': 'satellite',
                'zoom': 14,
                'auto_colors': True,
                **options
            }
        }
        
        result = await gateway.call_service(
            'visualization',
            '/create-visualization',
            method='POST',
            data=viz_request
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating multi-workout visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/visualize/heat-map")
async def create_heat_map(request: Dict):
    """Create heat map visualization."""
    try:
        area_bounds = request.get('bounds')  # [lat_min, lon_min, lat_max, lon_max]
        options = request.get('options', {})
        
        if not area_bounds or len(area_bounds) != 4:
            raise HTTPException(status_code=400, detail="Invalid area bounds")
        
        # Create heat map
        viz_request = {
            'visualization_type': 'heat_map',
            'bounds': area_bounds,
            'options': {
                'map_type': 'satellite',
                'grid_size': 100,
                'zoom': 13,
                **options
            }
        }
        
        result = await gateway.call_service(
            'visualization',
            '/create-visualization',
            method='POST',
            data=viz_request
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating heat map: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Analytics Operations
@app.get("/api/analytics/summary")
async def get_activity_summary():
    """Get activity summary statistics."""
    try:
        summary = gateway.db.get_activity_summary()
        return {
            "activity_summary": summary.to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Error getting activity summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/workouts-in-area")
async def get_workouts_in_area(lat_min: float, lon_min: float, lat_max: float, lon_max: float):
    """Get workouts that intersect with a geographic area."""
    try:
        workouts = gateway.db.query_workouts_by_area(lat_min, lon_min, lat_max, lon_max)
        return {
            "area_bounds": [lat_min, lon_min, lat_max, lon_max],
            "workout_count": len(workouts),
            "workouts": workouts.to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Error querying workouts in area: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Map Operations
@app.post("/api/maps/preload-nyc")
async def preload_nyc_maps():
    """Preload NYC area maps for offline use."""
    try:
        result = await gateway.call_service('map_service', '/preload-nyc', method='POST')
        return result
        
    except Exception as e:
        logger.error(f"Error preloading NYC maps: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/maps/cleanup-cache")
async def cleanup_map_cache(days_old: int = 90):
    """Clean up old cached map tiles."""
    try:
        result = await gateway.call_service('map_service', f'/cache/cleanup?days_old={days_old}', method='DELETE')
        return result
        
    except Exception as e:
        logger.error(f"Error cleaning up map cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health Check
@app.get("/api/health")
async def health_check():
    """Health check for all services."""
    try:
        health_status = {"gateway": "healthy"}
        
        # Check each service
        for service_name in ['fit_parser', 'map_service', 'visualization']:
            try:
                result = await gateway.call_service(service_name, '/health')
                health_status[service_name] = result.get('status', 'unknown')
            except:
                health_status[service_name] = 'unhealthy'
        
        # Overall status
        all_healthy = all(status == 'healthy' for status in health_status.values())
        health_status['overall'] = 'healthy' if all_healthy else 'degraded'
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error checking service health: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "service": "FIT File Mapper API Gateway",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "upload_fit": "POST /api/upload-fit",
            "workouts": "GET /api/workouts",
            "workout_details": "GET /api/workout/{workout_id}",
            "single_visualization": "POST /api/visualize/single-workout/{workout_id}",
            "multi_visualization": "POST /api/visualize/multi-workout",
            "heat_map": "POST /api/visualize/heat-map",
            "activity_summary": "GET /api/analytics/summary",
            "health": "GET /api/health"
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
