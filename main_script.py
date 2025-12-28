import requests
import geopandas as gpd
import pandas as pd
import numpy as np
import datetime, pytz, time
from geopy.distance import distance as geopy_distance
import gtfs_kit as gk 
import ruptures as rpt

# Secondary Function needed for the time group calculation: clean boundaries - if the first item of a time group statistically resembles more the previous group, it is reassigned

def clean_boundaries(signal, labels):

    labels = labels.copy()

    group_means = {}
    for g in np.unique(labels):
        group_means[g] = signal[labels == g].mean()

    for i in range(1, len(labels)):
        prev_group = labels[i-1]
        curr_group = labels[i]

        if prev_group == curr_group:
            continue

        curr_val = signal[i]
        # if boundary misplaced, shift
        if abs(curr_val - group_means[prev_group]) < abs(curr_val - group_means[curr_group]):
            labels[i] = prev_group
    
    return labels


#CYCLE TO UPLOAD THE GTFS INTO A VARIABLE (REPLACING THE PREVIOUS)

# Initate the export dataframe. Rules for connection via primary keys:
# 1. Main File is connected to stop_info arrivals via the stop_id
# 2. Main File is connected to route_info via day and route_id
# 3. Main File is connected to metrics via day, cluster, route_id, direction_id, route_type and time_group

main_file = pd.DataFrame(columns = ["day", "month","stop_id", "cluster", "route_id", "direction_id","arrival_time","headway","route_type","time_group"])
metrics = pd.DataFrame(columns = ["day", "cluster", "route_id", "direction_id", "route_type","time_group","avg_headway_group", "type_of_assessment","SWT","OTP1","OTP2","OTP3", "AWT", "EWT"])
stop_info = pd.DataFrame(columns =["day","stop_id","stop_name"])
route_info = pd.DataFrame(columns =["day", "route_id", "route_short_name","route_long_name"])

clusters = pd.read_csv("clusters_stops.csv")

for i in range(22,47,1):          #15-47 is the value for the whole cycle
    if i>31:
        filename = f"gtfs {i-31}-{9}.zip"
        service_day = i-31
        service_month = 9
    else:
        filename = f"gtfs {i}-{8}.zip"
        service_day = i
        service_month = 8
    feed = gk.read_feed(filename, dist_units='m')  # 'm' for meters
    
    tables ={}
    for item in feed.__dict__.keys():
        tables[item]=getattr(feed, item)
    
    if i>40:
        position_v = pd.read_csv(f"vehicles/vehicle_pos_09-{i-31}.csv")
        day=f"202509{i-31}"
    elif i<41 and i>31:
        position_v = pd.read_csv(f"vehicles/vehicle_pos_09-0{i-31}.csv")
        day=f"2025090{i-31}" 
    else:
        position_v = pd.read_csv(f"vehicles/vehicle_pos_08-{i}.csv")
        day=f"202508{i}" 

    print(service_day, service_month, day)
    ########                                
    ######## ARRIVALS TABLE
    ########

    #1. Algorithm to remove all but the most recent entry from an uuid and stop_id combination for a given day (we are only interested at the best )

    position_v["arrival_time"] = pd.to_timedelta(position_v["arrival_time"])   #Because the read csv takes this as a string and not a timedelta
    position_v = position_v.sort_values(["uuid","pointId","day","arrival_time"])
    arrivals = position_v.groupby(["pointId", "uuid"], as_index=False).first()

    #2. Merge to add the stop_id values to the table from matching the point_id:

    arrivals['pointId'] = arrivals['pointId'].astype(str)
    arrivals['pointId'] = arrivals['pointId'].str.zfill(4)
    tables['stops']['stop_id_prefix'] = tables['stops']['stop_id'].str[:4]
    arrivals = arrivals.merge(tables['stops'][['stop_id_prefix', 'stop_name',"stop_id"]],left_on='pointId',right_on='stop_id_prefix',how='left')
    arrivals = arrivals.drop(columns=['stop_id_prefix'])
    tables['stops']=tables['stops'].drop(columns=['stop_id_prefix'])

    #3. Merge to add the route_id to this table

    arrivals["lineId"] = arrivals["lineId"].astype(str)
    arrivals = arrivals.merge(
        tables['routes'][['route_id',"route_short_name"]],
        left_on='lineId',         
        right_on='route_short_name', 
        how='left'
    )

    #4. Merge to add the cluster to the table
    arrivals = arrivals.merge(
        clusters[["cluster","stop_id","route_type"]],
        on='stop_id',  # merge on stop_id
        how='left'     # keep all rows in arrivals
    )

    #5. Script to calculate headways:

    arrivals = arrivals.sort_values(["route_type", "cluster", "lineId", "direction","day", "arrival_time"])
    arrivals["headway"] = (arrivals.groupby(["lineId", "direction","route_type","cluster"])["arrival_time"].diff().dt.total_seconds() / 60)
    arrivals["headway"].describe(include='all')

    # 6. Create direction_id value from the direction
    arrivals["direction_id"]=arrivals.direction.map({1:1,2:0})
    arrivals["direction_id"] = arrivals["direction_id"].astype(str)

    #7. Cleans on data: 
    arrivals = arrivals.loc[~arrivals.headway.isna()] #7.1. Remove all lines where headway is missing, since we care only about time between stops
    arrivals["cluster"] = arrivals["cluster"].astype(str)
    arrivals["route_id"] = arrivals["route_id"].astype(str)
    arrivals["direction_id"] = arrivals["direction_id"].astype(str)

    #8. Sort by relevant columns, drop unnecessary ones and rename for uniformization
    arrivals = arrivals.drop(columns =["direction","color","time","pointId","uuid","timestamp","datetime","id","distanceFromPoint","distance","geometry"])

    stops_arrivals = arrivals[["day","stop_id"]].drop_duplicates()
    routes_arrivals = arrivals[["day","route_id"]].drop_duplicates()

    arrivals = arrivals.drop(columns =["stop_name","route_short_name"])
    arrivals = arrivals[["day","month","stop_id","cluster","route_id","direction_id","arrival_time","headway","lineId","route_type"]]

    ########                                
    ######## ALL_STOPS TABLE
    ########

    # 1. Treate the day and extract the service_ids that were run that day: take the scheduled and cross check with exception_types
    
    panda_day = pd.to_datetime(day)
    serv_scheduled = tables["calendar"].loc[(tables["calendar"].start_date <= day) & (tables["calendar"].end_date >= day) &(tables["calendar"][panda_day.day_name().lower()] == 1),"service_id"] 
    serv_removed = tables["calendar_dates"].loc[(tables["calendar_dates"].date == day) & (tables["calendar_dates"].exception_type == 2), "service_id"]
    serv_added = tables["calendar_dates"].loc[(tables["calendar_dates"].date == day) & (tables["calendar_dates"].exception_type == 1),"service_id"]
    a = serv_scheduled[~serv_scheduled.isin(serv_removed)]
    serv = pd.concat([a, serv_added]).unique()

    # 2. Get the trip_ids that correspond to the service_ids scheduled

    all_trips = tables["trips"].loc[(tables["trips"].service_id.isin(serv)),"trip_id"]

    # 3. Get all the stops that correspond to those trip_ids - THIS WILL BE THE BASE FOR THE ANALYSIS

    all_stops = tables["stop_times"].loc[tables["stop_times"].trip_id.isin(all_trips)]

    # 4. Merges to get the route_id and direction_id to this main table

    all_stops = all_stops.merge(tables['trips'][['trip_id', 'route_id','direction_id']], on='trip_id',how='left')
    all_stops = all_stops.merge(tables['routes'][['route_id','route_short_name','route_type']], on='route_id', how='left')   #we might be able to cut this entirely as well

    # 5. Merge to get the clusters in the table

    all_stops = all_stops.merge(clusters[['cluster', 'stop_id']],  on='stop_id', how='left')

    ##route_type_map = {0: "Tram",1: "Metro",3: "Bus"}
    ##all_stops["Route_Type"] = all_stops.route_type.map(route_type_map)

    # 6. Remove the multiple stops we might have on one trip on the same cluster - this happens since we are doing cluster and 
    # some lines have multiple stops on the same stops. We can assume here a "cluster" on the results as well - further build on the report

    all_stops = all_stops.sort_values(["trip_id","cluster","arrival_time"])
    all_stops = all_stops.groupby(["trip_id", "cluster"], as_index=False).first()

    # 7. Calculate headways:

    all_stops["arrival_time"] = pd.to_timedelta(all_stops["arrival_time"])
    all_stops = all_stops.sort_values(["route_type", "cluster", "route_id", "direction_id", "arrival_time"])
    all_stops["headway"] = (all_stops.groupby(["route_id", "direction_id","route_type","cluster"])["arrival_time"].diff().dt.total_seconds() / 60)

    # 8. Remove the trips that only have one stop, since they have no value either way. 
    # (potentially this can be increased to remove the trips with 2 or 3 stops as well)

    stop_count_per_trip = all_stops['trip_id'].value_counts().reset_index()
    stop_count_per_trip.columns = ['id', 'count']
    a = stop_count_per_trip.loc[stop_count_per_trip["count"] < 2,"id"]     #2 set for now, increase if we decide to exclude further
    all_stops = all_stops[~all_stops.trip_id.isin(a)]

    # 9. Remove the na headways (since we care only about the time between arrivals)

    all_stops = all_stops.loc[~all_stops.headway.isna()]

    # 10. Setting types for columns, useful for the future + assigning day columns for now
    all_stops["day"]=service_day            
    all_stops["month"]=service_month
    all_stops["cluster"] = all_stops["cluster"].astype(str)
    all_stops["route_id"] = all_stops["route_id"].astype(str)
    all_stops["direction_id"] = all_stops["direction_id"].astype(str)

    # 11. Clean column and sort columns for intermediate visualization

    all_stops = all_stops.drop(columns =["departure_time","stop_sequence","pickup_type","drop_off_type","timepoint","trip_id","route_short_name"])
    all_stops = all_stops[["day","month","stop_id","cluster","route_id","direction_id","arrival_time","headway","route_type"]]

    # 12. Prepare the stops and routes used and merge them into the main export dataframes at the end

    routes_all_stops = all_stops[["day","route_id"]].drop_duplicates()
    stops_all_stops = all_stops[["day","stop_id"]].drop_duplicates()

    routes = pd.concat([routes_all_stops, routes_arrivals], ignore_index=True)
    stops = pd.concat([stops_all_stops, stops_arrivals], ignore_index=True)

    routes = routes.merge(tables["routes"][["route_id","route_short_name","route_long_name"]],  on='route_id', how='left')
    stops = stops.merge(tables["stops"][["stop_id","stop_name"]],  on='stop_id', how='left')

    stop_info = pd.concat([stop_info, stops], ignore_index=True)
    route_info = pd.concat([route_info, routes], ignore_index=True)


    ########                                
    ######## TIME GROUP CALCULATION
    ########




    #Main function:

    all_stops["time_group"] = -1

    # 1. Cycle to iterate through the all_stops by cluster, route_id, direction_id

    for (stop,route,direction),table in all_stops.groupby(["cluster","route_id","direction_id"]):
        
        # 2. Sort and initialize the numpys that allow us to do the logic

        table = table.sort_values("arrival_time")
        idx = table.index.to_numpy()
        timestamps = table['arrival_time'].to_numpy()
        signal = table["headway"].to_numpy()

        # 3. If we have a small group, shorter than 3 arrivals, we just assign it to one time group 0

        if len(signal) < 4:
            # Assign all rows in this group to a single time_group = 0
            all_stops.loc[idx, "time_group"] = 0
            continue
        
        # 4. Run the pelt algorithm 

        model = rpt.Pelt(model="l2").fit(signal)
        change_points = model.predict(pen=15)  # increase pen → fewer segments
        labels = np.zeros(len(signal), dtype=int)

        # 5. Cycle to assign IDs (0, 1, 2, 3, ...) to each record of the time group

        start = 0
        group_id = 0
        for cp in change_points:
            labels[start:cp] = group_id
            start = cp
            group_id += 1

        # 6. Fix the labels producec by the algorithm with the secondary function, and potentially cleaning the boundary. Then assign it once to the all_stops table

        corrected_labels = clean_boundaries(signal, labels)
        all_stops.loc[idx, "time_group"] = corrected_labels

    #Compute SWT for all Frequency Intervals
    #Compute average headway per group and type of assessment 

    all_stops["avg_headway_group"] = (all_stops.groupby(["cluster", "route_id", "direction_id", "time_group"])["headway"].transform("mean"))
    all_stops["type_of_assessment"] = (all_stops["avg_headway_group"]<12).map({True: "Frequency",False: "Punctuality"})

    a = 2*all_stops.groupby(["cluster", "route_id", "direction_id", "time_group"])["headway"].transform("sum")
    b = all_stops.groupby(["cluster", "route_id", "direction_id", "time_group"])["headway"].transform(lambda x: (x ** 2).sum())
    all_stops["SWT"] = b/a
    all_stops.loc[all_stops["type_of_assessment"] != "Frequency", "SWT"] = np.nan

    all_stops = all_stops.sort_values(["cluster","route_id","direction_id","time_group","arrival_time"])
    arrivals = arrivals.sort_values(["cluster","route_id","direction_id","arrival_time"])

    #Compute AWT
    arrival_groups = arrivals.groupby(["day","cluster","route_id","direction_id"])

    for (day, cluster, route, direction, time_group, assessment),table in all_stops.groupby(["day", "cluster", "route_id", "direction_id", "time_group","type_of_assessment"]):
        
        idx = table.index.to_numpy()

        if (day, cluster, route, direction) not in arrival_groups.groups:
            # no arrivals at all
            if assessment == "Punctuality":
                all_stops.loc[idx, ["OTP1","OTP2","OTP3"]] = -1
            else:
                all_stops.loc[idx, ["AWT"]] = np.nan
            continue

        arrival_sub = arrival_groups.get_group((day,cluster,route,direction))
        arrival_sub = arrival_sub.rename(columns={"arrival_time": "arrival_actual"})


        if assessment == "Punctuality":

            joined = pd.merge_asof(
                table[["arrival_time"]],
                arrival_sub[["arrival_actual"]],
                left_on="arrival_time",
                right_on="arrival_actual",
                direction="nearest",
                tolerance=pd.Timedelta(minutes=3),
            )

            delta = (joined["arrival_time"]-joined["arrival_actual"]).abs()

            otp1 = (delta <= pd.Timedelta(minutes=1)).mean()
            otp2 = (delta <= pd.Timedelta(minutes=2)).mean()
            otp3 = (delta <= pd.Timedelta(minutes=3)).mean()

            all_stops.loc[idx, "OTP1"] = otp1
            all_stops.loc[idx, "OTP2"] = otp2
            all_stops.loc[idx, "OTP3"] = otp3

        if assessment == "Frequency":
            #Add 2 minutes to each side of the time group as an error margin
            max_window = table["arrival_time"].max() + pd.Timedelta(minutes=2)
            min_window = table["arrival_time"].min() - pd.Timedelta(minutes=2)
            
            real_headways =arrival_sub.loc[(arrival_sub.arrival_actual.between(min_window, max_window)),"headway"]
            
            h = real_headways.to_numpy()

            c = 2*h.sum()
            d = (h**2).sum()

            if c != 0:
                all_stops.loc[idx, "AWT"] = d/c
            else:
                all_stops.loc[idx, "AWT"] = np.nan


    all_stops.loc[all_stops["type_of_assessment"] != "Frequency", "AWT"] = np.nan
    all_stops.loc[all_stops["type_of_assessment"] != "Punctuality", ["OTP1","OTP2","OTP3"]] = np.nan

    all_stops["EWT"] = (all_stops["AWT"] - all_stops["SWT"])                             #If one column is nan then the result will be naan, which makes sense

    metrics_all_stops = all_stops[["day", "month", "cluster", "route_id", "direction_id", "route_type","time_group","avg_headway_group", "type_of_assessment","SWT","OTP1","OTP2","OTP3", "AWT", "EWT"]].drop_duplicates()
    main = all_stops[["day", "month","stop_id", "cluster", "route_id", "direction_id","arrival_time","headway","route_type","time_group"]]

    main_file = pd.concat([main_file,main], ignore_index = True)
    metrics = pd.concat([metrics,metrics_all_stops], ignore_index = True)



main_file.to_csv("main_file.csv", index=False)
metrics.to_csv("metrics.csv", index=False)
stop_info.to_csv("stop_info.csv", index=False)
route_info.to_csv("route_info.csv", index=False)