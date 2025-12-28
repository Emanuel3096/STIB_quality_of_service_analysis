Below is your text **re-formatted in clean Markdown**, with **English corrected and coherence improved**, while **keeping your original structure, tone, and intent**. I did **not** change the analytical logic or make it more “marketing-like”.

You can paste this directly into GitHub.

---

## STIB’s Quality of Service Assessment

### Introduction to the Problem

STIB (the public transport company of Brussels) operates a complex network of approximately **650 km**, composed of:

* **4 metro lines**
* **17 tram lines**
* **55 bus lines**
* **11 night bus lines**

Every day, the network transports around **1.2 million passengers**. Given this scale, complexity, and societal importance, a proper assessment of service quality is crucial, using established **public transportation metrics and analytical techniques**.

Thanks to the **open data APIs provided by STIB**
👉 [https://data.stib-mivb.brussels/pages/home/](https://data.stib-mivb.brussels/pages/home/)

it is possible to perform such an analysis.

This study covers the period from **August 23rd, 2025 to September 15th, 2025**.

The analysis was carried out in the spirit of the **Data Mining course** from the **Specialized Master in Data Science – Big Data curriculum (ULB)**.

---

## 📊 Dataset

### 1. GTFS (General Transit Feed Specification)

* Collection of text files describing:

  * schedules
  * routes
  * stops
  * trips
* The GTFS data can change **daily**, and therefore needs to be queried **for each day of the analysis**.
* **Role in the project:**
  Provides the *planned baseline* of the STIB transit network.
  It is used to compute:

  * scheduled arrivals
  * headways
  * route and stop structures

  This dataset serves as the foundation for the **scheduled arrivals table**.

---

### 2. Vehicle Position

* **GEOJSON** data containing real-time vehicle position information.
* Each API call returns the **latest position of every active vehicle**, updated approximately every **20 seconds** during operations.
* **Role in the project:**
  Captures *actual vehicle movements*, allowing the computation of:

  * real arrivals
  * observed headways
  * operational performance metrics

---

## 🛠️ Tools

* **Python**: `pandas`, `numpy`, `gtfs_kit`, `ruptures`, `datetime`, `pytz`, `time`
* **ML / Statistical Models**:

  * DBSCAN
  * PELT (change-point detection)

---

## 🚀 Approach

### 0. General Approach

The analysis was performed **per service day**, followed by the necessary aggregations across days.

For each daily iteration, the workflow was as follows:

1. Compute the **scheduled arrivals table**
2. Compute the **real arrivals table**
3. Compute **headways** for each:

   * line
   * direction
   * stop
4. Identify **time intervals with similar statistical properties** based on headways, and classify each interval in terms of:

   * punctuality
   * frequency
5. Compute punctuality and frequency metrics by comparing **scheduled vs. real arrivals** for each interval

---

### 1. Data Exploration & Pre-Processing

#### GTFS Processing

* All GTFS components (`stops`, `stop_times`, `routes`, `calendar`, `calendar_dates`, `trips`) were combined to build the **scheduled arrivals table**.

---

#### Stop Clustering (DBSCAN)

Some lines and directions contain **multiple stop_ids with the same stop name**, likely due to STIB’s need for high spatial precision. Since this level of granularity is not required for this study, stops were clustered.

* **Method:** DBSCAN based on geographic distance + stop name correction
* **Goal:** Group physically equivalent stops under a single logical stop cluster

##### Pseudo-code — *DBSCAN + Name Fix*

```
Algorithm: DBSCAN + Fix by Name

Initialize all clusters to -1

Repeat for x cycles (x = 10):

  # Step 1: Cluster assignment
  For each cluster group:
    If cluster == -1:
      eps = 200 meters if bus
      eps = 250 meters otherwise
      Apply DBSCAN using geographic distance (geopy metric)

  # Step 2: Name-based correction
  For each cluster:
    Find the first stop_name that appears more than once
    Remove all stops whose name does not match
    Reassign removed stops to cluster -1
```

---

#### Vehicle Position Data Handling

From the vehicle position samples collected every ~20 seconds, the following observations were made:

* `uuid` uniquely identifies a **trip + vehicle**
* `point_id` corresponds to the **stop_id** currently served by the vehicle

As a result:

* Only the **first occurrence of each (`uuid`, `point_id`) pair** was kept
* All subsequent occurrences were duplicates and were removed

---

#### Additional Data Cleaning

Several additional transformations were required to align vehicle position data with GTFS:

* **Stop ID formatting:**
  `point_id` contained only the first 4 digits of the GTFS `stop_id` and needed correction
* **Stop clustering:**
  The stop cluster logic was applied to the vehicle position data as well
* **Service day alignment:**

  * GTFS service days run approximately from **04:30 AM to 03:00 AM** the following day
  * Vehicle position timestamps were adjusted accordingly
* **Daily partitioning:**

  * GTFS files are provided **one per service day**
  * Vehicle position data was therefore split into **daily files** as well



