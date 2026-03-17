## Input Layer

There are three main types of input data: dynamic traffic data, traffic networks and the built environment. In this section we present how to obtain and process these types of data into the appropriate data structures and formats for the following visualization/analysis steps. 

The examples are based on the selected case study site in Kista, Stockholm. For the public transport data we use the data sources available in Stockholm, Sweden. Accessing and processing the data might look slightly different for other cities in terms of available APIs. We indicate these cases and specify what changes might be required under these circumstances.

### Built Environment

To visualize the built environment in the DT platform we need to download and process the data from the open data platform **[OpenStreetMap](https://www.openstreetmap.org)**. 

1. **Specify Bounding Box**

    For this purpose it is important to specify a bounding box (latitudes and longitudes in OSM) which will be used both for the querying the OSM Building data, but also the trafik network used for the traffic simulation, described later.

    Change the bounding box data in the ```./settings.toml``` under ```osm_settings```.

    ```
    [osm_settings]
    bb_south_long = 59.32
    bb_west_lat = 18.05
    bb_north_long = 59.34
    bb_east_lat = 18.09
    ```

2. **Download Building GeoJSON data**

    Execute the OSM GeoJSON downloader to retrieve the building data for the selected area from OSM.

    ```python src/input/buildings/input_geojson_downloader.py --output data/raw/osm_buildings.geojson```

3. **Transform to CityGML**

    Next we need to transform the GeoJSON data to CityGML to increase interoperability and facilitate the integration into the CESIUM frontend in the later steps.

    ```python src/input/buildings/input_geojson_to_citygml.py --geojson_input data/raw/osm_buildings.geojson --missing_height_imputation average --citygml_output data/processed/osm_buildings.gml```

    In this setting we impute missing height information with the average building height. A default height can be also passed as a float.

4. **Upload to Cesium**

    Next the resulting CityGML data needs to be uploaded to the Cesium Ion platform which provides 3D Tiling. After the upload an Asset ID is generated that later needs to be placed into the frontend component for visualization.


### Traffic Network

To simulate and visualize dynamic traffic data such as Public Transport via GTFS and individual car traffic data, we need to download a suitable network. We again use OSM as a basis to ensure interoperability with the other building blocks.

1. **Download OSM network**

    We download the OSM network with the same bounding boxes as defined above:

    ```python src/input/network/download_osm_network.py --output_folder data/raw/```

    Note: For this step SUMO needs to be installed.

2. **Convert OSM network to SUMO**

    For the later simulation the OSM network needs to be converted into SUMO readable format.

    ```python src/input/network/osm_network_to_sumo.py --input_osm_net data/raw/osm_bbox.osm.xml --output_folder data/raw/```


### Dynamic Traffic Data

#### Public Transport data: GTFS

*The following describes obtaining GTFS data for the case study region of Kista in Stockholm, Sweden. There might be changes necessary to obtain and process the GTFS data from your transport provider.*

1. **Execute GTFS Downloader tool**

    ```python src/input/get_data_from_koda.py --api_key <API_KEY> --date <DATE> --operator <OPERATOR> --download_folder <DOWNLOAD_FOLDER>```

    Data Inputs:
    - API key from [KoDA](https://www.trafiklab.se/api/our-apis/koda/), 
    - Data date and hours (Format: "2025-04-22")
    - Operator (you can find abbreviation for different operators [here](https://www.trafiklab.se/api/gtfs-datasets/gtfs-regional/))
    - Download folder

-----------------------------------------
In the *Backend* section further processing steps for the data are described, necessary for the front-end visualization. We'll also cover the database and some work on the backend framework such as using Node.js and Flask for different visualizations.