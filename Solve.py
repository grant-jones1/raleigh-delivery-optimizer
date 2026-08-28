"""Solve the Raleigh last-mile CVRP and write solution_routes.csv.

Run from the project root:  python solve.py
"""
import numpy as np
import pandas as pd
from ortools.constraint_solver import routing_enums_pb2, pywrapcp

# ---------------------------------------------------------------- parameters
N_VEHICLES = 4
CAPACITY = 130          # 4 x 130 = 520 vs 466 demand
SOLVE_SECONDS = 120
DEPOT = 0

# ---------------------------------------------------------------- load inputs
distance_matrix = np.load('data/distance_matrix.npy').astype(int)
sample = pd.read_csv('data/sample_stops.csv')

assert 'demand' in sample.columns, "no demand column — run notebook 04 first"
assert len(distance_matrix) == len(sample), "matrix and stops file disagree"

demand = sample['demand'].to_numpy()
total_demand = int(demand.sum())

print(f"{len(sample) - 1} stops, {total_demand} packages")
print(f"{N_VEHICLES} vehicles x {CAPACITY} = {N_VEHICLES * CAPACITY} capacity")
assert total_demand <= N_VEHICLES * CAPACITY, "infeasible: not enough capacity"

# ---------------------------------------------------------------- build model
manager = pywrapcp.RoutingIndexManager(len(distance_matrix), N_VEHICLES, DEPOT)
routing = pywrapcp.RoutingModel(manager)


def distance_callback(from_index, to_index):
    i = manager.IndexToNode(from_index)
    j = manager.IndexToNode(to_index)
    return int(distance_matrix[i][j])


transit_idx = routing.RegisterTransitCallback(distance_callback)
routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)


def demand_callback(from_index):
    return int(demand[manager.IndexToNode(from_index)])


demand_idx = routing.RegisterUnaryTransitCallback(demand_callback)
routing.AddDimensionWithVehicleCapacity(
    demand_idx, 0, [CAPACITY] * N_VEHICLES, True, 'Capacity'
)

# ---------------------------------------------------------------- solve
params = pywrapcp.DefaultRoutingSearchParameters()
params.first_solution_strategy = (
    routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
)
params.local_search_metaheuristic = (
    routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
)
params.time_limit.seconds = SOLVE_SECONDS

print(f"\nsolving ({SOLVE_SECONDS}s limit)...")
solution = routing.SolveWithParameters(params)

print(f"status code: {routing.status()}   (1 = success)")
assert solution is not None, "no solution found"

# ---------------------------------------------------------------- extract
cap_dim = routing.GetDimensionOrDie('Capacity')
rows = []
fleet_metres = 0

for v in range(N_VEHICLES):
    index = routing.Start(v)
    seq = 0
    route_metres = 0
    addresses = []

    while True:
        node = manager.IndexToNode(index)
        rows.append({
            'vehicle': v + 1,
            'stop_sequence': seq,
            'node': node,
            'address': sample.iloc[node]['Address'],
            'latitude': sample.iloc[node]['latitude'],
            'longitude': sample.iloc[node]['longitude'],
        })
        addresses.append(sample.iloc[node]['Address'])

        if routing.IsEnd(index):
            break

        nxt = solution.Value(routing.NextVar(index))
        route_metres += distance_matrix[node][manager.IndexToNode(nxt)]
        index, seq = nxt, seq + 1

    load = solution.Value(cap_dim.CumulVar(index))
    fleet_metres += route_metres

    print(f"\nDriver {v + 1}: {len(addresses) - 2} stops, "
          f"load {load}/{CAPACITY}, {route_metres / 1000:.2f} km")
    for a in addresses:
        print(f"  -> {a}")

print(f"\nFLEET TOTAL: {fleet_metres / 1000:.2f} km")

# ---------------------------------------------------------------- verify
routes_df = pd.DataFrame(rows)
served = set(routes_df['node']) - {DEPOT}
missing = set(range(1, len(sample))) - served

assert not missing, f"{len(missing)} stops unserved: {sorted(missing)[:10]}"
print(f"all {len(served)} stops served")

routes_df.to_csv('data/solution_routes.csv', index=False)
print(f"wrote data/solution_routes.csv ({len(routes_df)} rows)")