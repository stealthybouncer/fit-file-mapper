# FIT File Mapper

A Python application for reading FIT (Flexible and Interoperable Data Transfer) files from GPS devices and mapping workout coordinates on USGS maps with advanced visualization capabilities.

## Project Overview

This project aims to:
- Parse FIT files from running, hiking, mountain biking, and water sports activities
- Extract GPS coordinates, elevation, and comprehensive workout metrics
- Overlay workout routes on high-precision satellite maps with offline capabilities
- Generate static visualizations with automatic map stitching for multi-day and long routes
- Support multiple workout overlays and comparative analysis with heat maps
- Focus on National/State parks and NYC area with precise mapping
- Enable workout stitching to combine multiple activities into unified visualizations

## Features (Implementation Priority)

### Phase 1: Core Functionality
- **FIT File Parsing**: Extract GPS coordinates and basic metrics from all activity types
- **Satellite Map Integration**: Download and cache high-resolution satellite tiles for offline use
- **Route Visualization**: Overlay single and multiple workout routes on maps
- **Automatic Map Stitching**: Seamlessly combine map tiles for long routes and multi-day activities

### Phase 2: Advanced Visualizations
- **Elevation Profiles**: Generate detailed elevation charts with route correlation
- **Heat Maps**: Show activity density and frequently used routes
- **Multi-workout Overlays**: Display multiple activities on the same map for comparison
- **Workout Stitching**: Combine separate FIT files into unified route visualizations

### Phase 3: Interactive Features
- **Interactive Maps**: Convert static visualizations to interactive web maps
- **Animation**: Show workout progress over time with playback controls
- **Advanced Analytics**: Speed zones, performance metrics, route optimization

## Features (Planned)

### Core Functionality
- **FIT File Parsing**: Read and extract data from FIT files using fitparse library
- **GPS Data Processing**: Clean and process GPS coordinates, elevation, timestamps
- **USGS Map Integration**: Download and cache USGS map tiles
- **Route Visualization**: Overlay workout routes on topographic maps
- **Map Stitching**: Automatically combine multiple map tiles for long routes
- **Multi-workout Support**: Display multiple workouts on the same map

### Data Extraction
- GPS coordinates (latitude, longitude) - **PRIMARY FOCUS**
- Elevation profiles
- Timestamps and duration
- Speed and pace data
- Heart rate (if available)
- Cadence (for cycling/running)
- Power data (for cycling)
- Activity type detection (running, hiking, biking, water sports)
- Multi-day workout support
- Workout segmentation and merging capabilities

### Visualization Options
- Static map images (PNG, PDF)
- Interactive HTML maps
- Elevation profiles
- Speed/pace charts
- Heat maps for frequently used routes
- 3D terrain visualization
- Animation of workout progress

### Map Features
- USGS topographic maps
- **High-resolution satellite imagery** (primary focus)
- Hybrid satellite/topographic overlays
- **Offline map caching** for field use
- Contour lines and elevation data
- Trail and road overlays
- Custom styling and color schemes
- **National/State parks optimization**
- **NYC area high-precision mapping**

## Technical Stack

### Programming Language
- **Python 3.9+** (preferred for geospatial libraries)

### Key Libraries (To Be Confirmed)
- **fitparse**: FIT file parsing
- **folium**: Interactive maps
- **geopandas**: Geospatial data manipulation
- **matplotlib**: Static plotting
- **plotly**: Interactive visualizations
- **requests**: USGS API integration
- **Pillow**: Image processing for map stitching
- **numpy/pandas**: Data manipulation

### APIs and Data Sources
- USGS National Map API
- USGS Elevation Point Query Service
- OpenStreetMap (if needed)

## Project Structure

```
fit-file-mapper/
├── .devcontainer/             # Dev container configuration
├── services/                  # Microservices architecture
│   ├── api-gateway/          # Central API gateway (port 8000)
│   ├── fit-parser/           # FIT file parsing service (port 8001)
│   ├── map-service/          # Map downloading and caching (port 8002)
│   └── visualization/        # Visualization generation (port 8003)
├── shared/                   # Shared utilities and database
│   ├── __init__.py
│   └── database.py           # DuckDB database operations
├── src/                      # Legacy/standalone modules
│   ├── __init__.py
│   ├── fit_parser.py         # FIT file reading and parsing
│   ├── gps_processor.py      # GPS data cleaning and processing
│   ├── map_downloader.py     # USGS map tile downloading
│   ├── map_stitcher.py       # Map tile combination logic
│   └── visualizer.py         # Route visualization on maps
├── data/
│   ├── fit_files/            # Input FIT files
│   ├── maps/                 # Downloaded map tiles cache
│   └── processed/            # Processed GPS data
├── database/                 # DuckDB database files
├── output/                   # Generated visualizations
├── tests/                    # Unit tests
├── docs/                     # Documentation
├── config/                   # Configuration files
├── pyproject.toml           # Modern Python project configuration
├── uv.lock                  # UV lock file for reproducible builds
├── Makefile                 # Development workflow automation
└── README.md                # This file
```

## Architecture

The project uses a **microservices architecture** with the following components:

### Services
- **API Gateway** (`:8000`): Central REST API for all operations
- **FIT Parser Service** (`:8001`): Processes FIT files and extracts GPS data
- **Map Service** (`:8002`): Downloads and caches USGS satellite tiles
- **Visualization Service** (`:8003`): Creates route overlays and visualizations

### Database
- **DuckDB**: High-performance analytical database for workout data
- **Structured storage** for GPS points, workout metadata, and map tiles
- **Optimized queries** for geographic and temporal analysis

### Package Management
- **UV**: Lightning-fast Python package manager
- **pyproject.toml**: Modern dependency management
- **Lock files**: Reproducible builds across environments

## Installation and Setup

### Prerequisites
- Python 3.11 or higher
- [UV package manager](https://github.com/astral-sh/uv) (recommended for fastest installs)
- Docker and Docker Compose (for containerized development)
- Git

### Quick Start with UV (Recommended)

1. **Install UV package manager:**
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Clone and setup the project:**
   ```bash
   git clone <repository-url>
   cd fit-file-mapper
   
   # Create virtual environment and install dependencies
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e ".[dev,all]"
   ```

3. **Start development environment:**
   ```bash
   make quick-start
   ```

### Alternative Installation (pip)
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install from pyproject.toml
pip install -e ".[dev,all]"
```

### Development with Dev Containers

For the most consistent development experience:

1. **Open in VS Code with Dev Containers extension**
2. **Reopen in Container** when prompted
3. **All dependencies will be automatically installed with UV**

## Usage Examples

### Quick Start
```bash
# Start all services
make services-up

# Visit API documentation
open http://localhost:8000/docs

# Upload a FIT file via curl
curl -X POST "http://localhost:8000/api/upload-fit" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@data/fit_files/your_workout.fit"
```

### API Usage
```python
import requests

# Upload FIT file
with open('workout.fit', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/upload-fit',
        files={'file': f}
    )
    workout_data = response.json()
    workout_id = workout_data['workout_id']

# Create single workout visualization
viz_response = requests.post(
    f'http://localhost:8000/api/visualize/single-workout/{workout_id}',
    json={
        'options': {
            'map_type': 'satellite',
            'zoom': 16,
            'include_elevation_profile': True
        }
    }
)

# Create multi-workout overlay
multi_viz = requests.post(
    'http://localhost:8000/api/visualize/multi-workout',
    json={
        'workout_ids': [workout_id1, workout_id2, workout_id3],
        'options': {
            'map_type': 'satellite',
            'auto_colors': True
        }
    }
)
```

### Direct Module Usage (Legacy)
```python
from src.fit_parser import FITParser
from src.visualizer import MapVisualizer
from shared.database import get_database

# Parse FIT file and store in database
parser = FITParser()
parsed_data = parser.parse_fit_file('workout.fit')

db = get_database()
workout_id = db.insert_workout(parsed_data['metadata'])
db.insert_gps_points(workout_id, parsed_data['gps_data'])

# Create visualization
visualizer = MapVisualizer()
map_image = visualizer.create_route_overlay(
    coordinates=parsed_data['coordinates'],
    map_image=base_map,
    map_bounds=bounds
)
```

### Development Workflow
```bash
# Setup development environment
make dev-setup

# Run tests
make test

# Format code
make format

# Check code quality
make check

# View service logs
make services-logs

# Stop services
make services-down
```

## Configuration

### Map Settings
- Default map type (topographic, satellite, hybrid)
- Map resolution and zoom levels
- Cache settings for downloaded tiles
- Output image quality and format

### Data Processing
- GPS smoothing algorithms
- Elevation correction methods
- Speed calculation parameters
- Data filtering options

## Development Guidelines

### Code Style
- Follow PEP 8 Python style guidelines
- Use type hints for function parameters and returns
- Comprehensive docstrings for all functions and classes
- Unit tests for all major functionality

### Git Workflow
- Feature branches for new functionality
- Descriptive commit messages
- Pull request reviews for major changes

## API Documentation

### FIT File Structure
- Record types and data fields
- Timestamp handling
- Coordinate system conversions
- Error handling for corrupted files

### USGS Map Integration
- Tile server endpoints
- Coordinate projection systems
- Map scale and resolution options
- Rate limiting and caching strategies

## Testing Strategy

### Unit Tests
- FIT file parsing accuracy
- GPS data processing algorithms
- Map tile downloading and caching
- Visualization output validation

### Integration Tests
- End-to-end workflow testing
- Multiple file format support
- Performance benchmarks
- Memory usage optimization

## Known Limitations and Considerations

### FIT File Compatibility
- Device-specific data field variations
- Firmware version differences
- Corrupted file handling

### Map Data Limitations
- USGS tile availability and coverage
- Download rate limits
- Offline usage requirements
- Copyright and attribution requirements

### Performance Considerations
- Large file processing optimization
- Memory management for long routes
- Map tile caching strategies
- Parallel processing opportunities

## Future Enhancements

### Advanced Features
- GPX file format support
- Real-time GPS tracking integration
- Route planning and optimization
- Social sharing capabilities
- Mobile app development

### Machine Learning Integration
- Route difficulty prediction
- Performance analysis and trends
- Anomaly detection in GPS data
- Automated route categorization

## Contributing

### How to Contribute
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

### Development Setup
- Pre-commit hooks for code quality
- Continuous integration pipeline
- Documentation generation
- Code coverage reporting

## License

[To be determined - consider MIT, Apache 2.0, or GPL depending on requirements]

## Support and Documentation

### Resources
- FIT SDK documentation
- USGS API documentation
- Geospatial Python tutorials
- Example FIT files for testing

### Contact Information
[To be added]

---

**Note**: This README serves as a comprehensive guide for GitHub Copilot to understand the project structure, goals, and technical requirements. Update sections as the project evolves and requirements are clarified.