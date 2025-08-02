"""
Visualization Service

Microservice for creating route visualizations, elevation profiles, and heat maps.
Integrates with map tiles and GPS data from other services.
"""

import os
import sys
import logging
from typing import Dict, List, Optional
from pathlib import Path

# Add shared modules to path
sys.path.append('/workspace/shared')
sys.path.append('../shared')

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import uvicorn

from shared.database import get_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Visualization Service", version="1.0.0")


class VisualizationService:
    """
    Service for creating workout visualizations and analytics.
    """
    
    def __init__(self):
        self.db = get_database()
        self.output_dir = Path("/app/output")
        self.output_dir.mkdir(exist_ok=True)
    
    def create_single_route_visualization(self, workout_id: str, options: Dict) -> str:
        """
        Create visualization for a single workout route.
        
        Args:
            workout_id: ID of the workout to visualize
            options: Visualization options
            
        Returns:
            Path to generated visualization file
        """
        # Implementation placeholder for Copilot
        # This will be implemented in the next development phase
        logger.info(f"Creating single route visualization for workout {workout_id}")
        return "placeholder_single_route.png"
    
    def create_multi_route_visualization(self, workout_ids: List[str], options: Dict) -> str:
        """
        Create visualization overlaying multiple workout routes.
        
        Args:
            workout_ids: List of workout IDs to overlay
            options: Visualization options
            
        Returns:
            Path to generated visualization file
        """
        # Implementation placeholder for Copilot
        logger.info(f"Creating multi-route visualization for {len(workout_ids)} workouts")
        return "placeholder_multi_route.png"
    
    def create_heat_map(self, bounds: List[float], options: Dict) -> str:
        """
        Create heat map visualization for activity density.
        
        Args:
            bounds: Geographic bounds [lat_min, lon_min, lat_max, lon_max]
            options: Heat map options
            
        Returns:
            Path to generated heat map file
        """
        # Implementation placeholder for Copilot
        logger.info(f"Creating heat map for bounds {bounds}")
        return "placeholder_heat_map.png"


# Initialize service
viz_service = VisualizationService()


@app.post("/create-visualization")
async def create_visualization(request: Dict):
    """Create visualization based on request type."""
    try:
        viz_type = request.get('visualization_type')
        options = request.get('options', {})
        
        if viz_type == 'single_route':
            workout_id = request.get('workout_id')
            if not workout_id:
                raise HTTPException(status_code=400, detail="workout_id required for single_route")
            
            output_file = viz_service.create_single_route_visualization(workout_id, options)
            
        elif viz_type == 'multi_route_overlay':
            workout_ids = request.get('workout_ids', [])
            if not workout_ids:
                raise HTTPException(status_code=400, detail="workout_ids required for multi_route_overlay")
            
            output_file = viz_service.create_multi_route_visualization(workout_ids, options)
            
        elif viz_type == 'heat_map':
            bounds = request.get('bounds')
            if not bounds or len(bounds) != 4:
                raise HTTPException(status_code=400, detail="bounds [lat_min, lon_min, lat_max, lon_max] required for heat_map")
            
            output_file = viz_service.create_heat_map(bounds, options)
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown visualization type: {viz_type}")
        
        return {
            "status": "success",
            "visualization_type": viz_type,
            "output_file": output_file,
            "download_url": f"/download/{output_file}"
        }
        
    except Exception as e:
        logger.error(f"Error creating visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated visualization file."""
    file_path = viz_service.output_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "visualization"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
