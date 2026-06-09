from router import Router
from packet import Packet
import json

class LSrouter(Router):
    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr) 
        self.heartbeat_time = heartbeat_time
        self.last_time = 0 
        
        self.neighbors = {}

       
        self.graph = {}

       
        self.sequence_numbers = {}
        self.my_seq_num = 0

      
        self.forwarding_table = {}

    def handle_packet(self, port, packet):
       
        if packet.is_traceroute:
            
            if packet.dst_addr == self.addr:
                return
                
          
            if packet.dst_addr in self.forwarding_table:
                self.send(self.forwarding_table[packet.dst_addr], packet)
        else:
            
            try:
                lsp_data = json.loads(packet.content)
            except:
                return

            source_router = lsp_data["source"]
            seq_num = lsp_data["seq"]
            links = lsp_data["links"]

           
            if source_router == self.addr:
                return

            
            if source_router in self.sequence_numbers:
                if seq_num <= self.sequence_numbers[source_router]:
                    return

            
            self.sequence_numbers[source_router] = seq_num
            self.graph[source_router] = links

           
            for n_addr, n_info in self.neighbors.items():
                if n_info["port"] != port:
                  
                    forward_pkt = packet.copy()
                    self.send(n_info["port"], forward_pkt)

          
            self.update_forwarding_table()

    def handle_new_link(self, port, endpoint, cost):
        self.neighbors[endpoint] = {"port": port, "cost": cost}
        
        if self.addr not in self.graph:
            self.graph[self.addr] = {}
        self.graph[self.addr][endpoint] = cost

        self.broadcast_link_state()

    def handle_remove_link(self, port):
        endpoint_to_remove = None
        for endpoint, info in self.neighbors.items():
            if info["port"] == port:
                endpoint_to_remove = endpoint
                break
        
        if endpoint_to_remove:
            if endpoint_to_remove in self.neighbors:
                del self.neighbors[endpoint_to_remove]
            if self.addr in self.graph and endpoint_to_remove in self.graph[self.addr]:
                del self.graph[self.addr][endpoint_to_remove]

            self.broadcast_link_state()

    def handle_time(self, time_ms):
       
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            self.broadcast_link_state()

    def broadcast_link_state(self):
        self.my_seq_num += 1
        my_links = {n_addr: n_info["cost"] for n_addr, n_info in self.neighbors.items()}
        
        lsp_payload = {
            "source": self.addr,
            "seq": self.my_seq_num,
            "links": my_links
        }
        lsp_string = json.dumps(lsp_payload)

        # Phát tán gói tin cho tất cả láng giềng kết nối trực tiếp
        for n_addr, n_info in self.neighbors.items():
            pkt = Packet(Packet.ROUTING, self.addr, n_addr, content=lsp_string)
            self.send(n_info["port"], pkt)

        self.graph[self.addr] = my_links
        self.update_forwarding_table()
    def update_forwarding_table(self):
        distances = {}
        next_hops = {}
        unvisited = set()

        all_nodes = set(self.graph.keys())
        for links in self.graph.values():
            all_nodes.update(links.keys())

        if self.addr not in all_nodes:
            return

        for node in all_nodes:
            distances[node] = float('inf')
            unvisited.add(node)
        distances[self.addr] = 0

        while unvisited:
            current_node = min(unvisited, key=lambda node: distances[node])
            if distances[current_node] == float('inf'):
                break

            unvisited.remove(current_node)
            current_dist = distances[current_node]

            neighbors_of_current = self.graph.get(current_node, {})
            for neighbor, cost in neighbors_of_current.items():
                if neighbor in unvisited:
                    new_dist = current_dist + cost
                    if new_dist < distances[neighbor]:
                        distances[neighbor] = new_dist
                        
                        if current_node == self.addr:
                            next_hops[neighbor] = neighbor
                        else:
                            next_hops[neighbor] = next_hops.get(current_node)

        new_forwarding_table = {}
        for target, next_hop in next_hops.items():
            if next_hop in self.neighbors:
                new_forwarding_table[target] = self.neighbors[next_hop]["port"]

        self.forwarding_table = new_forwarding_table

    def __repr__(self):
        return f"LSrouter(addr={self.addr})" 
