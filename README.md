# 🚍 Open Public Transport Digital Twin (OPDTwin) 

Despite its practical potential, the current adoptation of Digital Twins (DT) in the transportation domain and especially in Public Transport (PT) is relatively slow. A significant barrier is the substantial effort and investment in resources required during the development phase, especially for informative visualizations, thus limiting its accessibility to PT agencies. 

Thus, we propose an automated development pipeline of DT for PT, which uses open-source software and data that make it easy to access and extend. 

## Overview

This is a summary of a tutorial that can help you quickly understand our overall technology pipeline. If you want to get started developing a DT instance for yourself, please refer to our more detailed documentation.

The goal of our DT development pipeline is building an open-source digital twin model for urban public transportation system. Technically, there are some key issues that need to be addressed.

- How to represent physical objects (road, buildings, land etc.) as the 3D digital twin objects? 
- How to visualize vehicle (buses, trains, etc) movements and corresponding effects such as emissions, congestion, noise, etc.?
- How to integrate the traffic outputs into the digital twin platform?

This tutorial will introduce how we addressed the three aspects from above: building data, vehicles/roads data, and the digital twin platform.
     
**Overview of the development pipeline:**
![[pipeline]](docs/_static/DT-Pipeline-Overview.png)


## Building Data
### Overview
The basic idea is to obtain a three-dimensional model from OSM data. The process begins with downloading building data from Open Street Map (find more info in section [Built Environment](docs/source/detailed_guide/input/tutorial_input.md#built-environment)). After obtaining the GeoJSON data of the buildings, it needs to be converted into CityGML (3D data).

Subsequently the CityGML data is transformed into 3D Tiles for efficient visualization in the Cesium platform. We directly used Cesium ION's cloud storage function and loaded the Cesium.JS frontend using a Node.js server (find more info in section [Building Visualization](docs/source/detailed_guide/frontend/tutorial_frontend.md#nodejs-module-cesium-integration--czml-visualization)).

**Visualization of the obtained 3D Buildings in Cesium:**
[![Watch the PT DT video](docs/source/_static/optdtwin_video_thumbnail.png)](https://kth-my.sharepoint.com/:v:/g/personal/jostmann_ug_kth_se/Eex8tEcl6WpPrr5cjA7GvP8BTn5I4ueavzloHjAcWWlXkQ?e=g6EUJ9)

## Vehicle Data
### Overview
While GTFS static provides data about public transport schedules, GTFS real-time provides historical and real-time public transport trajectories. Typically public transport agencies provide APIs to query both types of data if available. In our case, we obtained the data from the Koda API for regional GTFS data in Sweden. 

For predictive cases, such as noise/emission/congestion visualization, and to simulate the public transports' interaction with other vehicles. The basic idea is to use SUMO to parse the GTFS Static timetable, and then output the result as floating car and aggregated data. In this way, vehicle simulation data can be dynamically or statically visualized at any time interval (find more info in section [SUMO simulation](docs/source/detailed_guide/backend/tutorial_backend.md#sumo-simulation-module)). In this case, we use noise visualization as an example, in fact, you can use the same approach and method to visualize many other aspects, such as average speed, emissions, and so on. You can find information on the [SUMO Website: Output](https://sumo.dlr.de/docs/Simulation/Output/index.html). Specifically, you can focus on these two chapters: vehicle-based information, disaggregated, and values for edges or lanes. Meanwhile, if you have your own model, you can also perform secondary development on SUMO.


For GTFS Realtime data, we have two main operations. The first focus is on historical GTFS real-time data, which can lay the foundation for many future historical data analyses. The second is the real-time data, and we mainly use the MongoDB + Flask technology stack for its efficient data processing. The processing details of historical real-time data are still ongoing work (find more info in section [Real Time GTFS Data Processing](docs/source/detailed_guide/backend/tutorial_backend.md#flask-backend-module-gtfs-real-time-processing)). The basic idea for visualizing the GTFS data is to use Flask to obtain the location of the vehicle and store it in MongoDB, converting it into a CZML file in real-time for display. MongoDB has excellent support for unstructured real-time data streams. 

## Digital Twin Platform
### CesiumJS
CesiumJS is the core of our DT visualization platform. We chose this web-based platform because cross platform access is relatively simple, and it also has scalability and flexibility.

We need to visualize the building environment and vehicle trajectories, and Cesium supports both aspects very well:
- For vehicle trajectories, Cesium provides the Cesium Language (CZML), an open data format designed to represent dynamic geospatial objects and their changes over time. CZML is a JSON-based schema and file format that allows the description of time-varying geospatial data and graphical scenes. This lays the foundation for us to develop different user cases in the future, which means good scalability. In a word, we can visualize most of the spatio-temporal data through this.
- For building environment, CityGML data, derived from OSM building data, serves as the 3D model representation standard due to its extendability and compatibility with other DT pipelines.

### Server Framework
Currently, using Node.js + Express + SUMO (visit section [nodejs-backend-module-cesium-integration--czml-visualization](docs/source/detailed_guide/frontend/tutorial_frontend.md#nodejs-module-cesium-integration--czml-visualization)) or Flask + MongoDB (visit [flask-backend-module-gtfs-real-time-processing](docs/source/detailed_guide/backend/tutorial_backend.md#flask-backend-module-gtfs-real-time-processing)), it can host front-end static resources containing CesiumJS, as well as provide back-end data interfaces for CesiumJS, thus supporting complete CesiumJS DT platform.

