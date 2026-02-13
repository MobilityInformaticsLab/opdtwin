# Overview

This project provides a development pipeline for the construction of an open-source digital twin platform for urban public transportation using open source software (e.g., SUMO and Cesium), as well as open data and data standards (e.g., OSM, GTFS, CityGML). The platform is able to visualize simulation results from SUMO, GTFS historical real-time and current real-time trajectories within an OSM-based 3D built environment in the Cesium platform.

This documentation breaks down each step with code examples and screenshots.

![[overview_3D]](../_static/overview_3D.png)

## Technology Pipeline Overview
One of the core points we want to share in this tutorial is how to establish **a public transportation digital twin platform using open source data and methods**. With this architecture we deliver the basis for further developments to ensure efficient integration of diverse data sources and software components for future use cases.

In this documentation we introduce the workflow from data input to processing and visualization. Before that, we will provide an overview of the technology pipeline, including the system architecture, module functions, and their interactions across different stages (input, processing, and output). As for the specific and detailed steps, we will introduce them later in subsequent sections. 

![DT Pipeline Overview](../_static/DT-Pipeline-Overview.svg)


---
## Use Cases
The scenarios can be broadly categorized along a temporal dimension into back-casting, now-casting, and forecasting, each of which offers distinct benefits to different stakeholders.

### Retrospective Analysis
Back-casting through this platform refers to analyzing past traffic patterns and behaviors based on the current situation and using this method to understand the performance of the transportation network under different conditions.

### Now-casting
Now-casting is the prediction and analysis of current and near real time traffic conditions based on real-time traffic data. This is critical for instant decision-making and response.

### Forecasting
Forecasting uses long-term data trends to predict future traffic conditions, helping city planners and policymakers with long-term planning. SUMO serves a tool to simulate scenarios, involving changed network layouts, changes in demand or PT schedules.


