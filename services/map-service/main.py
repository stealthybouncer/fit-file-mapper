"""
Map Service

Microservice for downloading, caching, and serving USGS map tiles.
Optimized for satellite imagery with offline capabilities.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import math
import hashlib

# Add shared modules to path
sys.path.append('/workspace/shared')
sys.path.append('../shared')

import aiohttp
import asyncio
import io
from PIL import Image
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
import uvicorn

from shared.database import get_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Map Service", version="1.0.0")


class MapService:
    """
    Service for downloading and managing USGS map tiles.
    """
    
    def __init__(self):
        self.db = get_database()
        
        # USGS tile server URLs
        self.tile_urls = {
            'satellite': 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile',
            'topo': 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile',
            'hybrid': 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer/tile'
        }
        
        # NYC area bounds for optimization
        self.nyc_bounds = {
            'lat_min': 40.4774,
            'lat_max': 40.9176,
            'lon_min': -74.2591,
            'lon_max': -73.7004
        }
        
        # Rate limiting
        self.max_concurrent_downloads = 8
        self.semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
    
    def lat_lon_to_tile(self, lat: float, lon: float, zoom: int) -> Tuple[int, int]:
        """
        Convert latitude/longitude to tile coordinates.
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            zoom: Zoom level
            
        Returns:
            (x, y) tile coordinates
        """
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y
    
    def tile_to_lat_lon(self, x: int, y: int, zoom: int) -> Tuple[float, float, float, float]:
        """
        Convert tile coordinates to latitude/longitude bounds.
        
        Args:
            x: Tile X coordinate
            y: Tile Y coordinate
            zoom: Zoom level
            
        Returns:
            (lat_min, lon_min, lat_max, lon_max) bounds
        """
        n = 2.0 ** zoom
        lon_min = x / n * 360.0 - 180.0
        lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
        
        lon_max = (x + 1) / n * 360.0 - 180.0
        lat_min = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
        
        return lat_min, lon_min, lat_max, lon_max
    
    def get_tiles_for_area(self, lat_min: float, lon_min: float, 
                          lat_max: float, lon_max: float, 
                          zoom: int) -> List[Tuple[int, int]]:
        """
        Get all tile coordinates needed for a geographic area.
        
        Args:
            lat_min, lon_min, lat_max, lon_max: Bounding box
            zoom: Zoom level
            
        Returns:
            List of (x, y) tile coordinates
        """
        # Get tile coordinates for corners
        x_min, y_max = self.lat_lon_to_tile(lat_min, lon_min, zoom)
        x_max, y_min = self.lat_lon_to_tile(lat_max, lon_max, zoom)
        
        # Generate all tiles in the grid
        tiles = []
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                tiles.append((x, y))
        
        return tiles
    
    def get_tiles_for_route(self, coordinates: List[Tuple[float, float]], 
                           zoom: int, buffer_km: float = 1.0) -> List[Tuple[int, int]]:
        """
        Get tiles needed for a GPS route with buffer.
        
        Args:
            coordinates: List of (lat, lon) coordinates
            zoom: Zoom level
            buffer_km: Buffer distance in kilometers
            
        Returns:
            List of (x, y) tile coordinates
        """
        if not coordinates:
            return []
        
        # Calculate route bounds
        lats = [coord[0] for coord in coordinates]
        lons = [coord[1] for coord in coordinates]
        
        lat_min, lat_max = min(lats), max(lats)
        lon_min, lon_max = min(lons), max(lons)
        
        # Add buffer (approximate)
        lat_buffer = buffer_km / 111.0  # ~111 km per degree latitude
        lon_buffer = buffer_km / (111.0 * math.cos(math.radians((lat_min + lat_max) / 2)))
        
        lat_min -= lat_buffer
        lat_max += lat_buffer
        lon_min -= lon_buffer
        lon_max += lon_buffer
        
        return self.get_tiles_for_area(lat_min, lon_min, lat_max, lon_max, zoom)
    
    async def download_tile(self, x: int, y: int, zoom: int, 
                           map_type: str = 'satellite') -> Optional[bytes]:
        """
        Download a single map tile with caching.
        
        Args:
            x: Tile X coordinate
            y: Tile Y coordinate
            zoom: Zoom level
            map_type: Type of map (satellite, topo, hybrid)
            
        Returns:
            Tile image data as bytes or None if failed
        """
        # Check cache first
        cached_tile = self.db.get_cached_tile(zoom, x, y, map_type)
        if cached_tile:
            logger.debug(f"Retrieved cached tile {map_type}_{zoom}_{x}_{y}")
            return cached_tile
        
        # Download from USGS
        if map_type not in self.tile_urls:
            logger.error(f"Unknown map type: {map_type}")
            return None
        
        url = f"{self.tile_urls[map_type]}/{zoom}/{y}/{x}"
        
        async with self.semaphore:  # Rate limiting
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=30) as response:
                        if response.status == 200:
                            tile_data = await response.read()
                            
                            # Cache the tile
                            self.db.cache_map_tile(zoom, x, y, map_type, tile_data)
                            
                            logger.debug(f"Downloaded tile {map_type}_{zoom}_{x}_{y}")
                            return tile_data
                        else:
                            logger.warning(f"Failed to download tile {url}: HTTP {response.status}")
                            return None
                            
            except Exception as e:
                logger.error(f"Error downloading tile {url}: {e}")
                return None
    
    async def download_tiles_batch(self, tiles: List[Tuple[int, int]], 
                                 zoom: int, map_type: str = 'satellite') -> Dict[Tuple[int, int], bytes]:
        """
        Download multiple tiles concurrently.
        
        Args:
            tiles: List of (x, y) tile coordinates
            zoom: Zoom level
            map_type: Map type
            
        Returns:
            Dictionary mapping (x, y) to tile data
        """
        # Create download tasks
        tasks = []
        for x, y in tiles:
            task = self.download_tile(x, y, zoom, map_type)
            tasks.append(((x, y), task))
        
        # Execute downloads concurrently
        results = {}
        completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for ((x, y), _), result in zip(tasks, completed_tasks):
            if isinstance(result, bytes):
                results[(x, y)] = result
            elif isinstance(result, Exception):
                logger.error(f"Error downloading tile ({x}, {y}): {result}")
        
        logger.info(f"Downloaded {len(results)} of {len(tiles)} tiles")
        return results
    
    def stitch_tiles(self, tiles_data: Dict[Tuple[int, int], bytes], 
                    zoom: int, tile_size: int = 256) -> Optional[Image.Image]:
        """
        Stitch downloaded tiles into a single image.
        
        Args:
            tiles_data: Dictionary mapping (x, y) to tile data
            zoom: Zoom level
            tile_size: Size of individual tiles
            
        Returns:
            Stitched PIL Image or None if failed
        """
        if not tiles_data:
            return None
        
        # Find tile grid bounds
        x_coords = [x for x, y in tiles_data.keys()]
        y_coords = [y for x, y in tiles_data.keys()]
        
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        # Calculate output image size
        width = (x_max - x_min + 1) * tile_size
        height = (y_max - y_min + 1) * tile_size
        
        # Create output image
        stitched = Image.new('RGB', (width, height))
        
        # Place tiles
        for (x, y), tile_data in tiles_data.items():
            try:
                tile_image = Image.open(io.BytesIO(tile_data))
                
                # Calculate position in stitched image
                px = (x - x_min) * tile_size
                py = (y - y_min) * tile_size
                
                stitched.paste(tile_image, (px, py))
                
            except Exception as e:
                logger.error(f"Error processing tile ({x}, {y}): {e}")
        
        return stitched
    
    async def preload_nyc_area(self, zoom_levels: List[int] = [12, 13, 14]):
        """
        Preload NYC metropolitan area tiles for offline use.
        
        Args:
            zoom_levels: List of zoom levels to preload
        """
        logger.info("Starting NYC area preload...")
        
        for zoom in zoom_levels:
            tiles = self.get_tiles_for_area(
                self.nyc_bounds['lat_min'],
                self.nyc_bounds['lon_min'],
                self.nyc_bounds['lat_max'],
                self.nyc_bounds['lon_max'],
                zoom
            )
            
            logger.info(f"Preloading {len(tiles)} tiles at zoom {zoom}")
            
            # Download in batches to avoid overwhelming the server
            batch_size = 50
            for i in range(0, len(tiles), batch_size):
                batch = tiles[i:i + batch_size]
                await self.download_tiles_batch(batch, zoom, 'satellite')
                
                # Small delay between batches
                await asyncio.sleep(1)
        
        logger.info("NYC area preload completed")


# Initialize service
map_service = MapService()


@app.get("/tile/{map_type}/{zoom}/{x}/{y}")
async def get_tile(map_type: str, zoom: int, x: int, y: int):
    """Get a specific map tile."""
    try:
        tile_data = await map_service.download_tile(x, y, zoom, map_type)
        
        if tile_data:
            return Response(content=tile_data, media_type="image/png")
        else:
            raise HTTPException(status_code=404, detail="Tile not found")
            
    except Exception as e:
        logger.error(f"Error retrieving tile {map_type}/{zoom}/{x}/{y}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/download-area")
async def download_area(request: Dict):
    """Download all tiles for a geographic area."""
    try:
        lat_min = request['lat_min']
        lon_min = request['lon_min']
        lat_max = request['lat_max']
        lon_max = request['lon_max']
        zoom = request['zoom']
        map_type = request.get('map_type', 'satellite')
        
        # Get required tiles
        tiles = map_service.get_tiles_for_area(lat_min, lon_min, lat_max, lon_max, zoom)
        
        # Download tiles
        tiles_data = await map_service.download_tiles_batch(tiles, zoom, map_type)
        
        return {
            "status": "success",
            "requested_tiles": len(tiles),
            "downloaded_tiles": len(tiles_data),
            "zoom": zoom,
            "map_type": map_type
        }
        
    except Exception as e:
        logger.error(f"Error downloading area: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/download-route")
async def download_route(request: Dict):
    """Download tiles for a GPS route."""
    try:
        coordinates = request['coordinates']  # List of [lat, lon] pairs
        zoom = request['zoom']
        map_type = request.get('map_type', 'satellite')
        buffer_km = request.get('buffer_km', 1.0)
        
        # Convert to list of tuples
        coords_tuples = [(coord[0], coord[1]) for coord in coordinates]
        
        # Get required tiles
        tiles = map_service.get_tiles_for_route(coords_tuples, zoom, buffer_km)
        
        # Download tiles
        tiles_data = await map_service.download_tiles_batch(tiles, zoom, map_type)
        
        return {
            "status": "success",
            "route_points": len(coordinates),
            "requested_tiles": len(tiles),
            "downloaded_tiles": len(tiles_data),
            "zoom": zoom,
            "map_type": map_type,
            "buffer_km": buffer_km
        }
        
    except Exception as e:
        logger.error(f"Error downloading route tiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/preload-nyc")
async def preload_nyc():
    """Preload NYC area tiles for offline use."""
    try:
        await map_service.preload_nyc_area()
        return {"status": "success", "message": "NYC area preloaded"}
    except Exception as e:
        logger.error(f"Error preloading NYC area: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/cache/cleanup")
async def cleanup_cache(days_old: int = 90):
    """Clean up old cached tiles."""
    try:
        map_service.db.cleanup_old_tiles(days_old)
        return {"status": "success", "message": f"Cleaned up tiles older than {days_old} days"}
    except Exception as e:
        logger.error(f"Error cleaning up cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "map-service"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
