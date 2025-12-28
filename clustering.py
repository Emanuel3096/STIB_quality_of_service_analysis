import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from geopy.distance import distance as geopy_distance
from sklearn.neighbors import NearestNeighbors
import matplotlib.pyplot as plt

#Get the table to match stop_id and route_type. We only care about these two, so drop everything else.
stoptype = pd.read_csv("stop_route_type_match.csv")
stoptype = stoptype.drop_duplicates(subset="stop_id", keep="first")
stoptype = stoptype.drop(columns=["parent_station","location_type"])

def geopy_metric(coord1, coord2):
    return geopy_distance(coord1, coord2).meters

stoptype["cluster"]="-1"
min_samples = 2

letter = 'A'
name = "AFDGEGDSGDGRTDFDG"     #random string impossible to be matched on the condition below, for the cases name isn't defined straight away on the first iteration 

#run 10 times
for i in range(10):

    #DBScan algorithm part, finding the nearest neighbours and 
    for (cluster, route_type), group in stoptype.groupby(["cluster","route_type"]):
        if cluster == "-1":

            if route_type == 3:
                eps_meters = 200
            else:
                eps_meters = 250
            coords = group[['stop_lat', 'stop_lon']].to_numpy()
            db = DBSCAN(eps=eps_meters, min_samples=min_samples, metric=geopy_metric)
            labels = db.fit_predict(coords)
            labels = np.array([f"{letter}{l}" if l != -1 else -1 for l in labels])
            stoptype.loc[group.index, 'cluster'] = labels
    stoptype['cluster'] = stoptype['cluster'].astype(str)
    #Fix the clusters
    for (cluster, route_type), table in stoptype.groupby(["cluster", "route_type"]):
        for name1 in table["stop_name"]:
            count = 0
            for name2 in table["stop_name"]:
                if (name1.lower() in name2.lower()) or (name2.lower() in name1.lower()):
                    count += 1 
            if count > 1:
                name = name1
                break
        for stop in table["stop_id"]:        
            aux_name = table.loc[table["stop_id"] == stop, "stop_name"].iloc[0]
            if (aux_name.lower() in name.lower()) or (name.lower() in aux_name.lower()):
                pass
            else:
                stoptype.loc[stoptype["stop_id"] == stop, "cluster"] = "-1"

    letter = chr(ord(letter) + 1)

#Manual Fixing two entries that are actually not on the same cluster
stoptype.loc[stoptype["stop_id"]=="3042","cluster"]="-1"
stoptype.loc[stoptype["stop_id"]=="9701","cluster"]="-1"

stoptype['cluster'] = stoptype['cluster'].astype(str)


mask = stoptype['cluster'] == "-1"

# Get how many outliers there are
n_outliers = mask.sum()

n_outliers

# Create numeric cluster IDs: 1, 2, 3, ...
new_clusters = [str(i) for i in range(1, n_outliers + 1)]

# Assign them in order
stoptype.loc[mask, 'cluster'] = new_clusters

stoptype['cluster'] = stoptype['cluster'].astype(str)

stoptype.to_csv("clusters_stops.csv", index=False, encoding="utf-8")