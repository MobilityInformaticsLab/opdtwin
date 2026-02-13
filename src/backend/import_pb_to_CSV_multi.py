from gtfs_realtime_pb2 import FeedMessage
import csv
import os
import time
import glob

# Enumeration mapping dictionary (defined according to gtfs elevation. pro)
STATUS_MAP = {0: "INCOMING_AT", 1: "STOPPED_AT", 2: "IN_TRANSIT_TO"}
CONGESTION_MAP = {0: "UNKNOWN", 1: "RUNNING_SMOOTHLY", 2: "STOP_AND_GO", 
                 3: "CONGESTION", 4: "SEVERE_CONGESTION"}
OCCUPANCY_MAP = {0: "EMPTY", 1: "MANY_SEATS_AVAILABLE", 2: "FEW_SEATS_AVAILABLE",
                 3: "STANDING_ROOM_ONLY", 4: "CRUSHED_STANDING_ROOM_ONLY", 5: "FULL"}

# CSV field order (uniformly defined globally
FIELD_NAMES = [
    'vehicle_id', 'vehicle_label', 'license_plate',
    'trip_id', 'route_id', 'direction_id', 'start_time', 'start_date',
    'latitude', 'longitude', 'bearing', 'speed', 'odometer',
    'current_stop_sequence', 'stop_id', 'current_status',
    'timestamp', 'congestion_level', 'occupancy_status', 'multi_carriage'
]

def parse_vehicle_positions(file_path):
    """Analyze a single. pb file"""
    feed = FeedMessage()
    with open(file_path, 'rb') as f:
        feed.ParseFromString(f.read())
    
    records = []
    for entity in feed.entity:
        if not entity.HasField('vehicle'):
            continue
        
        v = entity.vehicle
        record = {}

        # Vehicle information
        record['vehicle_id'] = v.vehicle.id if v.HasField('vehicle') else ''
        record['vehicle_label'] = v.vehicle.label if (v.HasField('vehicle') and v.vehicle.HasField('label')) else ''
        record['license_plate'] = v.vehicle.license_plate if (v.HasField('vehicle') and v.vehicle.HasField('license_plate')) else ''

        # Travel information
        trip = v.trip if v.HasField('trip') else None
        record['trip_id'] = trip.trip_id if (trip and trip.HasField('trip_id')) else ''
        record['route_id'] = trip.route_id if (trip and trip.HasField('route_id')) else ''
        record['direction_id'] = trip.direction_id if (trip and trip.HasField('direction_id')) else ''
        record['start_time'] = trip.start_time if (trip and trip.HasField('start_time')) else ''
        record['start_date'] = trip.start_date if (trip and trip.HasField('start_date')) else ''

        # Position information
        pos = v.position if v.HasField('position') else None
        record['latitude'] = pos.latitude if pos else None
        record['longitude'] = pos.longitude if pos else None
        record['bearing'] = pos.bearing if (pos and pos.HasField('bearing')) else None
        record['speed'] = pos.speed if (pos and pos.HasField('speed')) else None
        record['odometer'] = pos.odometer if (pos and pos.HasField('odometer')) else None

        # Other information
        record['current_stop_sequence'] = v.current_stop_sequence if v.HasField('current_stop_sequence') else ''
        record['stop_id'] = v.stop_id if v.HasField('stop_id') else ''
        record['current_status'] = STATUS_MAP.get(v.current_status, 'UNKNOWN') if v.HasField('current_status') else ''
        record['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(v.timestamp)) if v.HasField('timestamp') else '' #This line converts a Unix timestamp (v.timestamp) into a UTC (GMT) string. So in Sweden， we need to adjust this data.
        record['congestion_level'] = CONGESTION_MAP.get(v.congestion_level, 'UNKNOWN') if v.HasField('congestion_level') else ''
        record['occupancy_status'] = OCCUPANCY_MAP.get(v.occupancy_status, 'UNKNOWN') if v.HasField('occupancy_status') else ''

        # Multi carriage information
        if v.multi_carriage_details:
            carriages = [f"id:{c.id},status:{OCCUPANCY_MAP.get(c.occupancy_status, 'UNKNOWN')}" 
                        for c in v.multi_carriage_details]
            record['multi_carriage'] = '; '.join(carriages)
        else:
            record['multi_carriage'] = ''

        records.append(record)
    
    return records

def process_directory(input_dir, output_path):
    """Process. pb files for the entire directory"""
    # Retrieve all. pb files (sorted by file name)
    pb_files = sorted(glob.glob(os.path.join(input_dir, '*.pb')))
    if not pb_files:
        print(".pb file not found")
        return

    # Initialize CSV file
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
        writer.writeheader()

    total_files = len(pb_files)
    total_records = 0

    for idx, pb_file in enumerate(pb_files, 1):
        try:
            records = parse_vehicle_positions(pb_file)
            with open(output_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
                writer.writerows(records)
            
            total_records += len(records)
            print(f"progress: {idx}/{total_files} | Current: {os.path.basename(pb_file)} | adding record: {len(records)}")
        except Exception as e:
            print(f"fail: {os.path.basename(pb_file)} | error {str(e)}")

    print(f"\nProcessing completed！Total number of files: {total_files} | Total number of records: {total_records}")

if __name__ == "__main__":
    # configure paths
    input_directory = r"F:\postgresql\data\koda_downloads_sl_20250422\test\koda_downloads_sl_20250422_hourly\sl_gtfs-rt_VehiclePositions_2025-04-22"
    output_csv = os.path.join(os.path.dirname(input_directory), "vehicle_positions_2025-04-22.csv")

    process_directory(input_directory, output_csv)