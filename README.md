<img width="154" height="53" alt="image" src="https://github.com/user-attachments/assets/6b4d4ef8-81c2-4478-a519-b446a19e0607" />## STIB’s Quality of Service Assessment

# Intro to the Problem

STIB (public transport company in Brussels) operates a complex network of around 650km:
- 4 metro lines
- 17 tram lines
- 55 bus lines
- 11 night bus lines
Everyday it provides transport to 1,2 million people. Given this complexity and relevance, a proper assessment of the quality of the service is important, using relevant techniques and metrics of the world of  public transportation. Given the open data source APIs STIB provides, https://data.stib-mivb.brussels/pages/home/, one can perform the analysis. The analysis was done from the 23th of August 2025 - 15h of September 2025.

The below analysis was done in the spirif of the Data Mining course from the Specialized Master in data science, Big data curcciulum, from ULB.

# 📊 Dataset
**1. GTFS**
- General Transit Feed Specification - Several txt files on schedule, route, stops, trip
- Can change daily, so needs to be queried on each day of the analysis
- **Role in the project:** Provides the planned baseline of the STIB transit network for analysis on headways, route, and stop structure, base for the "shedule arrivals" table
- 
**2. Vehicle Position**
- GEOJSON data - Vehicle position details
- Each API call returns the latest position for every active vehicle, which changes roughly every 20 seconds when on operation
- **Role in the project:** Collects actual vehicle movements to compute headways and operational performance

# 🛠️ Tools
- Python (pandas, numpy, gtfs_kit, ruptures, datetime, pytz, time)
- ML models (DBSCAN, Pelt)

# 🚀 Approach
0. General Thought
The general thought was to perform the analysis for each service day and then do the necessary aggregations. With that in mind, for each iteration of the cycle the plan was:
a. Compute the schedule arrivals table
b. Compute the real arrivals table
c. Compute the headways for each line, direction and stop
d. Build time groups with similar statistical properties based on those headways, and classify each group on punctuality or frequency
e. Compute the metrics of punctuality and frequency for each respective interval by comparing the real and schedule tables.

2. Data Exploration & Pre - Processing
- Combine all the GTFS information (stops, stop_times, lines, calendar, calendar_dates, trips) to obtain the schedule arrivals table
- Cluster stop_ids using an algorithm with DBSCAN with coordinate distance between stops + name fixing. This was necessary since some line + direction would have same stops names with different stop_ids (most likely from a necessity from STIB to be "exact" on where the coordinates of the physical stops are, which are not a necessity for the study at the hand)
Pseudo-code:
*Algorithm “DBSCAN + fix by name”
	All clusters set to -1
	For x cycles: (x chosen as 10)*
  *#First: Cluster Assignment for the stop_ids not assigned
		  For cluster in group by cluster 			
			  If cluster == -1:
				  Eps = 200 if bus, else eps = 250
				  DBSCAN (eps, coordinates of points, metric = geopy_metric)*
  *#SecondFix clusters based on name
		  For cluster in group by cluster:
			  Find first stop_name that appears twice on the cluster
			  Remove all stops from that cluster that do not match that name and reassign them to cluster -1*
- Feature engineering
- Modeling / analysis
- Evaluation

# 📈 Results
- Key insights
- Metrics (accuracy, RMSE, business impact)
- Visuals (screenshots!)

## 🧠 What I Learned
- Technical learnings
- Trade-offs
- What you’d improve next

## ▶️ How to Run
Simple instructions (optional but nice)
