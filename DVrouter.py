####################################################
# DVrouter.py
# Name:
# HUID:
#####################################################

import json

from router import Router
from packet import Packet


class DVrouter(Router):
    """Distance vector routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)  # Initialize base class - DO NOT REMOVE
        self.heartbeat_time = heartbeat_time
        self.last_time = 0
        self.distance_vector = {self.addr: 0}
        self.neighbors_dv = {}
        self.forwarding_table = {}
        self.neighbor_info = {}

    def _update_distance_vector(self):
        """Recalculate distance vector using Bellman-Ford algorithm."""
        new_dv = {self.addr: 0}

        for port, (neighbor_addr, link_cost) in self.neighbor_info.items():
            if neighbor_addr not in new_dv:
                new_dv[neighbor_addr] = link_cost
            else:
                new_dv[neighbor_addr] = min(new_dv[neighbor_addr], link_cost)

            if neighbor_addr in self.neighbors_dv:
                for dest, dist in self.neighbors_dv[neighbor_addr].items():
                    cost = link_cost + dist
                    if dest not in new_dv:
                        new_dv[dest] = cost
                    else:
                        new_dv[dest] = min(new_dv[dest], cost)

        old_dv = self.distance_vector
        self.distance_vector = new_dv
        return old_dv != new_dv

    def _update_forwarding_table(self):
        """Update forwarding table based on current distance vector."""
        new_ft = {}

        for dest in self.distance_vector:
            if dest == self.addr:
                continue

            best_port = None
            best_cost = float('inf')

            for port, (neighbor_addr, link_cost) in self.neighbor_info.items():
                if neighbor_addr == dest:
                    cost = link_cost
                elif neighbor_addr in self.neighbors_dv and dest in self.neighbors_dv[neighbor_addr]:
                    cost = link_cost + self.neighbors_dv[neighbor_addr][dest]
                else:
                    continue

                if cost < best_cost:
                    best_cost = cost
                    best_port = port

            if best_port is not None:
                new_ft[dest] = best_port

        self.forwarding_table = new_ft

    def _broadcast_dv(self):
        """Broadcast distance vector to all neighbors."""
        content = json.dumps(self.distance_vector)
        packet = Packet(Packet.ROUTING, self.addr, None, content=content)
        for port in self.neighbor_info.keys():
            self.send(port, packet)


    def handle_packet(self, port, packet):
        """Process incoming packet."""
        if packet.is_traceroute:
            if packet.dst_addr in self.forwarding_table:
                self.send(self.forwarding_table[packet.dst_addr], packet)
        else:
            sender_addr = packet.src_addr
            received_dv = json.loads(packet.content)

            if sender_addr not in self.neighbors_dv or self.neighbors_dv[sender_addr] != received_dv:
                self.neighbors_dv[sender_addr] = received_dv

                if self._update_distance_vector():
                    self._update_forwarding_table()
                    self._broadcast_dv()
                else:
                    self._update_forwarding_table()

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""
        self.neighbor_info[port] = (endpoint, cost)

        if endpoint not in self.neighbors_dv:
            self.neighbors_dv[endpoint] = {endpoint: 0}

        self._update_distance_vector()
        self._update_forwarding_table()
        self._broadcast_dv()

    def handle_remove_link(self, port):
        """Handle removed link."""
        if port in self.neighbor_info:
            neighbor_addr, _ = self.neighbor_info[port]
            del self.neighbor_info[port]
            if neighbor_addr in self.neighbors_dv:
                del self.neighbors_dv[neighbor_addr]

        self._update_distance_vector()
        self._update_forwarding_table()
        self._broadcast_dv()

    def handle_time(self, time_ms):
        """Handle current time."""
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            self._broadcast_dv()

    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        return f"DVrouter(addr={self.addr}, dv={self.distance_vector})"
