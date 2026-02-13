import psycopg2
import random
import json
from datetime import datetime
from decimal import Decimal

# Database Connect Information
DB_PARAMS = {
    'dbname': 'gtfs_db',
    'user': 'postgres',
    'password': 'your_password',
    'host': 'localhost',
    'port': '5432'
}

# Define possible values for occupancy_status
OCCUPANCY_STATUS = [
    'Unknown', 'Empty', 'Many seats available', 'Few seats available',
    'Standing room only', 'Crushed standing room only',
    'Full', 'Not accepting passengers'
]

# Define the distance threshold (in meters) for determining the arrival of a vehicle at a station
STOP_DISTANCE_THRESHOLD = 10

def create_line_197_table():
    """
    Create a new table for Line 197 vehicle using CTAS
    """
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # Check if the source table exists
        check_source_table_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'gtfs_realtime_vehicle_positions_20250422'
            )
        """
        cursor.execute(check_source_table_query)
        source_table_exists = cursor.fetchone()[0]
        
        if not source_table_exists:
            print("Error: The source table 'gtfs_realtime_vehicle_positions_20250422' does not exist")
            conn.close()
            return False
        
        # SQL for creating tables
        create_table_query = """
            CREATE TABLE IF NOT EXISTS line_197_positions_2025_04_22 AS
            SELECT 
                vph.id,
                vph.trip_id,
                vph.vehicle_id,
                vph.license_plate,
                vph.speed,
                vph.bearing,
                vph.latitude,
                vph.longitude,
                vph.occupancy_status,
                vph.sweden_timestamp,
                vph.geom,
                t.route_id,
                r.route_short_name
            FROM gtfs_realtime_vehicle_positions_20250422 vph
            JOIN trips t ON vph.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE r.route_short_name = '197';
        """
        cursor.execute(create_table_query)
        
        # Verify if the table was successfully created
        check_table_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'line_197_positions_2025_04_22'
            )
        """
        cursor.execute(check_table_query)
        table_created = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if table_created:
            print("The creation of line 197 vehicle list has been successful")
            return True
        else:
            print("The table was not successfully created, there may be permission issues or query errors")
            return False
            
    except (Exception, psycopg2.Error) as error:
        print(f"Error creating table: {error}")
        # Rollback transactions when exceptions occur
        if conn:
            conn.rollback()
            conn.close()
        return False

def update_occupancy_status():
    """
    Update occupancy_status value based on spatial distance calculation
    """
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # Check if the target table exists
        check_table_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'line_197_positions_2025_04_22'
            )
        """
        cursor.execute(check_table_query)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("Error: Table 'line_197_positions_2025_04_22' does not exist, unable to update occupancy_status")
            conn.close()
            return False
        
        # Retrieve the vehicle trajectory data for the specified trip_id and calculate the distance to the nearest station
        #Revised SQL (UTM 33N, EPSG: 32633, returns meters)
        select_query = """
            SELECT 
                id,
                vehicle_id,  -- vehicle ID
                sweden_timestamp, 
                geom,
                (
                    SELECT MIN(
                        ST_Distance(
                            ST_Transform(s.geom, 32633),  -- Station to UTM 33N
                            ST_Transform(vph.geom, 32633)   -- Vehicle to UTM 33N
                        )
                    ) 
                    FROM stops s 
                    JOIN stop_times st ON s.stop_id = st.stop_id 
                    WHERE st.trip_id = vph.trip_id
                ) AS min_distance_meters  -- Clearly define the unit
            FROM line_197_positions_2025_04_22 vph
            WHERE vph.trip_id = %s
            ORDER BY sweden_timestamp;
        """
        cursor.execute(select_query, ('14010000674263674',))
        # records = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        records = [dict(zip(columns, row)) for row in cursor.fetchall()]

        if not records:
            print("No record found for the specified trip_id")
            conn.close()
            return False
        
        # Define possible values for occupancy_status
        OCCUPANCY_STATUS = [
            'Empty', 'Many seats available', 'Few seats available',
            'Standing room only', 'Crushed standing room only',
            'Full', 'Not accepting passengers'
        ]
        
        current_occupancy = random.choice(OCCUPANCY_STATUS) 
        last_near_stop = False  # Record whether the previous location is near the station
        
        for record in records:
            record_id = record['id']
            min_distance = record['min_distance_meters']
            is_near_stop = min_distance <= STOP_DISTANCE_THRESHOLD if min_distance is not None else False
            print(f"Record ID: {record_id}, Min Distance: {min_distance}, Near Stop: {is_near_stop}, Current Occupancy: {current_occupancy}")

            # if is_near_stop != last_near_stop:
            #     current_occupancy = random.choice(OCCUPANCY_STATUS)

            # Update status only when leaving the site (core modifications)
            if last_near_stop and not is_near_stop:
                current_occupancy = random.choice(OCCUPANCY_STATUS)
                print(f"vehicle {record['vehicle_id']} leaving the site, status updated to: {current_occupancy}")
            
            last_near_stop = is_near_stop
            
            update_query = """
                UPDATE line_197_positions_2025_04_22
                SET occupancy_status = %s
                WHERE id = %s;
            """
            cursor.execute(update_query, (current_occupancy, record_id))

        conn.commit()
        cursor.close()
        conn.close()
        print("occupancy_status update completed")
        return True
    except (Exception, psycopg2.Error) as error:
        print(f"Error updating occupancy_status: {error}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def get_processed_data():
    """
    Retrieve processed data from the new table
    """
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # Check if the target table exists
        check_table_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'line_197_positions_2025_04_22'
            )
        """
        cursor.execute(check_table_query)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            error_msg = "Error: Table 'line_197_positions_2025_04_22' does not exist"
            print(error_msg)
            conn.close()
            raise Exception(error_msg)
        
        # Add projection conversion (consistent with update function)
        query = """
            SELECT 
                vph.*,
                (
                    SELECT MIN(
                        ST_Distance(
                            ST_Transform(s.geom, 32633), 
                            ST_Transform(vph.geom, 32633)
                        )
                    ) 
                    FROM stops s 
                    JOIN stop_times st ON s.stop_id = st.stop_id 
                    WHERE st.trip_id = vph.trip_id
                ) AS distance_to_stop_meters  -- Clearly define the unit
            FROM line_197_positions_2025_04_22 vph
            WHERE vph.trip_id = '14010000674263674'
            ORDER BY sweden_timestamp;
        """
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
          # Convert Decimal type to float
        data = []
        for row in cursor.fetchall():
            converted_row = []
            for value in row:
                if isinstance(value, Decimal):
                    converted_row.append(float(value))
                else:
                    converted_row.append(value)
            data.append(dict(zip(columns, converted_row)))
        
        cursor.close()
        conn.close()
        
        if not data:
            print("Warning: Query returns empty result set")
        
        return data
    except (Exception, psycopg2.Error) as error:
        print(f"Error occurred while obtaining processed data: {error}")
        if conn:
            conn.close()
        return []

def create_czml(data):
    if not data:
        print("Error: No data available for generating CZML")
        return []
    
    # Group data by vehicle_id
    vehicle_groups = {}
    for row in data:
        vehicle_id = row['vehicle_id']
        if vehicle_id not in vehicle_groups:
            vehicle_groups[vehicle_id] = []
        vehicle_groups[vehicle_id].append(row)
    
    # Document level configuration
    czml = [
        {
            "id": "document",
            "name": "GTFS Vehicle Positions",
            "version": "1.0",
            "clock": {
                "interval": get_global_interval(data),  # This function needs to be implemented
                "currentTime": get_global_interval(data).split('/')[0],
                "multiplier": 1,
                "range": "LOOP_STOP",
                "step": "SYSTEM_CLOCK_MULTIPLIER"
            }
        }
    ]
    
    occupancy_colors = {
        'Empty': [0, 255, 0, 255],
        'Many seats available': [144, 238, 144, 255],
        'Few seats available': [255, 255, 0, 255],
        'Standing room only': [255, 165, 0, 255],
        'Crushed standing room only': [255, 69, 0, 255],
        'Full': [255, 0, 0, 255],
        'Not accepting passengers': [128, 0, 128, 255],
        'Unknown': [255, 255, 255, 255]
    }
    
    # Create dynamic entities for each vehicle
    for vehicle_id, records in vehicle_groups.items():
        # Sort records (ensure they are in chronological order)
        records.sort(key=lambda x: x['sweden_timestamp'])
        
        # Build a time series of locations
        position_values = []
        for record in records:
            timestamp = record['sweden_timestamp']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            timestamp_str = timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
            lon = float(record['longitude'])
            lat = float(record['latitude'])
            position_values.extend([timestamp_str, lon, lat, 0])
        
        # Building a color time series
        color_values = []
        for record in records:
            timestamp = record['sweden_timestamp']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            timestamp_str = timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            occupancy = record['occupancy_status']
            if occupancy is None:
                occupancy = 'Unknown'
            color = occupancy_colors.get(occupancy, [255, 255, 255, 255])
            color_values.extend([timestamp_str] + color)
        
        # Create vehicle entity
        vehicle_czml = {
            "id": f"vehicle_{vehicle_id}",
            "name": f"Vehicle {vehicle_id}",
            "availability": get_vehicle_interval(records),  # This function needs to be implemented
            "position": {
                "interpolationAlgorithm": "LAGRANGE",
                "interpolationDegree": 5,
                "referenceFrame": "FIXED",
                "cartographicDegrees": position_values
            },
            "point": {
                "color": {
                    "interpolationAlgorithm": "STEP",
                    "rgba": color_values
                },
                "pixelSize": 10,
                "outlineColor": {
                    "rgba": [0, 0, 0, 255]
                },
                "outlineWidth": 2
            },
            "description": f"<p><strong>Vehicle ID:</strong> {vehicle_id}</p>" # we can add more such as occupancy rate or speed
        }
        
        # Add path visualization
        vehicle_czml["path"] = {
            "material": {
                "solidColor": {
                    "color": {
                        "rgba": [0, 0, 255, 100]
                    }
                }
            },
            "width": 3,
            "resolution": 60,
            "leadTime": 0,
            "trailTime": 3600
        }
        
        czml.append(vehicle_czml)
    
    return czml 

# Auxiliary function: Calculate global time range
def get_global_interval(data):
    if not data:
        return "2025-01-01T00:00:00Z/2025-01-01T01:00:00Z"
    
    timestamps = []
    for row in data:
        ts = row['sweden_timestamp']
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        timestamps.append(ts)
    
    min_ts = min(timestamps).strftime('%Y-%m-%dT%H:%M:%SZ')
    max_ts = max(timestamps).strftime('%Y-%m-%dT%H:%M:%SZ')
    return f"{min_ts}/{max_ts}"

# Auxiliary function: Calculate the time range of a single vehicle
def get_vehicle_interval(records):
    if not records:
        return "2025-01-01T00:00:00Z/2025-01-01T01:00:00Z"
    
    timestamps = []
    for record in records:
        ts = record['sweden_timestamp']
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        timestamps.append(ts)
    
    min_ts = min(timestamps).strftime('%Y-%m-%dT%H:%M:%SZ')
    max_ts = max(timestamps).strftime('%Y-%m-%dT%H:%M:%SZ')
    return f"{min_ts}/{max_ts}"

def main():
    # Create line 197 vehicle schedule
    table_created = create_line_197_table()
    
    if not table_created:
        print("Program termination: Table creation failed")
        return
    
    # Update occupancy_status value (based on spatial distance calculation)
    rate_updated = update_occupancy_status()
    
    if not rate_updated:
        print("Program termination: occupancy_status update failed")
        return
    
    # Retrieve processed data from the new table
    processed_data = get_processed_data()
    
    if processed_data:
        # Generate CZML data
        czml_data = create_czml(processed_data)
        
        if czml_data:
            # Save CZML file
            try:
                with open('gtfs_vehicle_positions.czml', 'w') as f:
                    json.dump(czml_data, f, indent=2)
                print("CZML file generated successfully")
            except Exception as e:
                print(f"Error saving CZML file: {e}")
        else:
            print("No valid CZML data was generated")
    else:
        print("Unable to generate CZML file as processed data not found")

if __name__ == "__main__":
    main()