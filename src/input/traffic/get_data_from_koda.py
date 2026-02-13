import requests
import time
import os
import sys
import argparse

# Historical Real-time data download settings
REALTIME_FEEDS = ["VehiclePositions"]
HOURS_TO_DOWNLOAD = list(range(0, 24))  # Download for all hours 00 through 23
POLL_INTERVAL_SECONDS = 120  # Time between polls for HTTP 202
MAX_POLLING_RETRIES = 60  # Max attempts for polling per hour
REQUEST_DELAY_SECONDS = 15  # Shorter delay between hourly requests is acceptable

# API Base URLs
STATIC_BASE_URL = "https://api.koda.trafiklab.se/KoDa/api/v2/gtfs-static/"
REALTIME_BASE_URL = "https://api.koda.trafiklab.se/KoDa/api/v2/gtfs-rt/"


def download_gtfs_static(api_key, operator, date, download_dir):
    """Downloads historical GTFS static data."""
    endpoint = f"{STATIC_BASE_URL}{operator}"
    params = {"date": date, "key": api_key}
    filename = f"{operator}_gtfs_static_{date}.zip"
    filepath = os.path.join(download_dir, filename)

    print(f"--- Downloading Static Data ---")
    print(f"Requesting: {endpoint} with date={date}")

    try:
        # Increased timeout for potentially larger static files too
        response = requests.get(endpoint, params=params, stream=True, timeout=120)
        response.raise_for_status()

        if response.status_code == 200:
            print(f"Status: {response.status_code} OK. Saving to {filepath}...")
            os.makedirs(download_dir, exist_ok=True)
            with open(filepath, "wb") as f:
                # Use a larger chunk size for potentially large static files
                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):  # 1MB chunks
                    f.write(chunk)
            print(f"Static data download complete: {filepath}\n")
            return True
        else:
            # This case is less likely now due to raise_for_status()
            print(f"Received unexpected status code: {response.status_code}")
            print(f"Response text: {response.text[:500]}...\n")
            return False

    except requests.exceptions.Timeout:
        print(f"Error: The request for static data timed out.\n")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred for static data: {e}")
        # Check if response object exists before accessing text
        if response:
            print(f"Response text: {response.text[:500]}...\n")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Network error occurred during static data request: {e}\n")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during static download: {e}\n")
        return False


def download_gtfs_realtime_hourly(
    api_key, operator, feed, date, hour, download_dir, poll_interval=30, max_retries=20
):
    """Downloads historical GTFS real-time data for a specific hour, handling HTTP 202."""
    endpoint = f"{REALTIME_BASE_URL}{operator}/{feed}"
    params = {"date": date, "hour": hour, "key": api_key}  # Include hour parameter
    # Ensure hour is formatted with leading zero if needed (e.g., H01, H10)
    filename = f"{operator}_gtfs-rt_{feed}_{date}_H{hour:02d}.7z"
    filepath = os.path.join(download_dir, filename)

    print(f"--- Downloading Real-time: {feed} | Date: {date} | Hour: {hour:02d} ---")
    print(f"Requesting: {endpoint} with params: {params}")  # Show params in log

    retries = 0
    while retries < max_retries:
        # Check if file already exists (useful for resuming interrupted downloads)
        if os.path.exists(filepath):
            print(f"File already exists: {filepath}. Skipping download.")
            return True

        try:
            # Increased timeout per request, as even hourly data might take time
            response = requests.get(endpoint, params=params, stream=True, timeout=600)

            if response.status_code == 200:
                print(f"Status: 200 OK. Saving to {filepath}...")
                os.makedirs(download_dir, exist_ok=True)
                try:
                    with open(filepath, "wb") as f:
                        # Use a larger chunk size for potentially large hourly files too
                        for chunk in response.iter_content(
                            chunk_size=5 * 1024 * 1024
                        ):  # 5MB chunks
                            f.write(chunk)
                    print(f"Download complete: {filepath}\n")
                    return True
                except Exception as e_write:
                    print(f"Error writing file {filepath}: {e_write}. Cleaning up.")
                    if os.path.exists(filepath):
                        os.remove(filepath)  # Remove partially written file on error
                    return False

            elif response.status_code == 202:
                retries += 1
                print(
                    f"Status: 202 Accepted. Waiting {poll_interval}s... (Attempt {retries}/{max_retries})"
                )
                # Add a small buffer to sleep time
                time.sleep(poll_interval + 0.5)
                continue

            else:
                # This will catch 4xx/5xx errors
                response.raise_for_status()

        except requests.exceptions.Timeout:
            print(
                f"Error: Request timed out for hour {hour:02d} (Attempt {retries+1}/{max_retries}). Moving to next hour/feed."
            )
            # Don't retry on timeout for this specific hour, just report and fail for this hour
            return False
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred for hour {hour:02d}: {e}")
            # Check if response object exists before accessing text
            if response:
                print(f"Response text: {response.text[:500]}...\n")
            return False
        except requests.exceptions.RequestException as e:
            # Includes connection errors, etc. Might be worth retrying, but for simplicity now we fail for the hour.
            print(f"Network error occurred for hour {hour:02d}: {e}\n")
            return False
        except Exception as e:
            print(f"An unexpected error occurred for hour {hour:02d}: {e}\n")
            return False

    print(
        f"Failed to download real-time data for {feed} at hour {hour:02d} after {max_retries} retries (persistent 202 or error).\n"
    )
    return False


# --- Main Execution ---

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--api_key", help="")
    parser.add_argument("--operator", help="")
    parser.add_argument("--date", help="")
    parser.add_argument("--download_folder", help="")
    args = parser.parse_args()

    print("Starting KoDa Data Download Process (Hourly Real-time)...")
    print(f"Operator: {args.operator}")
    print(f"Date: {args.date}")
    print(f"Download Directory: {args.download_folder}")
    print("-" * 40)

    # Create download directory if it doesn't exist
    os.makedirs(args.download_folder, exist_ok=True)

    # 1. Download Static Data
    static_filename = f"{args.operator}_gtfs_static_{args.date}.zip"
    static_filepath = os.path.join(args.download_folder, static_filename)
    if os.path.exists(static_filepath):
        print(f"Static data file already exists: {static_filepath}. Skipping download.")
        static_success = True
    else:
        static_success = download_gtfs_static(
            args.api_key, args.operator, args.date, args.download_folder
        )

    if not static_success:
        print("Static data download failed. Check API key and parameters.")
        # Optionally exit if static data is essential
        # sys.exit(1)

    print("-" * 40)
    print("Starting Real-time Data Downloads (Hour-by-Hour)...")

    # 2. Download Real-time Data Feeds (Hourly)
    total_rt_tasks = len(REALTIME_FEEDS) * len(HOURS_TO_DOWNLOAD)
    rt_success_count = 0
    rt_failed_tasks = []

    for feed in REALTIME_FEEDS:
        print(f"\n>>> Processing Feed: {feed} <<<")
        for hour in HOURS_TO_DOWNLOAD:
            filename = f"{args.operator}_gtfs-rt_{feed}_{args.date}_H{hour:02d}.7z"
            filepath = os.path.join(args.download_folder, filename)
            if os.path.exists(filepath):
                print(
                    f"Real-time data file already exists: {filepath}. Skipping download."
                )
                success = True
            else:
                success = download_gtfs_realtime_hourly(
                    args.api_key,
                    args.operator,
                    feed,
                    args.date,
                    hour,  # Pass the specific hour
                    args.download_folder,
                    poll_interval=POLL_INTERVAL_SECONDS,
                    max_retries=MAX_POLLING_RETRIES,
                )
            if success:
                rt_success_count += 1
            else:
                rt_failed_tasks.append(f"{feed}_H{hour:02d}")

            # Add a small delay between hourly requests to be courteous to the API
            time.sleep(REQUEST_DELAY_SECONDS)

    print("-" * 40)
    print("KoDa Data Download Process Finished.")
    print(f"Static data download status: {'Success' if static_success else 'Failed'}")
    print(f"Real-time hourly downloads attempted: {total_rt_tasks}")
    print(f"Real-time hourly downloads successful: {rt_success_count}")
    print(f"Real-time hourly downloads failed: {len(rt_failed_tasks)}")

    if rt_failed_tasks:
        print(f"Failed tasks: {', '.join(rt_failed_tasks)}")
        sys.exit(1)  # Exit with error code if any real-time download failed
    elif not static_success:
        sys.exit(1)  # Exit with error code if static download failed
    else:
        sys.exit(0)  # Exit normally
