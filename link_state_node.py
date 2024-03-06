from simulator.node import Node
import json

# --------------------------------------------------------------------------------
# LSA STRUCTURE:

# "LSA|NODE1|NODE2|MESSAGE_SENDER|SEQ_NUM|LINK_COST"

# this way we can just .split('|') and int()
# node1 and node2 are nodes with the link being advertised abt
# message_sender is the node that sent this specific version of the lsa
# --------------------------------------------------------------------------------
# FULL LSA DATABASE TRANSFER STRUCTURE:

# "DAT|OWNER|SENDER|SEQ|JSON_DUMP_OF_LINK_SEQS|JSON_DUMP_OF_LINK_COSTS"

# ---------------------------------------------------------------------------------

class Link_State_Node(Node):
    def __init__(self, id):
        super().__init__(id)

        # LSA DATABASE STRUCTURE
        # link_costs : {frozenset(node1, node2) : latency_btw_node1_node2}
        # link_seqs : {frozenset(node1, ndoe2) : most_recent_seq_for_link}
        self.link_costs = {}
        self.link_seqs = {}

        # dat_seqs = {node : seq_of_last_database_sent_or_recvd}
        self.dat_seqs = {self.id: 0}

        self.neighbors = []
        self.known_nodes = []


    def __str__(self):
        return f"[NODE: {self.id} with NEIGBORS: {self.neighbors}\nDATABASE: {self.link_costs}]"
    
    def link_has_been_updated(self, neighbor, latency):
        # -1 if removed
        if neighbor not in self.known_nodes:
            self.known_nodes.append(neighbor)
        
        link = frozenset([self.id, neighbor])
        if neighbor not in self.neighbors and latency != -1:
            self.link_costs[link] = latency
            self.link_seqs[link] = 0
            self.neighbors.append(neighbor)
            self.begin_flood(neighbor, latency, 0)
            self.send_my_db(neighbor)
        elif neighbor in self.neighbors:
            if latency != -1 and latency != self.link_costs[link]:
                self.link_costs[link] = latency
                self.link_seqs[link] += 1
                self.begin_flood(neighbor, latency, self.link_seqs[link])
            elif latency == -1:
                del self.link_costs[link]
                seq = self.link_seqs[link] + 1
                del self.link_seqs[link]
                # del self.link_seqs[link]
                self.neighbors.remove(neighbor)
                self.begin_flood(neighbor, latency, seq)
        


    # SENDING FUNCTIONS -------------------------------------------------------

    def begin_flood(self, neighbor, latency, seq):
        # to be used when a new node is added as our neighbor
        # LSA STRUCTURE:
        # "LSA|NODE1|NODE2|MESSAGE_SENDER|SEQ_NUM|LINK_COST"
        lsa = f"LSA|{self.id}|{neighbor}|{self.id}|{seq}|{latency}"
        # if latency != -1:
        #     link = frozenset({self.id, neighbor})
        #     self.link_seqs[link] += 1
        for n in self.neighbors:
            # since neighbor will be doing the same, does not send to neighbor
            if n != neighbor:
                self.send_to_neighbor(n, lsa)

    def send_lsa(self, neighbor, node1, node2, latency, sequ=-1, dead=0):
        # since it is meant to be used in iteration, it does NOT update seq num for us
        link = frozenset({node1, node2})
        if sequ == -1:
            seq = self.link_seqs[link]
        else:
            seq = sequ


        if dead == 0:
            lsa = f"LSA|{node1}|{node2}|{self.id}|{seq}|{latency}"
        else:
            lsa = f"LSA|{node1}|{node2}|{self.id}|{seq}|-1"
        

        self.send_to_neighbor(neighbor, lsa)
        

    def send_my_db(self, neighbor):
        # FULL LSA DATABASE TRANSFER STRUCTURE:
        # "DAT|OWNER|SENDER|SEQ|JSON_DUMP_OF_LINK_SEQS|JSON_DUMP_OF_LINK_COSTS"
        json_costs = self.dict_to_string(self.link_costs)
        json_seqs = self.dict_to_string(self.link_seqs)
        lda = f"DAT|{self.id}|{self.id}|{self.dat_seqs[self.id]}|{json_seqs}|{json_costs}"
        self.send_to_neighbor(neighbor, lda)
        self.dat_seqs[self.id] += 1

    # -------------------------------------------------------------------------

    # LSA DATABASE UPKEEP FUNCTIONS --------------------------------------------

    def dict_to_string(self, d):
        """
        Convert a dictionary to a string representation.
        """
        return json.dumps([[list(k), v] for k, v in d.items()])

    def string_to_dict(self, s):
        """
        Convert a string representation back to a dictionary.
        """
        return {frozenset(k): v for k, v in json.loads(s)}
    # credit : the two functions above were created by chatgpt

    def get_dat_sequence_number(self, node):
        if node not in self.dat_seqs:
            return -1
        else:
            return self.dat_seqs[node]

    def get_link_sequence_number(self, node1, node2, link=None):
        if link == None:
            link = frozenset(node1, node2)
        
        if link not in self.link_seqs:
            return -1
        else:
            return self.link_seqs[link]



    def update_link_info(self, neighbor1, neighbor2, latency, seq, link=None):
        if link == None:
            link = frozenset({neighbor1, neighbor2})
        self.link_costs[link] = latency
        self.link_seqs[link] = seq
    
    # --------------------------------------------------------------------------

    def process_incoming_routing_message(self, m: str):
        classifier = m[0:3]
        if classifier == 'LSA':
            
            # case 1 : received an LSA
            # LSA STRUCTURE:
            # "LSA|NODE1|NODE2|MESSAGE_SENDER|SEQ_NUM|LINK_COST"
            parts = m[4:].split('|')
            node1, node2, sndr, seq, lat = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
            if node1 not in self.known_nodes:
                self.known_nodes.append(node1)
            if node2 not in self.known_nodes:
                self.known_nodes.append(node2)

            link = frozenset({node1, node2})
            if self.id in link:
                # case 1: info about my link,
                # it will receive the information on its own, and can ignore
                return
            elif link not in self.link_costs and lat == -1:
                # in this case we've already deleted this link and don't wanna redo this
                return

            elif seq > self.get_link_sequence_number(node1, node2, link=link):
                # print(f"\n\n{self.id} ACCEPTING {m} with my\nseqs: {self.link_seqs}\ncosts: {self.link_costs}\n\n")
                if lat != -1:
                    self.update_link_info(node1, node2, lat, seq, link=link)

                    for n in self.neighbors:
                        
                        if n != sndr:
                            # print(f"{self.id} FORWARDING ({link} : {lat}) TO {n}")
                            self.send_lsa(n, node1, node2, lat, seq)
                else:
                    if link in self.link_costs:
                        # del self.link_seqs[link]
                        del self.link_costs[link]
                        del self.link_seqs[link]
                        for n in self.neighbors:
                            if n != sndr:
                                self.send_lsa(n, node1, node2, lat, seq, dead=1)
            elif seq == self.get_link_sequence_number(node1, node2, link=link):
                # print(f"\n\n{self.id} IGNORING {m} with my\nseqs: {self.link_seqs}\ncosts: {self.link_costs}\n\n")
                pass
            elif seq < self.get_link_sequence_number(node1, node2, link=link):
                # print(f"\n\n{self.id} REJECTING {m} with my\nseqs: {self.link_seqs}\ncosts: {self.link_costs}\n\n")
                self.send_lsa(sndr, node1, node2, lat)

        elif classifier == 'DAT':
            # case 2 : received a database
            if len(m) == 4:
                # should never happen, idk why i check
                return
            # FULL LSA DATABASE TRANSFER STRUCTURE:
            # "DAT|OWNER|SENDER|SEQ|JSON_DUMP_OF_LINK_SEQS|JSON_DUMP_OF_LINK_COSTS"
            
            parts = m[4:].split('|')
            owner, sndr, seq, link_seqs, link_costs = int(parts[0]), int(parts[1]), int(parts[2]), self.string_to_dict(parts[3]), self.string_to_dict(parts[4])

            if owner not in self.dat_seqs or seq > self.dat_seqs[owner]:
                # copy over the received database for every link it doesn't have
                # or if db's link info is more recent
                self.dat_seqs[owner] = seq
                for link in link_costs:
                    linkseq = link_seqs[link]
                    if linkseq > self.get_link_sequence_number(0, 0, link):
                        # since get_link_seq_number returns -1 on link not found
                        # this effectively tests if link exists as well 
                        nodes = list(link)
                        node1 = nodes[0]
                        node2 = nodes[1]
                        lat = link_costs[link]
                        if node1 not in self.known_nodes:
                            self.known_nodes.append(node1)
                        if node2 not in self.known_nodes:
                            self.known_nodes.append(node1)

                        self.update_link_info(node1, node2, lat, linkseq, link)
                        for n in self.neighbors:
                            if n != sndr and n != owner:
                                self.send_lsa(n, node1, node2, lat, linkseq)

                    


    def get_next_hop(self, destination):
        if destination == self.id:
            # this might be wrongs
            return self.id
        path = self.generate_path(destination)
        return path[0]


    # PATH GENERATION FUNCTIONS ------------------------------------------------

    def generate_path(self, dst):
        # will return a list representing path between self and dst
        # or -1 if no path is found 
        path_dict = self.dijkstra()
        # print(f"just dijkstrad:\nlink_costs = {self.link_costs}\nknown_nodes = {self.known_nodes}\nself = {self.id}\ndijkstra result = {path_dict}")
        if dst not in path_dict:
            return [-1]
        
        path_node = dst
        path = []
        while path_node != self.id:
            if path_node == None:
                return [-1]
            path.insert(0, path_node)
            path_node = path_dict[path_node][0]
        
        return path

    def dijkstra(self):
        # Initialize distances dictionary with infinity for all nodes except the start node
        distances = {node: float('inf') for node in self.known_nodes}
        distances[self.id] = 0

        # Initialize dictionary to store predecessor nodes and their respective costs
        predecessors = {node: None for node in self.known_nodes}

        # Set of nodes whose shortest path from the start node is already determined
        visited = set()

        while len(visited) < len(self.known_nodes):
            # Find the node with the minimum distance from the start node
            min_node = None
            min_distance = float('inf')
            for node, distance in distances.items():
                if node not in visited and distance < min_distance:
                    min_node = node
                    min_distance = distance

            if min_node is None:
                break  # All remaining nodes are unreachable

            visited.add(min_node)

            # Update distances for neighbors of the current node
            for link, cost in self.link_costs.items():
                if min_node in link:
                    other_node = next(iter(link - {min_node}))
                    total_cost = distances[min_node] + cost
                    if other_node not in distances:
                        distances[other_node] = float('inf')  # Initialize if not present
                    if total_cost < distances[other_node]:
                        distances[other_node] = total_cost
                        predecessors[other_node] = min_node



        # Construct the shortest_paths dictionary
        shortest_paths = {}
        for node, distance in distances.items():
            if node != self.id:
                shortest_paths[node] = [predecessors[node], distance]

        return shortest_paths
