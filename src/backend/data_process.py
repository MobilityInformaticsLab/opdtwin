import csv
import os
from datetime import datetime
import pytz

# --- Configuration ---
# IMPORTANT: Update this to the correct path of your existing CSV file
INPUT_CSV_PATH = r"F:\postgresql\data\koda_downloads_sl_20250422\test\koda_downloads_sl_20250422_hourly\vehicle_positions_2025-04-22.csv" # Current file with UTC timestamps

# Define the output path for the processed file
# It's good to indicate the changes in the filename
OUTPUT_CSV_PATH = r"F:\postgresql\data\koda_downloads_sl_20250422\test\koda_downloads_sl_20250422_hourly\vehicle_positions_2025-04-22_SwedenTime_Deduplicated.csv"

# Define the target timezone
SWEDISH_TIMEZONE = pytz.timezone('Europe/Stockholm')

# Column name for the timestamp
TIMESTAMP_COLUMN = 'timestamp'
# Original FIELD_NAMES from your script (ensure this matches your CSV header)
# This list is crucial for maintaining column order and for creating the hashable tuple for deduplication.
FIELD_NAMES = [
    'vehicle_id', 'vehicle_label', 'license_plate',
    'trip_id', 'route_id', 'direction_id', 'start_time', 'start_date',
    'latitude', 'longitude', 'bearing', 'speed', 'odometer',
    'current_stop_sequence', 'stop_id', 'current_status',
    'timestamp', 'congestion_level', 'occupancy_status', 'multi_carriage'
]
# --- End Configuration ---

def convert_utc_to_swedish_time(utc_timestamp_str):
    """
    Converts a UTC timestamp string to a Swedish local time string.
    Returns None if parsing fails.
    """
    if not utc_timestamp_str:
        return None
    try:
        # 1. Parse the UTC timestamp string to a naive datetime object
        #    Assuming the format from your original script: '%Y-%m-%d %H:%M:%S'
        dt_naive_utc = datetime.strptime(utc_timestamp_str, '%Y-%m-%d %H:%M:%S')

        # 2. Make the naive datetime object timezone-aware (assign UTC)
        dt_aware_utc = pytz.utc.localize(dt_naive_utc)

        # 3. Convert to Swedish timezone
        dt_swedish = dt_aware_utc.astimezone(SWEDISH_TIMEZONE)

        # 4. Format back to string
        return dt_swedish.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        # Handle cases where the timestamp string might not be in the expected format
        print(f"Warning: Could not parse timestamp: {utc_timestamp_str}")
        return utc_timestamp_str # Or return None, or raise error, depending on desired handling


def process_csv_file(input_filepath, output_filepath, field_names, timestamp_col_name):
    """
    Reads a CSV file, converts timestamps, removes duplicates, and writes to a new CSV.
    """
    seen_rows_hashes = set()  # Store hashes of rows to detect duplicates
    original_row_count = 0
    written_row_count = 0
    skipped_duplicates_count = 0
    header_checked = False

    print(f"Starting processing of: {input_filepath}")
    print(f"Output will be saved to: {output_filepath}")

    try:
        with open(input_filepath, 'r', newline='', encoding='utf-8') as infile, \
             open(output_filepath, 'w', newline='', encoding='utf-8') as outfile:

            reader = csv.DictReader(infile)
            writer = csv.DictWriter(outfile, fieldnames=field_names) # Use predefined field_names for consistent order

            # Check header integrity
            if reader.fieldnames is None :
                 print("Error: Could not read header from input CSV. File might be empty or malformed.")
                 return

            if set(reader.fieldnames) != set(field_names):
                print("Warning: CSV header mismatch!")
                print(f"  Expected columns (set): {set(field_names)}")
                print(f"  Actual columns in CSV (set): {set(reader.fieldnames)}")
                print("  Will proceed using the column order defined in FIELD_NAMES for writing.")
                # If critical columns are missing, you might want to stop execution here.
                if timestamp_col_name not in reader.fieldnames:
                    print(f"Error: Critical timestamp column '{timestamp_col_name}' not found in CSV header.")
                    return

            writer.writeheader()

            for row_dict in reader:
                original_row_count += 1

                # 1. Convert timestamp
                if timestamp_col_name in row_dict:
                    original_utc_time_str = row_dict[timestamp_col_name]
                    swedish_time_str = convert_utc_to_swedish_time(original_utc_time_str)
                    row_dict[timestamp_col_name] = swedish_time_str if swedish_time_str is not None else original_utc_time_str
                else:
                    print(f"Warning: Timestamp column '{timestamp_col_name}' not found in row: {row_dict}")


                # 2. Prepare row for deduplication check
                #    Create a tuple of values in the order of FIELD_NAMES for consistent hashing
                #    Handle potential missing keys gracefully by using row_dict.get(col, '')
                try:
                    row_values_tuple = tuple(row_dict.get(col, '') for col in field_names)
                except Exception as e:
                    print(f"Error creating tuple from row {original_row_count}: {row_dict}. Error: {e}")
                    print("Skipping this row due to error.")
                    continue


                # 3. Check for duplicates and write if unique
                #    Using hash(row_values_tuple) can be more memory-efficient for the set
                #    if the tuples themselves are very long, but direct tuple storage is fine.
                if row_values_tuple not in seen_rows_hashes:
                    seen_rows_hashes.add(row_values_tuple)
                    try:
                        # Ensure all data in row_dict is suitable for writerow
                        # (e.g., DictWriter expects a dict where keys match its fieldnames)
                        writer.writerow({k: row_dict.get(k, '') for k in field_names})
                        written_row_count += 1
                    except Exception as e:
                         print(f"Error writing row {original_row_count} to output: {row_dict}. Error: {e}")

                else:
                    skipped_duplicates_count += 1

                if original_row_count % 500000 == 0: # Log progress
                    print(f"  Processed: {original_row_count} rows | Written: {written_row_count} unique rows | Skipped: {skipped_duplicates_count} duplicates")

        print("\nProcessing completed.")
        print(f"  Total original rows read: {original_row_count}")
        print(f"  Total unique rows written: {written_row_count}")
        print(f"  Total duplicate rows skipped: {skipped_duplicates_count}")

    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_filepath}'")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Basic check if the input file exists
    if not os.path.exists(INPUT_CSV_PATH):
        print(f"FATAL ERROR: Input CSV file not found: {INPUT_CSV_PATH}")
    else:
        process_csv_file(INPUT_CSV_PATH, OUTPUT_CSV_PATH, FIELD_NAMES, TIMESTAMP_COLUMN)
