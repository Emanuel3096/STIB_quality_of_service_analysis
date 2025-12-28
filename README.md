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
* Each API call returns the **latest info on every active vehicle**, updated approximately every **20 seconds** during operations.
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
3. Compute **headways** for each:line, direction and stop combination
4. Identify **time intervals with similar statistical properties** based on headways, and classify each interval in terms of:

   * punctuality
   * frequency
5. Compute punctuality and frequency metrics by comparing **scheduled vs. real arrivals** for each interval

---

### 1. Data Exploration & Pre-Processing

#### GTFS Processing

* All GTFS components (`stops`, `stop_times`, `routes`, `calendar`, `calendar_dates`, `trips`) were combined to build the **scheduled arrivals table**.

---

#### Stop Clustering

Some lines and directions contain **multiple stop_ids with the same stop name**, likely due to STIB’s need for high spatial precision. Since this preceision isn't needed for the current analysis, and it´s actually harmful since we need a robust stop identifier for agreggation, stops were clustered.

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

### 2. Modelling

#### Compute Headways

* Headways were computed for **both scheduled and real arrivals**.
* The arrivals tables were:

  * sorted by `stop_cluster`, `route_id`, `direction_id`, and `arrival_time`
  * grouped by `stop_cluster`, `route_id`, and `direction_id`
* For each group, headways were computed by subtracting the arrival time of each vehicle from the **previous arrival** within the same group.

---

#### Build Time Groups

1. Group data by:

   * stop cluster
   * route
   * direction

2. For each group, treat the **headway series as a time signal** and apply the **PELT algorithm** to split the signal into segments based on changes in statistical properties.

   * Cost model: **squared error**
   * Penalty: **3**
   * Minimum segment length: **4**
   * Several configurations were tested before selecting these parameters.

3. **Boundary cleaning algorithm**:

   * For each boundary between two adjacent time groups:

     * Check whether the first element of the current group is closer to the **mean headway of the previous group** or its own group.
     * If it is closer to the previous group, reassign it accordingly.

4. Compute the **median headway** for each time group and label it as follows:

   * **Frequency interval** if median headway < **12 minutes**
   * **Punctuality interval** otherwise

---

### 3. Results

#### Metric Definition

##### Punctuality – On-Time Performance (OTP)

Punctuality was assessed using the **On-Time Performance (OTP)** metric, computed using three different absolute thresholds:

* **OTP1**: ± **1 minute**
* **OTP2**: ± **2 minutes**
* **OTP3**: ± **3 minutes**

For each arrival belonging to a **punctuality time group**:

* The real arrivals table was queried to check whether an arrival for the same
  `[stop_cluster, route, direction]` occurred within the defined time threshold around the scheduled arrival.
* Each comparison yielded a Boolean value.
* Boolean values were averaged to obtain a **percentage score per time group**.

---

##### Frequency – Excess Waiting Time (EWT)

Frequency was evaluated using the **Excess Waiting Time (EWT)** metric, computed from:

* **Scheduled Waiting Time (SWT)**
* **Actual Waiting Time (AWT)**

**Scheduled Waiting Time (SWT):**

* For each frequency time group, SWT was computed by applying the standard formula to the **scheduled headways**.

**Actual Waiting Time (AWT):**

1. For each time group, extract its **time interval** (difference between first and last scheduled arrival).
2. Add a **2-minute tolerance** to both the lower and upper bounds.
3. Query the real arrivals table for arrivals within this extended interval.
4. Compute headways from the retrieved real arrivals.
5. Compute AWT using the resulting headways.

Finally, **EWT** was computed by combining the SWT and AWT values.

---

#### Export Results

1. Aggregate all computed metrics **per service day**.
2. Export results into manageable **CSV files**, splitting labeled data into separate tables connected by keys, in preparation for a future dashboard:

   * `main_file.csv`
   * `metrics.csv`
   * `stop_info.csv`
   * `route_info.csv`

### 4. Analysis

Here is the section **formatted consistently with the previous ones**, with **clean Markdown**, **corrected English**, and **improved flow**, while keeping **your original style and intent**.

---

### 4. Analysis

Further analysis was carried out using a **Power BI dashboard**, where bottlenecks and other operational patterns can be identified much more quickly and intuitively.

The analysis pipeline was designed in this way to allow **STIB decision makers** (if desired) to explore:

* specific lines
* stops
* neighborhoods
* times

**without requiring any additional coding**.

#### Missing Metrics in Time Groups

During the analysis, it was observed that a significant number of time groups could not be evaluated, as **no real arrivals were recorded** for those intervals.

* Approximately **20% of the computed time groups** fell into this category.


#### Potential Reasons

Several factors may explain the absence of real arrivals in these time groups:

* **Terminal stations** sometimes do not emit a “real arrival” trigger
* **Stops located very close to each other**, where one stop is systematically missed, especially in dense or highly trafficked areas
* **Faulty reception** from vehicle positioning systems
* **“Ghost trips”**, i.e. trips present in the schedule but that did not actually occur
* **Limitations or potential miscomputations** in the analysis itself

