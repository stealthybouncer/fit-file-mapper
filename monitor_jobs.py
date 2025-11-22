#!/usr/bin/env python3
"""
Job monitoring script for FIT file batch processing.
Provides real-time monitoring of batch job status and progress.
"""

import sys
import time
import requests
from typing import Dict, Any, Optional
from datetime import datetime


class JobMonitor:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()

    def check_service_health(self) -> bool:
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=3)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_statistics(self) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.get(f"{self.base_url}/statistics", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching statistics: {e}")
            return None

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.get(
                f"{self.base_url}/parse/batch/{job_id}/status", timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching job {job_id}: {e}")
            return None

    def format_duration(self, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"

    def format_timestamp(self, timestamp: str) -> str:
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return timestamp

    def display_statistics(self) -> None:
        print("━" * 80)
        print("📊 DATABASE STATISTICS")
        print("━" * 80)

        stats = self.get_statistics()
        if not stats:
            print("❌ Unable to fetch statistics")
            return

        summary = stats.get('summary', {})
        print(f"Total Workouts:  {summary.get('total_workouts', 0):,}")
        print(f"Total Distance:  {summary.get('total_distance_km', 0):,.2f} km")
        print(f"Total Duration:  {summary.get('total_duration_hours', 0):,.2f} hours")
        print(f"Total Calories:  {summary.get('total_calories', 0):,}")

        activities = stats.get('activity_breakdown', {})
        if activities:
            print("\nActivity Breakdown:")
            for activity_type, count in sorted(activities.items(), key=lambda x: x[1], reverse=True):
                print(f"  • {activity_type}: {count:,} workouts")

    def display_job_status(self, job_id: str) -> None:
        print("\n" + "━" * 80)
        print(f"🔄 BATCH JOB: {job_id}")
        print("━" * 80)

        job = self.get_job_status(job_id)
        if not job:
            print("❌ Job not found or unable to fetch status")
            return

        status = job.get('status', 'unknown')
        status_emoji = {
            'pending': '⏳',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '🚫'
        }.get(status, '❓')

        print(f"Status: {status_emoji} {status.upper()}")
        print(f"Total Files: {job.get('total_files', 0):,}")
        print(f"Processed: {job.get('processed', 0):,}")
        print(f"Successful: {job.get('successful', 0):,}")
        print(f"Failed: {job.get('failed', 0):,}")

        if job.get('total_files', 0) > 0:
            progress = (job.get('processed', 0) / job.get('total_files', 1)) * 100
            bar_length = 50
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f"\nProgress: [{bar}] {progress:.1f}%")

        if job.get('start_time'):
            print(f"\nStart Time: {self.format_timestamp(job['start_time'])}")

        if job.get('end_time'):
            print(f"End Time: {self.format_timestamp(job['end_time'])}")

        if job.get('duration'):
            print(f"Duration: {self.format_duration(job['duration'])}")

        errors = job.get('errors', [])
        if errors:
            print(f"\n⚠️  Recent Errors ({len(errors)}):")
            for error in errors[-5:]:
                print(f"  • {error.get('file', 'unknown')}: {error.get('error', 'unknown error')}")

    def watch_job(self, job_id: str, interval: int = 5) -> None:
        print(f"👀 Watching job {job_id} (refresh every {interval}s, Ctrl+C to stop)")

        try:
            while True:
                print("\033[2J\033[H")  # Clear screen

                if not self.check_service_health():
                    print("❌ Service is not available at", self.base_url)
                    time.sleep(interval)
                    continue

                self.display_job_status(job_id)

                job = self.get_job_status(job_id)
                if job and job.get('status') in ['completed', 'failed', 'cancelled']:
                    print(f"\n✓ Job {job.get('status')}")
                    break

                print(f"\n(Refreshing in {interval}s...)")
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped")

    def list_active_jobs(self) -> None:
        print("━" * 80)
        print("📋 ACTIVE JOBS")
        print("━" * 80)
        print("\nNote: This endpoint would need to be implemented in the service.")
        print("Currently, you need to track job IDs from when you submit them.")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Monitor FIT file batch processing jobs"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8001",
        help="Base URL of FIT parser service"
    )
    parser.add_argument(
        "command",
        choices=["health", "stats", "job", "watch"],
        help="Command to run"
    )
    parser.add_argument(
        "job_id",
        nargs="?",
        help="Job ID (required for 'job' and 'watch' commands)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Refresh interval in seconds for watch mode"
    )

    args = parser.parse_args()

    monitor = JobMonitor(args.url)

    if args.command == "health":
        if monitor.check_service_health():
            print("✅ Service is healthy")
            sys.exit(0)
        else:
            print(f"❌ Service is not available at {args.url}")
            sys.exit(1)

    elif args.command == "stats":
        if not monitor.check_service_health():
            print(f"❌ Service is not available at {args.url}")
            sys.exit(1)
        monitor.display_statistics()

    elif args.command == "job":
        if not args.job_id:
            print("❌ Job ID is required for 'job' command")
            sys.exit(1)

        if not monitor.check_service_health():
            print(f"❌ Service is not available at {args.url}")
            sys.exit(1)

        monitor.display_job_status(args.job_id)

    elif args.command == "watch":
        if not args.job_id:
            print("❌ Job ID is required for 'watch' command")
            sys.exit(1)

        if not monitor.check_service_health():
            print(f"❌ Service is not available at {args.url}")
            sys.exit(1)

        monitor.watch_job(args.job_id, args.interval)


if __name__ == "__main__":
    main()
