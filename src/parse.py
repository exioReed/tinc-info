import sys


class ConvertDatatypeDict(dict):
    """
    A dict that converts values for certain keys.

    The keys for which the corresponding value should be converted can be
    specified via the attributes self.decs and self.hexs.

    The conversion must be done explicitly via convert_datatypes(self)

    self.decs: A list of keys for which the values are interpreted as
     *decimal* integer literals.
    self.hexs: A list of keys for which the values are interpreted as
     *hexadecimal* integer literals.

    The value -1 represents an unknown/invalid value for every key in self.decs
    and self.hexs.
    """
    decs = []
    hexs = []

    def convert_datatypes(self):
        """
        Converts datatypes for the keys specified in self.decs and self.hexs
        """
        self._convert2int(self.decs, 10)
        self._convert2int(self.hexs, 16)

    def _convert2int(self, keys, base=10, err_val=-1):
        for k in keys:
            if self.get(k):
                try:
                    self[k] = int(self[k], base)
                except ValueError:
                    self[k] = err_val


class TincNode(object):
    """
    Represents a node of a tinc VPN.
    """
    def __init__(self):
        """
        Initialize TincNode object
        """
        self.name = None
        """Node name"""
        self.network = []
        """List of networks owned by the node"""
        self.peer_info = {}
        """Dictionary with further information about that node. See PeerInfo"""

    def __repr__(self):
        return "%s %s" % (self.name, self.network)

    def add_network(self, network):
        """
        Adds a network to the list of networks if it's not in the list already.

        :param network: Network to add
        """
        if network not in self.network:
            self.network.append(network)


class PeerInfo(ConvertDatatypeDict):
    """
    Represents information about a node of a tinc VPN.

    node, id, host, port, cipher, digest, maclength, compression, options,
    status_int, nexthop, via, distance, pmtu, minmtu, maxmtu, last_state_change
    """
    decs = ['port', 'distance', 'pmtu', 'minmtu', 'maxmtu',
            'last_state_change']
    hexs = ['cipher', 'digest', 'maclength', 'compression', 'options',
            'status_int']


class TincEdge(ConvertDatatypeDict):
    """
    Represents an edge of a tinc VPN.

    from, to, host, local_host, local_port, options, weight, avg_rtt

    Depending on the protocol version of tincd avg_rtt may not be defined.
    """
    decs = ['port', 'local_port', 'weight', 'avg_rtt']
    hexs = ['options']


class TincConnection(ConvertDatatypeDict):
    """
    Represents a meta connection of a tinc VPN.

    node, host, port, options, socket, status_int
    """
    decs = ['port']
    hexs = ['options', 'status_int']


class TincInfo(object):
    """
    TincInfo parses data retrieved from tincd's control socket.
    """
    def __init__(self):
        """
        Initialize TincInfo object
        """
        self.connections = []
        self.nodes = {}
        self.edges = []

    # parse
    def parse_networks(self, data=None):
        """
        Parse all known subnets in the VPN and store them in the network list
        of the corresponding node.

        If parse_nodes() was executed before peer_info is also present.

        :param data: Data to parse. If not specified ValueError will be raised.

        :return: A dictionary of nodes
        """
        if not data:
            raise ValueError('No data to parse networks given.')

        for line in [l for l in data.splitlines() if len(l.split(" ")[2:])]:
            i = line.split(" ")[2:]
            try:
                net, node_name = i
            except ValueError as ve:
                print('Cannot parse line [{}]'.format(line))
                raise ve
            node = self.nodes.setdefault(node_name, TincNode())
            node.name = node_name
            node.add_network(net)
        return self.nodes

    def parse_edges(self, data=None):
        """
        Parse all known connections in the VPN and store the information
        in a list of edges. An edge holds the following information:

        from, to, host, local_host, local_port, options, weight, avg_rtt

        Depending on the protocol version of tincd avg_rtt may not be defined.

        :param data: Data to parse. If not specified ValueError will be raised.

        :return: A list of edges
        """

        if not data:
            raise ValueError('No data to parse edges given.')

        # from, to, host, port, local_host, local_port, &options, &weight
        purpose = ["from", "to", "host", "_a", "port", "local_host",
                   "_b", "local_port", "options", "weight", "avg_rtt"]
        # edges = []
        # for i in [z for z in answer.splitlines() if len(z.split(" ")[2:]) > 0]:
        #     edges.append(self.meta_parse(i.split(" ")[2:], purpose, TincEdge()))

        self.edges = map(lambda i : self.meta_parse(i.split(" ")[2:], purpose, TincEdge()),
                    [z for z in data.splitlines() if len(z.split(" ")[2:])])

        return self.edges

    def parse_connections(self, data=None):
        """
        Parse all meta connections and store information in a list.
        A connection holds the following information:

        node, host, port, options, socket, status_int

        :param data: Data to parse. If not specified ValueError will be raised.

        :return: A list of meta connections
        """
        if not data:
            raise ValueError('No data to parse connections given.')

        # connections = []
        # node, host, port, &options, &socket, &status_int
        purpose = ["node", "host", "_a", "port",
                   "options", "socket", "status_int"]

        for i in [z for z in data.splitlines() if len(z.split(" ")[2:])]:
            self.connections.append(self.meta_parse(i.split(" ")[2:], purpose, TincConnection()))

        return self.connections

    def parse_nodes(self, data=None):
        """
        Parse information about all known nodes in the VPN.
        The peer_info of a node holds the following information:

        node, id, host, port, cipher, digest, maclength, compression, options,
        status_int, nexthop, via, distance, pmtu, minmtu, maxmtu,
        last_state_change

        If parse_networks() was excecuted before the networks owned by a node
        are also present.

        :param data: Data to parse. If not specified ValueError will be raised.

        :return: A dictionary of nodes where nodes[nodename].peer_info contains
        the mentioned information.
        """
        if not data:
            raise ValueError('No data to parse nodes given.')

        # node, id, host, port, &cipher, &digest, &maclength, &compression, &options,
        # &status_int, nexthop, via, &distance, &pmtu, &minmtu, &maxmtu, &last_state_change)
        purpose = ['node', 'id', 'host', '_a', 'port', 'cipher', 'digest', 'maclength',
                   'compression', 'options', 'status_int', 'nexthop', 'via', 'distance',
                   'pmtu', 'minmtu', 'maxmtu', 'last_state_change']
        for i in [z for z in data.splitlines() if len(z.split(" ")[2:])]:
            x = self.meta_parse(i.split(" ")[2:], purpose, PeerInfo())
            n = self.nodes.setdefault(x['node'], TincNode())
            n.peer_info = x

        return self.nodes

    @staticmethod
    def meta_parse(_tmp, purpose, t_obj):
        for k, v in zip(purpose, _tmp):
            t_obj[k] = v

        t_obj.convert_datatypes()
        return t_obj

    # info
    def get_max_weight(self):
        """
        Compute the maximal weight of all parsed edges.

        :return: The maximal weight
        """
        max_weight = 0
        for edge in self.edges:
            if int(edge['weight']) > max_weight:
                max_weight = int(edge['weight'])
        return max_weight

    def get_min_weight(self):
        """
        Compute the minimal weight of all parsed edges.

        :return: The minimal weight
        """
        min_weight = sys.maxint
        for edge in self.edges:
            if int(edge['weight']) < min_weight:
                min_weight = int(edge['weight'])
        return min_weight

    def edge_count(self, node):
        """
        Compute the count of edges for a given node name.

        :param node: The node name
        :return: Edge count
        """
        # return len(filter(lambda i : i['from'] == node, self.edges))
        return len([e for e in self.edges if e['from'] == node])
