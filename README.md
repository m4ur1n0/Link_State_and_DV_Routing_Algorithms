# Link_State_and_DV_Routing_Algorithms
implementation of BGP and OSPF style routing algorithms for a routing simulation program (routing sim not written by me).

# Link_State_Node Class
Implementation of an OSPF-style link-state routing algorithm, wherein each node in a network has knowledge of the latency and endpoints of all reachable links, and uses Dijkstra's algorithm to figure out the shortest path to any other reachable node.

# Distance_Vector_Node Class
Implementation of a Bellman-Ford style algorithm wherein each node keeps a distance vector routing table mapping every reachable known to the exact path it needs to take to get there. When one of its paths changes, it alerts its neighbors, and each path changed causes the recalculating of the entire routing table based on the distance vectors of neighbors.

This project was a lot of fun. I love Dijkstra's pathfinding algorithm and it was cool to learn about other pathfinding algorithms and how they are used in routing. I encountered a few bugs in implementating these projects as a result of rushing myself and not taking the proper time to understand the algorithms before jumping in, so about halfway through I restarted both classes, but it was incredibly satisfying to start from scratch with a much more in-depth knowledge. Everything feels a lot neater than it was before. 

Usage:
Cmd> python3 sim.py DISTANCE_VECTOR path/to/event.event
OR
Cmd> python3 sim.py LINK_STATE path/to/event.event
