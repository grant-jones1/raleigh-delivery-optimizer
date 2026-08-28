# Raleigh Last-Mile Delivery Route Optimizer

A capacitated vehicle routing model for commercial deliveries in Raleigh, NC,
built on real road-network distances and county address data.

## Result

Routing 150 commercial stops from a single depot across a four-van fleet:

| Method | Drivers | Distance (mi) | Labor hours | Daily cost |
|---|---|---|---|---|
| Dataset order (no tool) | 4 | 1,141.4 | 73.7 | $799.01 |
| Nearest-neighbor heuristic | 4 | 245.9 | 25.7 | $172.15 |
| **OR-Tools (guided local search)** | **4** | **177.0** | **22.0** | **$123.91** |

**28.0% fewer miles than a greedy nearest-neighbor heuristic** — roughly what a
dispatcher working from a map would produce — and 84.5% fewer than serving stops
in unstructured database order.

At an assumed $0.70/mile fully-burdened operating cost, the improvement over
nearest-neighbor is about **$48/day, or $12,500/year** across 260 operating days
for a single four-van route.

Two baselines are reported deliberately. The dataset-order figure shows the
value of routing at all; the nearest-neighbor figure is the honest measure of
what the optimizer contributes over a competent manual approach.

## Problem

- **Depot:** 4520 Bullock Farm Rd, Raleigh (Amazon DRT3)
- **Stops:** 150 non-residential addresses sampled from Wake County MAR data
- **Demand:** 466 packages, 1–5 per stop
- **Fleet:** 4 vans, 130-package capacity each (520 total, so capacity binds)
- **Objective:** minimize total fleet distance subject to capacity

## Method

1. **Address data** — Wake County Master Address Repository, filtered to
   non-residential structures inside Raleigh city limits (22,000 records).
2. **Coordinate conversion** — NC State Plane (ESRI:102719) to WGS84.
3. **Road network** — OSMnx drive network for Raleigh, reduced to its largest
   strongly connected component so every stop pair is reachable under one-way
   restrictions.
4. **Distance matrix** — single-source Dijkstra per origin over the road graph,
   giving true driving distances rather than straight-line approximations.
   151 Dijkstra runs instead of 22,650 pairwise shortest-path calls.
5. **Solver** — Google OR-Tools CVRP. Parallel cheapest insertion for the first
   solution, then guided local search with a 120-second limit.
6. **Validation** — every reported route set is checked for full coverage, no
   duplicate visits, no capacity violations, and correct fleet size before it
   reaches the comparison table.

## Repository

```
├── solve.py                    # runs the routing model, writes solution_routes.csv
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_coordinate_conversion.ipynb
│   ├── 03_depot_addition.ipynb
│   ├── 04_road_network.ipynb        # graph, sampling, demand, distance matrix
│   ├── 05_routing_model.ipynb       # exploratory; solve.py is the entry point
│   ├── 06_visualization.ipynb       # Folium route map
│   └── 07_baseline_comparison.ipynb # baselines, validation, results table
├── data/                       # not versioned — see Reproducing
└── output/
    ├── route_map.html
    └── comparison.csv
```

Run `python solve.py` from the project root after notebook 04 has produced the
distance matrix.

## Reproducing

Data files are excluded from version control (the raw address file and road
graph are large). To rebuild:

1. Download the Wake County MAR address dataset and place the CSV in `data/`.
2. Run notebooks 01 through 04 in order. Notebook 04 downloads the OSM road
   network, samples stops, generates demand, and builds the distance matrix.
3. Run `python solve.py`.
4. Run notebooks 06 and 07 for the map and the comparison table.

Demand and stop sampling are seeded, so results are reproducible.

```
pip install -r requirements.txt
```

## Assumptions

- Package demand is synthetic (uniform 1–5 per stop); real volume data was
  not available.
- 30 km/h average urban delivery speed, 5 minutes service time per stop.
- $0.70/mile fully-burdened van operating cost.
- Labor hours are summed across the fleet, not per driver — 22.0 hours means
  four drivers at roughly 5.5 hours each.

## Limitations and next steps

**Distance, not time.** The objective minimizes kilometers. Real last-mile
dispatch is time-constrained: a travel-time matrix with service time folded into
a shift-length dimension would better reflect how routes are actually built.

**No time windows.** Commercial deliveries frequently carry appointment
constraints. Adding windows to a subset of stops is the most realistic next
extension.

**Route imbalance.** The solver minimizes total fleet distance with no balance
term, so route lengths vary (58–97 km). Adding a global span cost coefficient
would even them out at the cost of total mileage — a trade-off worth reporting
in both directions rather than silently choosing one.

**Single depot.** Every route begins with a long leg out of southeast Raleigh.
A multi-depot formulation would show whether a second dispatch point pays for
itself.

**Deterministic demand.** Package counts are known in advance. A stochastic
formulation, where demand is revealed on arrival, is closer to reality and is
the direction this model would extend academically.

**Network boundary.** The road graph is clipped to Raleigh city limits, so
routes that would realistically cut through adjacent municipalities are forced
to stay inside the boundary, slightly inflating distances for stops near the
edge.

## Built with

Python, OR-Tools, OSMnx, NetworkX, pandas, NumPy, Folium, GeoPy, pyproj.
