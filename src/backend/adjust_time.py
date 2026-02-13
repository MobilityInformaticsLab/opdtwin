input_file = r'F:\postgresql\data\koda_downloads_sl_20250422\sl_gtfs_static_2025-04-22\stop_times.txt'
output_file = r'F:\postgresql\data\koda_downloads_sl_20250422\sl_gtfs_static_2025-04-22\stop_times_fixed.txt'

with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
    header = infile.readline()
    outfile.write(header)
    for line in infile:
        parts = line.strip().split(',')
        # The second and third columns are time columns
        for i in [1, 2]:
            time_str = parts[i]
            hours, minutes, seconds = map(int, time_str.split(':'))
            if hours >= 24:
                hours = hours - 24
                # Ensure that the number of hours is filled to two digits from 0
                new_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                parts[i] = new_time_str

        new_line = ','.join(parts) + '\n'
        outfile.write(new_line)