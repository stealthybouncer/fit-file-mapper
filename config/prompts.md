## prompt 1
I'll help you create a comprehensive project for reading FIT files and mapping coordinates on USGS maps with visualizations. First, let me ask you some detailed questions to create a useful README file, then I'll set up the project structure.

## prompt 2
User Requirements Summary:
1. **Language**: Python
2. **Activities**: Primarily running and hiking, some mountain biking and white water rafting. Parse all additional data but start with coordinates. Multi-day workouts supported. Ability to stitch multiple workouts into one visual.
3. **Maps**: Configurable map types, start with satellite, maximum precision, offline capabilities needed
4. **Visualizations**: Route overlays, elevation profiles, heat maps. Start with static images, extend to interactive. Multiple workout overlays on same map. Animation for workout progress.
5. **Geography**: National and state parks, NYC area focus. Automatic map stitching needed.

## Implementation Priorities
1. FIT file parsing with coordinate extraction
2. Satellite map downloading and caching for offline use
3. Basic route overlay visualization
4. Multi-workout stitching functionality
5. Elevation profile generation
6. Heat map creation
7. Interactive map capabilities
8. Animation features

## prompt 3
Additional Requirements:
- **Database**: Use DuckDB for storing parsed workout data
- **Architecture**: Use dev containers and split into separate apps/services as needed
- **Data Storage**: Structured storage for efficient querying and analysis

## prompt 4
Additional Requirements:
- **Package Manager**: Use Astral UV for fast Python package management
- **Dependency Management**: Use pyproject.toml for modern Python project configuration

## prompt 5
optimize the container to use a build and prod baseimage

