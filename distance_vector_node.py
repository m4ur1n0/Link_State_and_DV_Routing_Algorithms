import copy
from simulator.node import Node
import json
import math
# ---------------------------------------------------
# ROUTING MESSAGE STRUCTURE
# "SENDER|SEQ|[DISTANCE_VECTOR]" 
# ---------------------------------------------------

class Distance_Vector_Node(Node):    

    def __init__(self, id):
        super().__init__(id)

        self.id = id
        # DV STRUCTURE:
        # {node2 : [[path, to, node2], latency, learned_from]}
        # node1.dv[node2][0] == path to node2
        # node1.dv[node2][1] == latency of that path
        # node1.dv[node2][2] == learned_from, the node where node1 learned
        # this path, this is stored for implementation of split horizons
        self.dv = {self.id : [self.id, 0, -1]}
        
        # NEIGHBORS DICT STRUCTURE:
        # {neighbor : [most_recent_dv, seq, latency]}
        # node1.neighbors[neighbor][0] == that n's DV
        # node1.neighbors[neighbor][1] == that n's seq
        # node1.neighbors[neighbor][2] == latency to that neighbor
        self.neighbors = {}
        
        # seq num starts at 1, save new neighbors w seq = 0
        self.seq = 1

    def __str__(self):
        # return f"NODE ID: {self.id}\nNEIGHBORS: {self.neighbors}\nSEQ: {self.seq}\nDV: {self.dv}"
        retstr = f"----------------------------------\nNODE: {self.id}\nNEIGHBORS:\n"
        for n in self.neighbors:
            retstr += f"{n} : {self.neighbors[n][2]}\n"

        retstr += "\nPATHS:\n"

        for d in self.dv:
            retstr += f"{d} : {self.dv[d][0]} : {self.dv[d][1]}\n"

        retstr += "----------------------------------"
        return retstr


    def responsible_flood(self):
        # send out dv ONLY including nodes not learned from node we send to
        for n in self.neighbors:
            dv_to_transmit = {}
            for node in self.dv:
                if self.dv[node][2] != n:
                    # if we did not learn this path from n, we can share
                    dv_to_transmit[node] = self.dv[node]
            
            if dv_to_transmit != {}:
                dva = f"{self.id}|{self.seq}|" + json.dumps(dv_to_transmit)
                self.send_to_neighbor(n, dva)
        
        self.seq += 1

    def link_has_been_updated(self, neighbor, latency):
        
        if neighbor not in self.neighbors and latency != -1:
            # case 1: brand new neighbor/link
            # give neighbor a stored seq of 0
            # default DV of empty dict, learned from -1
            self.neighbors[neighbor] = [{}, 0, latency]
            self.dv[neighbor] = [[neighbor], latency, neighbor]
            self.recompute_own_dv()
            # there was definitely a change
            self.responsible_flood()
        
        elif neighbor in self.neighbors and latency != -1:
            # case 2: neighbor exists, but a change in latency
            old_lat = self.dv[neighbor][1]
            if old_lat != latency:
                self.dv[neighbor][1] = latency
                self.neighbors[neighbor][2] = latency
                self.recompute_own_dv()
                # a change has definitely taken place
                
                self.responsible_flood()
        else:
            # case 3: a link/neighbor has been deleted
            del self.neighbors[neighbor]
            self.dv[neighbor] = [[neighbor], math.inf, neighbor]
            print(f"{self.id} lost connection to {neighbor}")
            self.recompute_own_dv(poisoned_node=neighbor)
            self.responsible_flood()

    def recompute_own_dv(self, poisoned_node=-15):
        # REFERENCE --------------------------------------
        # DV STRUCTURE:
        # {node2 : [[path, to, node2], latency, learned_from]}
        # node1.dv[node2][0] == path to node2
        # node1.dv[node2][1] == latency of that path
        # node1.dv[node2][2] == learned_from, the node where node1 learned
        # this path, this is stored for implementation of split horizons
        
        # NEIGHBORS DICT STRUCTURE:
        # {neighbor : [most_recent_dv, seq, latency]}
        # node1.neighbors[neighbor][0] == that n's DV
        # node1.neighbors[neighbor][1] == that n's seq
        # node1.neighbors[neighbor][2] == latency to that neighbor
        # END REFERENCE --------------------------------------
        
        # start a new dv
        new_dv = {self.id : [[self.id], 0, -1]}

        for n in self.neighbors:
            # for each neighbor, log our link to new dv
            new_dv[n] = [[n], self.neighbors[n][2], n]

        # now we optimize paths to neighbors
        for n in self.neighbors:
            # now we steal our neighbors paths (where useful)
            neighbor_dv = self.neighbors[n][0]
            for n2 in neighbor_dv:
                if n2 in self.neighbors:
                    # only looking at possible paths where dst is a neighbor
                    neighbor_path_to_n2 = neighbor_dv[n2][0]
                    neighbor_latency = neighbor_dv[n2][1]

                    cost_to_neighbor = new_dv[n][1] 

                    if cost_to_neighbor + neighbor_latency < new_dv[n2][1] and self.id not in neighbor_path_to_n2:
                        # MIGHT BE MORE TO CHECK HERE
                        # print(f"found new path from {self.id} to neighbor {n2} : {neighbor_path_to_n2}  @  {neighbor_latency}\nFOUND FROM {n}")
                        new_dv[n2] = [[n] + neighbor_path_to_n2, neighbor_latency + cost_to_neighbor, n]
            


        
        for n in self.neighbors:
            # now we steal our neighbors paths (where useful)
            neighbor_dv = self.neighbors[n][0]
            for dst in neighbor_dv:
                if dst not in self.neighbors:
                    neighbor_path_to_dst = neighbor_dv[dst][0]
                    neighbor_latency = neighbor_dv[dst][1]

                    cost_to_neighbor = new_dv[n][1]

                    if neighbor_latency != math.inf and (dst not in new_dv or cost_to_neighbor + neighbor_latency < new_dv[dst][1]) and self.id not in neighbor_path_to_dst:
                        flag = 0

                        for neigh in self.neighbors:
                            if neigh in neighbor_path_to_dst and neigh != n:
                                flag = 1
                        
                        if flag == 0:
                            # only add the path if it doesn't include
                            # print(f"found new path from {self.id} to {dst} : {neighbor_path_to_dst}  @  {neighbor_latency}\nFOUND FROM {n}")

                            new_dv[dst] = [new_dv[n][0] + neighbor_path_to_dst, neighbor_latency + cost_to_neighbor, n]

        
        # print(self)
        self.dv = new_dv
        

    def process_incoming_routing_message(self, m):
        # FOR REFERENCE 
        # DV STRUCTURE:
        # {node2 : [[path, to, node2], latency, learned_from]}
        # node1.dv[node2][0] == path to node2
        # node1.dv[node2][1] == latency of that path
        # node1.dv[node2][2] == learned_from, the node where node1 learned
        # this path, this is stored for implementation of split horizons
        # learned_from == -1 when it is just a neighbor i know

        # NEIGHBORS DICT STRUCTURE:
        # {neighbor : [most_recent_dv, seq]}
        # node1.neighbors[neighbor][0] == that n's DV
        # node1.neighbors[neighbor][1] == that n's seq
        # END REFERENCE

        if '|' not in m:
            # not a real dva
            return
        parts = m.split('|')

        def int_keys_hook(d):
               return {int(k): v for k, v in d.items()}
        
        sndr, seq, recvd_dv = int(parts[0]), int(parts[1]), json.loads(parts[2], object_hook=int_keys_hook)

        if sndr not in self.neighbors:
            # if self.id in recvd_dv:
            #     # new neighbor, add them (MIGHT BE WRONG)
            #     self.neighbors[sndr] = [recvd_dv, seq, recvd_dv[self.id][1]]
            #     # the only way this index won't work is if we some how
            #     # received a dv from someone who isn't our neighbor 
            #     self.dv[sndr] = [[sndr], recvd_dv[self.id][1], -1]

            # else:
            #     # how did they get my number?
            #     return
            return
            
        if seq > self.neighbors[sndr][1]:
            # >= because it doesn't hurt if we've heard it before
            # and there could be a glitch case where its useful

            # don't trust it too much, keep the latency we've got, if it
            # changes, we'll hear about it
            self.neighbors[sndr] = [recvd_dv, seq, self.neighbors[sndr][2]]

            # IF WE END UP NEEDING TO POISON INCREASED LINKS, EDIT HERE
        
        old_dv = self.dv
        self.recompute_own_dv()

        if old_dv != self.dv:
            # something changed, share w the world
            self.responsible_flood()



    def get_next_hop(self, destination):
        # return first step in path to dst if exists, else -1
        if destination in self.dv and self.dv[destination][1] != math.inf:
            return self.dv[destination][0][0]
        else:
            return -1