## Frontend Layer

In the following we will describe the visualization component of the PT DT development pipeline.

### GTFS Simulation visualization
We selected Node.js as a backend framework for the visualzation platform. This JavaScript backend allows CesiumJS to be ran locally.

- **Input**:  
  1. OSM building data (GeoJSON/CityGML) - CesiumJS 3D Building Service.
  2. CZML files (from SUMO simulations or historical real-time data).
  3. CesiumJS requests for visualization.

- **Function**:   
  1. 3D Building Service
    - Serve OSM buildings as 3D tiles. When uploading CityGML, calling data through Cesium ion will convert it directly into 3D Tiles format.
  2. CZML Visualization
    - Both SUMO's simulation results based on GTFS static data and the visualization of trajectory data from GTFS historical real-time data can be achieved through CMZL format

- **Output**: 
  1. 3D buildings' visualization in CesiumJS
  2. Visualization of dynamic vehicles in CZML format in CesiumJS（SUMO simulation and historical real-time data

**Detailed Steps**:
1. Install Node.Js
2. Initialize the project to generate the package.JSON file.
  ```
  cd src\frontend\server
  npm init -y 
  ```
4. We need to install some common libraries to support GTFS data parsing in this folder.
  ```
  npm install express node-fetch gtfs-realtime-bindings 
  npm install cesium@^1.68.0 compression@^1.7.4 express@^4.17.1 heatmap.js@^2.0.5
  ```
  
5. Afterwards, there are mainly three files that are responsible for the the web-based visualization.
  - ```src/frontend/server/server.js```: Express server

  - ```src/frontend/server/Public/index.html```: Main Page
    - Provide HTML skeleton and create a full screen container (cesiumContainer) for rendering the 3D Cesium maps
    - Introduce CesiumJS library and its style sheets for 3D geographic visualization.
    - Load custom script loadCesium.js to handle map data loading and interaction logic.

  - ```src/frontend/server/Public/loadCesium.js```: 
    - Initialize CesiumJS map view, configure base map and controls.
    - Load and integrate multiple data:
      - CZML format data: includes 3D models (such as vehicles) and edge-level data
      - Cesium ion asset: Load 3D models of Kista (buildings, etc.) from the Cesium platform
    - ***It is important that you need to enter your own Cesium API key in the first line.***
    ```
    Cesium.Ion.defaultAccessToken = '';// Your API Key
    ```
    
6. Before the visualization, we need to prepare for the vehicles, roads and buildings data. In ```src/frontend/server/Public/loadCesium.js```, we can specify which data we want to import. The first step is to paste the two CZML files into the ```Public``` folder.

7. For buildings visualization, you need to apply for an API key in Cesium Ion and upload the former CityGML files into it to get an IonAssetId. You can fill the API key and also change the value of IonAssetId in ```src/frontend/server/Public/loadCesium.js```. 
8. Then run the Node.js server: `node server.js` and navigate to [http://localhost:3000/](http://localhost:3000/) to see the visualization
  ![[node_visulization_bus]](../../_static/node_visualization_bus.png)


### Real-time GTFS data visualization

We developed a seperate visualization script to visualize the streamed and historic real-time GTFS data.

1. The files for this visualization are located under ```src/backend/gtfs_flask/static```. Similar to the simulation data visualiztion described above you need to adjust a few inputs in the ```index.html```: 
  - add the API Key to Cesium Ion 
  - add Cesium object ID
2. Then as described in the backend section of this documentation start the MongoDB server, run the ```src/backend/gtfs_flask/app.py``` to retrieve the GTFS data from the API, and open the ```index.html`` located in ```src/backend/gtfs_flask/static/index.html```
3. As a result you will see the real-time positions of the Public Transport vehicles in the Cesium-based visualization:
  ![[flask_simple_result]](../../_static/flask_simple_result.png)
  In the picture, real-time buses are displayed. The textual information records the IDs and timestamps of buses. If you want to end this process, you can directly use the control+c command line interface for [app.py](../../../../src/backend/gtfs_flask/app.py), and then close the database using the same way.
  ![[flask_working]](../../_static/flask_working.png)


