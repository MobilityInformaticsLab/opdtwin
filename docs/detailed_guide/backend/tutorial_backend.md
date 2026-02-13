## Backend Layer

In the following we describe what steps are necessary to prepare the input obtained in the previous steps for the visualization in the frontend step.

### SUMO Simulation Module
- **Input**:  
  1. GTFS Static data (.zip) 
  2. Simulation parameters and configuration (.net.xml, .trips.xml, .rou.xml, and .sumocfg etc)
- **Function**:  
  1. Convert and integrate GTFS Static data into the SUMO simulation environment.  
  2. Generate traffic simulation and then output **Floating Car Data** (XML format).
- **Output**: 
  - Floating Car Data (FCD) XML files

**Transform GTFS to SUMO Format**:

In the following we describe how to transform the GTFS data into SUMO format and run the simulation with private vehicle traffic subsequently. Further information about how to integrate GTFS data into SUMO can be found in the [SUMO documentation](https://sumo.dlr.de/docs/Tutorials/GTFS.html)

1. We use GTFS Regional data (GTFS static) from [KoDA](https://www.trafiklab.se/api/our-apis/koda/) as input retrieved in the previous step. We use one hour of data to demonstrate the usability of our pipeline. You can generate longer time periods with no problem.
2. Subsequently, we need to map the GTFS data to the SUMO network. OSM data lacks details such as departure intervals and schedules. GTFS provides these core operational data, which can also solve the possible problems of missing lines or station locations in OSM. Note: make sure the file ```osm_ptlines.xml``` is available before transforming the GTFS data into SUMO format as it includes necessary data for the transformation. The data is obtained from OpenStreetMap (OSM) when downloading the network. Afterwards use the SUMO tool: ```gtfs2pt.py``` to transform the GTFS data into SUMO format:

```
python "D:\Sumo\tools\import\gtfs\gtfs2pt.py" ^
-n <NETWORK FILE> ^
--gtfs <GTFS ZIP FOLDER> ^
--date <SELECTED GTFS DATE> ^
--osm-routes <FILE PATH TO osm_ptlines.xml>" ^
--repair
```
3. After few minutes, the script generates the following files: 
- vtypes.xml
- gtfs_pt_vehicles.add.xml (defining the single public transport vehicles)
- gtfs_pt_stops.add.xml (defining the stops)
- gtfs_missing.xml contains the elements (stops and ptLines) of the GTFS data that could not be imported
- gtfs_repair_errors.txt contains the warnings and errors from the repair of the ptLines

4. These output files allow to run a base simulation with focus on the public transport data. For that create a ```pt_only.sumocfg``` file:
  ```
  <?xml version="1.0" encoding="UTF-8"?>

  <configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">

      <input>
          <net-file value="osm.net.xml.gz"/>
          <additional-files value="vtypes.xml,gtfs_pt_stops.add.xml,gtfs_pt_vehicles.rou.xml,edgeOutputnoise.add.xml,edgeOutputemissions.add.xml,edgeOutputtraffic.add.xml"/>
      </input>

      <time>
          <begin value="28800"/>
          <end value="32400"/>
      </time>

      <processing>
          <ignore-route-errors value="true"/>
      </processing>

      <routing>
          <device.rerouting.adaptation-steps value="18"/>
          <device.rerouting.adaptation-interval value="10"/>
      </routing>

      <output>
          <fcd-output value="fcdOutput.xml"/>
          <fcd-output.geo value="true"/>
      </output>

  </configuration>
  ```
  And execute: ```sumo -c pt_only.sumocfg```

In addtion to the Public Transport data also individual vehicles can be simulated to simulate the interactions with Public Transport. In the following we demonstrate how additional data about the Public Transport and invidual vehicles can be calculated on a edge level. This can inlcude noise, speed and other variables.

**Create Additional Edge-based Outputs**

1. To correctly calculate and output additional edgel-level data such as vehicle speeds or noise, additional files specifying the data to be extracted from the simulation need to be specified. As an example we create one file named ```edgeOutputnoise.add.xml``` to export edge-based noise data:
  ```
  <additional>
   <edgeData id="noise" type="harmonoise" period="10" 
              file="edgeOutputnoise.xml" 
              excludeEmpty="true"/>
  </additional>
```
Besides noise, there are other road level attributes that can be extracted. More details can be found in the [SUMO documentation](https://sumo.dlr.de/docs/Simulation/Output/Lane-_or_Edge-based_Traffic_Measures.html).

6. In addition to the Public transport vehicles, we can co-simulate private cars. For this demonstration we generate random car traffic, if there is calibrated OD demand data available, more realistic scenarios can be specified. We use SUMO's ```randomTrips.py``` tool to generate a random flow of vehicles and create the corresponding config file for SUMO ```pt_and_vehicles.sumocfg``` with the following content, specifying the edge-based output data:

```
<?xml version="1.0" encoding="UTF-8"?>

<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">

    <input>
        <net-file value="osm.net.xml.gz"/>
        <route-files value="random_cars.rou.xml"/>
        <additional-files value="vtypes.xml,gtfs_pt_stops.add.xml,gtfs_pt_vehicles.rou.xml,edgeOutputnoise.add.xml,edgeOutputemissions.add.xml,edgeOutputtraffic.add.xml"/>
    </input>

    <time>
        <begin value="28800"/>
        <end value="32400"/>
    </time>

    <processing>
        <ignore-route-errors value="true"/>
    </processing>

    <routing>
        <device.rerouting.adaptation-steps value="18"/>
        <device.rerouting.adaptation-interval value="10"/>
    </routing>

    <output>
        <fcd-output value="fcdOutput.xml"/>
        <fcd-output.geo value="true"/>
        <emission-output value="VEHICLEOutputnoise.xml"/>
        <edgedata-output value="DEFAULT_EDGEDATA.xml"/>
    </output>

    <report>
        <verbose value="true"/>
        <duration-log.statistics value="true"/>
        <no-step-log value="true"/>
    </report>

    <gui_only>
        <gui-settings-file value="osm.view.xml"/>
    </gui_only>

</configuration>
```

Subsequently, we can run the simulation by executing: ```sumo -c pt_and_vehicles.sumocfg``` and obtain the outputs.

### Floating Car Data Processing Module

This module is responsible for processing the FCD and edge-based outputs into Cesium format to ultimately visualize the simulation outputs in the interactive visualization platform.

- **Input**:  
  - SUMO's XML-formatted floating car, and edge-level data
- **Process**:  
  1. Convert SUMO's XML-formatted floating car, and edge-level data to CSV 
  2. Transform CSV data into **CZML format** for following front-end visualization
- **Output**: 
  - CZML files

**Detailed Steps**:
1. The first step considers the preparation of edge-level data for visualization. For that the edges of the OSM-network need to transformed into GeoJSON and subsequently combined with the data into CZML. SUMO's ```net2geojson``` tool supports directly converting the network into GeoJSON:
  ```
  python "D:\Sumo\tools\net\net2geojson.py" ^
  -n <SUMO_NETWORK> ^
  -o <OUTPUT_GEOJSON>
  ```

2. Next, the XML files containing the edge level data (e.g., ```edgeOutputnoise.xml```) need to be converted into a CSV file (```road_information.csv```) using our custom script ```src/backend/road_xml2csv.py```. This prepares for dynamically displaying road level information in CesiumJS after combining it with the road shape information from the osm network.
In the code, 
  - Input: 
    - Edge-based XML file generated by SUMO (contains `interval` and `edge` nodes, recording road/edge attributes at different timesteps)
    - Optional: Specific edge attributes to extract (e.g., noise, speed, CO2_abs). If omitted, all edge attributes in the XML are automatically detected and used.
  - Output:
    - Complete CSV file: Each row includes `timestep`, `edge ID`, and values of specified/auto-detected attributes (missing edge values for any timestep are filled with 0).
  ```
  python <script_name>.py \
  -i <Path to input SUMO edge-based XML file.> \
  -o <Optional: Path to output CSV file (default: same name as XML with "_edge_matrix.csv" suffix).> \
  -f <Optional: Edge attributes to include (e.g., noise speed fuel_abs CO2_abs), multiple fields separated by spaces.>
  ```

Example execution:
  ```
  python road_xml2csv.py -i edgeOutputnoise.xml -o road_information.csv -f noise
  ```
  3. After that, we can run the custom script ```src/backend/main_trafficinput.py``` to generate CZML files from the generated CSV files. The script generates two CZML files, one for vehicle-level visualization, another for edge-level visualization. During the conversion of vehicles into 3D moving vehicles, we utilize techniques of the work of Beil et al.: https://github.com/tum-gis/sumo-to-czml to visualize their driving direction.

  In the code, 
  - Input: 
    - Vehicle trajectory data（FCD data）generated by SUMO
    - GeoJSON data (road ID, shape, and coordinates system)
    - GLB format models (such as car.glb and tram.glb) 
    - CSV data including timestep, road ID and noise values (converted from edgeOutputnoise.add.xml)
    - CSV data including timestep, vehicle ID, type, vehicle location information (x,y,z),vehicle motion information (slope, angle), noise values
    - Simulation start time (format: YYYY-MM-DD)
    - CurrentTime: Define the position of the cursor on the CesiumJS timeline.
    - Road level attributes: Attributes that want to be visualized, such as the average speed/average noise/ emissions of the road level.
  - Output:
    - CZML file containing vehicle 3D model trajectory, capable of rendering animations in CesiumJS
    - CZML file containing color mapping of road noise for visualizing noise distribution
  ```
  python src/backend/maintraffic_input.py \
  --xml <SUMO FCD (vehicle trajectory) XML file.> \
  --csv <Intermediate/output CSV path for vehicle data (timestep, ID, location, etc.)> \
  --road-csv <Input CSV path for road noise data (timestep, road ID, noise value).> \
  --geojson <Input GeoJSON path for road data (ID, shape, coordinates).> \
  --vehicles-czml <Output CZML path for vehicle 3D trajectory animation.> \
  --roads-czml <Output CZML path for road noise color visualization.>\
  --start-date <Simulation start date (format: YYYY-MM-DD).> \
  --current-time <Initial cursor time on Cesium timeline (seconds since start date).> \
  --road-metric <Road metric column to visualize (e.g., noise, speed, fuel_abs, CO2_abs).> \
  --metric-min <Override metric minimum for color scaling.> \
  --metric-max <Override metric maximum for color scaling> \
  ```

  Example execution:
  ```
  python main_trafficinput.py --xml fcdOutput.xml --csv testwholekista.csv --road-csv road_information.csv --geojson kistaosm.geojson --vehicles-czml czml_3Dmodels_test20250422test.czml --roads-czml kistaroad_noise_visualization.czml --start-date 2025-04-22 --current-time 28800 --road-metric "noise"
  ```


### GTFS Real-time Processing

This part describes how to prepare GTFS real-time data visualization in addition to the offline simulated GTFS data. 

- **Input**:  
  - Protobuf .pb file (GTFS-Realtime vehicle positions)
- **Function**:  
  1. Parse .pb to JSON using google.transit.gtfs_realtime_pb2. 
  2. Extract vehicle coordinates (latitude, longitude) and bearing, dynamically output to CZML format file for visualization
  3. Connecting with CesiumJS frontend to achieve data input and visualization.
- **Output**: 
  - Temporary real-time CZML stream (GTFS real-time data)

**Detailed Steps**:
1. First we need to download the gtfs-realtime.proto file on Google's official link: https://github.com/google/transit/blob/master/gtfs-realtime/proto/gtfs-realtime.proto. This file is required to decode the GTFS real-time data stream encoded as binary data to produce human-readable data.
  ```
  python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ./gtfs-realtime.proto
  ```
  This will generate two Python files for future analyze and process real-time traffic data from GTFS, such as the real-time location and status of buses and metros:
  - gtfs-realtime_pb2.py: Contains the definition of gtfs real-time data structure
  - gtfs-realtime_pb2_grpc.py: Contains code for gRPC services and clients


3. We use a MongoDB to store the real-time data temporary to create a historic data set for future analysis. For that purpose you need to set-up the MongoDB. Please find the connection specifications in ```src/backend/gtfs_flask/app.py```. This code requests the real-time data from the GTFS provider's API. You may adjust the URL and API Key in this file.
5. Then start the MongoDB database service and start the Flask-based streaming service ```src/backend/gtfs_flask/app.py```. 

  ```
    python src/gtfs_flask/app.py --api-key <Your API Key>
  ```
  The main function of this code is to obtain real-time location information of public transportation vehicles and provide visual data. The application continuously retrieves vehicle data (including ID, latitude and longitude, timestamp, etc.) from the KoDa API through backend threads, stores the data in MongoDB, and maintains the historical location information of the vehicle for smooth position interpolation. In addition, the code will convert real-time vehicle data into CZML format (suitable for geographic visualization) and provide it to the front-end through an interface in CesiumJS, supporting viewing real-time vehicle status through web access.
  
  For city APIs without historical real-time data archiving, this method further allows to store all real-time data trajectories for later analysis.

The visualization of this data is explained in the frontend section.



 
  


 


















