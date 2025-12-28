<img width="145" height="88" alt="image" src="https://github.com/user-attachments/assets/ed1268c0-e195-4eba-baa8-afb4156898e5" /># STIB’s Quality of Service Assessment

## Intro to the Problem

STIB (public transport company in Brussels) operates a complex network of around 650km:
- 4 metro lines
- 17 tram lines
- 55 bus lines
- 11 night bus lines
Everyday it provides transport to 1,2 million people. Given this complexity and relevance, a proper assessment of the quality of the service is important, using relevant techniques and metrics of the world of  public transportation. Given the open data source APIs STIB provides, https://data.stib-mivb.brussels/pages/home/, one can perform the analysis.

The below analysis was done in the spirif of the Data Mining course from the Specialized Master in data science, Big data curcciulum, from ULB.

## 📊 Dataset
# GTFS
-General Transit Feed Specification - Several txt files on schedule, route, stops, trip
-Can change daily, so needs to be queried on each day of the analysis
-**Role in the project:** Provides the planned baseline of the STIB transit network for analysis on headways, route, and stop structure, base for the "shedule arrivals" table
# Vehicle Position
-GEOJSON data - Vehicle position details
-Each API call returns the latest position for every active vehicle, which changes roughly every 20 seconds when on operation
-**Role in the project:**Collects actual vehicle movements to compute headways and operational performance

## 🛠️ Tools & Skills
- Python (pandas, scikit-learn)
- SQL
- Visualization (Matplotlib / Seaborn / Power BI)
- ML models (if any)

## 🚀 Approach
- Data cleaning
- EDA
- Feature engineering
- Modeling / analysis
- Evaluation

## 📈 Results
- Key insights
- Metrics (accuracy, RMSE, business impact)
- Visuals (screenshots!)

## 🧠 What I Learned
- Technical learnings
- Trade-offs
- What you’d improve next

## ▶️ How to Run
Simple instructions (optional but nice)
