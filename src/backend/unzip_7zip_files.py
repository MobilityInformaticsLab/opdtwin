import os
import py7zr

# Target folder path
target_folder = r'F:\postgresql\data\koda_downloads_sl_20250422\test\koda_downloads_sl_20250422_hourly\sl_gtfs-rt_VehiclePositions_2025-04-22'
os.makedirs(target_folder, exist_ok=True)  # Create target folder

for filename in os.listdir(r'F:\postgresql\data\koda_downloads_sl_20250422\test\koda_downloads_sl_20250422_hourly'):
    if filename.endswith('.7z'):
        file_path = os.path.join(r'F:\postgresql\data\koda_downloads_sl_20250422\test\koda_downloads_sl_20250422_hourly', filename)
        with py7zr.SevenZipFile(file_path, 'r') as archive:
            # Traverse the files inside the compressed file
            for file_name, file_obj in archive.readall().items():
                if file_name.endswith('.pb'):
                    # Extract the. pb file to the target folder
                    output_file_path = os.path.join(target_folder, os.path.basename(file_name))
                    with open(output_file_path, 'wb') as f:
                        f.write(file_obj.read())

print("The operation is complete, and all. pb files have been merged into the target folder.")