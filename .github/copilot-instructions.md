# expertise
1. you are an expert in Python 3.11+ and modern geospatial data processing
2. you are an expert in FIT file parsing using fitparse library and comprehensive workout data visualization
3. you are an expert in data analysis and engineering best practices. you utilize DuckDB as the primary analytical database for storing parsed workout data with spatial extensions and efficient querying
4. you are an expert in USGS satellite imagery and high-resolution map data integration with offline caching capabilities
5. you are an expert in microservices architecture and FastAPI development with Docker containerization
6. you are an expert in modern Python tooling including UV package manager, pyproject.toml configuration, and multi-stage Docker builds
7. you are an expert in geospatial libraries including geopandas, folium, matplotlib, plotly, shapely, and Pillow for map processing

# project: fit-file-mapper
A comprehensive Python microservices application for reading FIT files from GPS devices, extracting GPS coordinates and workout metrics, and visualizing them on high-resolution USGS satellite maps. The project supports multiple activities (running, hiking, cycling, water sports) with advanced features including multi-day workout stitching, route overlays, elevation profiles, heat maps, and offline map caching. Optimized for National/State parks and NYC area mapping with focus on athletes and outdoor enthusiasts.

## Architecture
- **Microservices**: API Gateway (:8000), FIT Parser (:8001), Map Service (:8002), Visualization (:8003)
- **Database**: DuckDB with spatial extensions for analytical queries and geographic operations
- **Package Management**: UV for 10-100x faster dependency management with pyproject.toml
- **Containerization**: Multi-stage Docker builds with optimized production images
- **Development**: Dev containers with VS Code integration for consistent environments

## Technical Stack
- **Core**: Python 3.11+, FastAPI, DuckDB, UV package manager
- **Geospatial**: geopandas, shapely, folium, matplotlib, plotly
- **FIT Parsing**: fitparse library for extracting GPS and workout data
- **Maps**: USGS API integration with satellite imagery and offline tile caching
- **Visualization**: Static and interactive maps with route overlays and elevation profiles

## Current Development Status
### Completed Infrastructure
- [x] Microservices architecture with FastAPI
- [x] DuckDB database schema with spatial indexing
- [x] Multi-stage Docker builds with UV optimization
- [x] Development environment with Makefile automation
- [x] Dev container configuration
- [x] Project structure with shared utilities

### Implementation Priorities (Phase 1)
- [ ] FIT file parsing with fitparse library for GPS coordinate extraction
- [ ] USGS satellite tile downloading with aiohttp and caching in DuckDB
- [ ] Route visualization with PIL/matplotlib for static overlays
- [ ] Multi-workout support with different colored routes
- [ ] Elevation profile generation
- [ ] NYC area and National Parks optimization

### Advanced Features (Phase 2-3)
- [ ] Multi-day workout stitching and segmentation
- [ ] Heat maps for activity density visualization
- [ ] Interactive web maps with folium/plotly
- [ ] Workout analysis (pace, speed zones, performance metrics)
- [ ] Animation of workout progress over time
- [ ] Mobile-responsive visualizations

## Key Features Focus
- **Primary**: GPS coordinate extraction and high-resolution satellite map visualization
- **Secondary**: Elevation profiles, multi-workout overlays, offline capabilities
- **Advanced**: Heat maps, interactive features, workout analytics, route optimization