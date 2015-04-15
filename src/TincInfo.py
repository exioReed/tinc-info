from TincConn import TincConn


class TincNode(object):
    def __init__(self):
        self.name = None
        self.network = []
        self.peer_info = {}

    def __repr__(self):
        return "%s %s" % (self.name, self.network)

    def add_network(self, network):
        if network not in self.network:
            self.network.append(network)


class PeerInfo(dict): pass


class TincEdge(dict): pass


class TincConnection(dict): pass


class TincInfo(object):

    def __init__(self, netname, rundir='/var/run'):
        self.netname = netname
        self.rundir = rundir
        self.tinc_conn = TincConn(self._pid_file(), self._socket(), True)
        self.tinc_conn.connect()
        self.tinc_conn.authenticate()
        self.connections = []
        self.nodes = {}
        self.edges = []

    def _pid_file(self):
        return "%s/tinc.%s.pid" % (self.rundir, self.netname)

    def _socket(self):
        return "%s/tinc.%s.socket" % (self.rundir, self.netname)

    # parse
    def parse_networks(self):
        answer = self.tinc_conn.communicate("REQ_DUMP_SUBNETS")

        for i in [l.split(" ")[2:] for l in answer.splitlines() if len(l.split(" ")[2:])]:
            net, node_name = i
            node = self.nodes.setdefault(node_name, TincNode())
            node.name = node_name
            node.add_network(net)
        return self.nodes

    def parse_edges(self):
        answer = self.tinc_conn.communicate("REQ_DUMP_EDGES")
        # from, to, host, port, local_host, local_port, &options, &weight
        purpose = ["from", "to", "host", "_a", "port", "local_host",
                   "_b", "local_port", "options", "weight", "avg_rtt"]
        # edges = []
        # for i in [z for z in answer.splitlines() if len(z.split(" ")[2:]) > 0]:
        #     edges.append(self.meta_parse(i.split(" ")[2:], purpose, TincEdge()))

        self.edges = map(lambda i : self.meta_parse(i.split(" ")[2:], purpose, TincEdge()),
                    [z for z in answer.splitlines() if len(z.split(" ")[2:])])

        return self.edges

    def parse_connections(self):
        answer = self.tinc_conn.communicate("REQ_DUMP_CONNECTIONS")
        # connections = []
        # node, host, port, &options, &socket, &status_int
        purpose = ["node", "host", "_a", "port",
                   "options", "socket", "status_int"]

        for i in [z for z in answer.splitlines() if len(z.split(" ")[2:])]:
            self.connections.append(self.meta_parse(i.split(" ")[2:], purpose, TincConnection()))

        return self.connections

    def parse_nodes(self):
        answer = self.tinc_conn.communicate("REQ_DUMP_NODES")
        # node, id, host, port, &cipher, &digest, &maclength, &compression, &options,
        # &status_int, nexthop, via, &distance, &pmtu, &minmtu, &maxmtu, &last_state_change)
        purpose = ['node', 'id', 'host', '_a', 'port', 'cipher', 'digest', 'maclength',
                   'compression', 'options', 'status_int', 'nexthop', 'via', 'distance',
                   'pmtu', 'minmtu', 'maxmtu', 'last_state_change']
        for i in [z for z in answer.splitlines() if len(z.split(" ")[2:])]:
            x = self.meta_parse(i.split(" ")[2:], purpose, PeerInfo())
            n = self.nodes.setdefault(x['node'], TincNode())
            n.peer_info = x

        return self.nodes

    def parse_all(self):
        self.parse_connections()
        self.parse_edges()
        self.parse_networks()
        self.parse_nodes()

    def __del__(self):
        self.tinc_conn.disconnect()

    @staticmethod
    def meta_parse(_tmp, purpose, t_obj):
        # print(_tmp, t_obj)
        # TODO: doesn't make sense
        if len(_tmp) < len(purpose):
            return t_obj

        for k, v in zip(purpose, _tmp):
            t_obj[k] = v

        return t_obj

    # info
    def get_max_weight(self):
        max_weight = 0
        for edge in self.edges:
            if int(edge['weight']) > max_weight:
                max_weight = int(edge['weight'])
        return max_weight

    def edge_count(self, node):
        # return len(filter(lambda i : i['from'] == node, self.edges))
        return len([e for e in self.edges if e['from'] == node])