#!/bin/bash

SERVICE_URL="http://localhost:8001"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 FIT Parser Service Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if service is running
if ! curl -s -f "${SERVICE_URL}/health" > /dev/null 2>&1; then
    echo "❌ Service is not running at ${SERVICE_URL}"
    echo ""
    echo "Start it with:"
    echo "  cd .devcontainer && docker compose up -d fit-parser-service"
    exit 1
fi

echo "✅ Service is healthy"
echo ""

# Get overall statistics
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Database Statistics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "${SERVICE_URL}/statistics" | jq -r '
  "Total Workouts: \(.summary.total_workouts // 0)",
  "Total Distance: \(.summary.total_distance_km // 0) km",
  "Total Duration: \(.summary.total_duration_hours // 0) hours",
  "Total Calories: \(.summary.total_calories // 0)",
  "",
  "Activity Breakdown:"
' 2>/dev/null

curl -s "${SERVICE_URL}/statistics" | jq -r '
  .activity_breakdown | to_entries[] |
  "  - \(.key): \(.value) workouts"
' 2>/dev/null || echo "  No data yet"

echo ""

# Check for active batch jobs (by checking service stats endpoint)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 Recent Activity"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "${SERVICE_URL}/stats" | jq -r '
  "Service: \(.service)",
  "Status: \(.status)",
  "Total Activities: \(.statistics.total_activities)"
' 2>/dev/null

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To check a specific batch job:"
echo "  curl http://localhost:8001/parse/batch/JOB_ID/status | jq '.'"
echo ""
echo "To start a new import:"
echo "  ./import_fits.sh"
echo ""
