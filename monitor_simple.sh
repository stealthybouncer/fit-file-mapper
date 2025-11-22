#!/bin/bash
#
# Simple job monitoring using only curl and jq
# No Python dependencies required
#

SERVICE_URL="${FIT_SERVICE_URL:-http://localhost:8001}"

check_health() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🏥 HEALTH CHECK"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if curl -sf "${SERVICE_URL}/health" > /dev/null 2>&1; then
        echo "✅ Service is healthy"
        return 0
    else
        echo "❌ Service is not available at ${SERVICE_URL}"
        return 1
    fi
}

show_stats() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 DATABASE STATISTICS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if ! curl -sf "${SERVICE_URL}/health" > /dev/null 2>&1; then
        echo "❌ Service is not available"
        return 1
    fi

    curl -s "${SERVICE_URL}/statistics" | jq -r '
        .summary as $s |
        "Total Workouts:  \($s.total_workouts // 0)",
        "Total Distance:  \($s.total_distance_km // 0) km",
        "Total Duration:  \($s.total_duration_hours // 0) hours",
        "Total Calories:  \($s.total_calories // 0)",
        "",
        "Activity Breakdown:"
    '

    curl -s "${SERVICE_URL}/statistics" | jq -r '
        .activity_breakdown | to_entries[] |
        "  • \(.key): \(.value) workouts"
    ' | sort -k3 -rn
}

show_job() {
    local job_id="$1"

    if [[ -z "$job_id" ]]; then
        echo "❌ Job ID required"
        echo "Usage: $0 job JOB_ID"
        return 1
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 BATCH JOB: $job_id"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local response
    response=$(curl -sf "${SERVICE_URL}/parse/batch/${job_id}/status" 2>/dev/null)

    if [[ -z "$response" ]]; then
        echo "❌ Job not found or service unavailable"
        return 1
    fi

    # Parse status
    local status
    status=$(echo "$response" | jq -r '.status // "unknown"')

    case "$status" in
        "pending")   echo "Status: ⏳ PENDING" ;;
        "running")   echo "Status: 🔄 RUNNING" ;;
        "completed") echo "Status: ✅ COMPLETED" ;;
        "failed")    echo "Status: ❌ FAILED" ;;
        "cancelled") echo "Status: 🚫 CANCELLED" ;;
        *)           echo "Status: ❓ UNKNOWN" ;;
    esac

    # Parse counts
    echo "$response" | jq -r '
        "Total Files: \(.total_files // 0)",
        "Processed:   \(.processed // 0)",
        "Successful:  \(.successful // 0)",
        "Failed:      \(.failed // 0)"
    '

    # Calculate and show progress bar
    local total processed
    total=$(echo "$response" | jq -r '.total_files // 0')
    processed=$(echo "$response" | jq -r '.processed // 0')

    if [[ $total -gt 0 ]]; then
        local percent=$((processed * 100 / total))
        local filled=$((percent / 2))
        local empty=$((50 - filled))

        printf "\nProgress: ["
        printf '█%.0s' $(seq 1 $filled)
        printf '░%.0s' $(seq 1 $empty)
        printf "] %d%%\n" $percent
    fi

    # Show timestamps
    echo "$response" | jq -r '
        if .start_time then "\nStart Time: \(.start_time)" else empty end,
        if .end_time then "End Time:   \(.end_time)" else empty end,
        if .duration then "Duration:   \(.duration)s" else empty end
    '

    # Show errors
    local error_count
    error_count=$(echo "$response" | jq '.errors | length')

    if [[ $error_count -gt 0 ]]; then
        echo ""
        echo "⚠️  Recent Errors ($error_count):"
        echo "$response" | jq -r '.errors[-5:] | .[] | "  • \(.file): \(.error)"'
    fi
}

watch_job() {
    local job_id="$1"
    local interval="${2:-5}"

    if [[ -z "$job_id" ]]; then
        echo "❌ Job ID required"
        echo "Usage: $0 watch JOB_ID [INTERVAL]"
        return 1
    fi

    echo "👀 Watching job $job_id (refresh every ${interval}s, Ctrl+C to stop)"
    echo ""

    while true; do
        clear

        if ! curl -sf "${SERVICE_URL}/health" > /dev/null 2>&1; then
            echo "❌ Service is not available at ${SERVICE_URL}"
            sleep "$interval"
            continue
        fi

        show_job "$job_id"

        # Check if job is done
        local status
        status=$(curl -sf "${SERVICE_URL}/parse/batch/${job_id}/status" 2>/dev/null | jq -r '.status // "unknown"')

        if [[ "$status" == "completed" ]] || [[ "$status" == "failed" ]] || [[ "$status" == "cancelled" ]]; then
            echo ""
            echo "✓ Job $status"
            break
        fi

        echo ""
        echo "(Refreshing in ${interval}s...)"
        sleep "$interval"
    done
}

# Main command handler
case "${1:-}" in
    "health")
        check_health
        ;;
    "stats")
        show_stats
        ;;
    "job")
        show_job "$2"
        ;;
    "watch")
        watch_job "$2" "${3:-5}"
        ;;
    *)
        echo "FIT File Job Monitor"
        echo ""
        echo "Usage: $0 COMMAND [OPTIONS]"
        echo ""
        echo "Commands:"
        echo "  health              Check service health"
        echo "  stats               Show database statistics"
        echo "  job JOB_ID          Show job status"
        echo "  watch JOB_ID [SEC]  Watch job with auto-refresh (default 5s)"
        echo ""
        echo "Environment:"
        echo "  FIT_SERVICE_URL     Service URL (default: http://localhost:8001)"
        echo ""
        echo "Examples:"
        echo "  $0 health"
        echo "  $0 stats"
        echo "  $0 job abc123"
        echo "  $0 watch abc123 10"
        exit 1
        ;;
esac
