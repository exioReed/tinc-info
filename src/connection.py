import math
import re
import socket
import time


class InvalidRequest(StandardError): pass


class NoConnection(StandardError): pass


class Control(object):
    """
    Handles a connection to tincd via unix socket.
    """
    buf_size = 16
    timeout = 0.6 # seconds

    available_requests = {"REQ_DUMP_NODES": "18 3\n",
                          "REQ_DUMP_EDGES": "18 4\n",
                          "REQ_DUMP_SUBNETS": "18 5\n",
                          "REQ_DUMP_CONNECTIONS": "18 6\n"}

    def __init__(self, netname, rundir='/var/run', reconn=False):
        self.netname = netname
        self.rundir = rundir
        self.pid_file = self._pid_file()
        self.tinc_socket = self._socket()

        self.reconn = reconn
        self.connection = None
        self.cookie = None
        self._parse_pid_file()

    def _pid_file(self):
        return "{rundir}/tinc.{netname}.pid".format(rundir=self.rundir,
                                                    netname=self.netname)

    def _socket(self):
        return "{rundir}/tinc.{netname}.socket".format(rundir=self.rundir,
                                                       netname=self.netname)

    def _parse_pid_file(self):
        """
        Parse cookie from tincd's pid file.
        """
        with open(self.pid_file, "r") as pid_file:
            self.cookie = pid_file.read().split()[1]

    def connect(self):
        """
        Connect to tincd's unix socket.

        :return: Data reveived from the socket after connecting
        """
        if not self.connection:
            self.connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.connection.connect(self.tinc_socket)
            self.connection.settimeout(self.timeout)
            ans = self._get_answer()
            return ans

    def disconnect(self):
        """
        Disconnect from unix socket.
        """
        if self.connection:
            self.connection.close()
            self.connection = None

    def reconnect(self, n=3):
        """
        Tries to reconnect to the socket n times with exponentially increasing
        sleep time after each try. There should be at least one try.
        """
        if n < 1:
            raise ValueError('At least one try required.')

        c = 0
        while c < n:
            try:
                self.disconnect()
                self.connect()
                self.authenticate()
            except IOError as e:
                # errno 2: No such file or directory
                # errno 13: Permission denied
                # errno 32: Broken pipe
                if c == n - 1:
                    raise e
            else:
                break
            c += 1
            time.sleep(self._sleep_time(c))

    def communicate(self, request):
        """
        Send a request to the socket and return its answer.
        Before sending the data the request gets validated.
        """
        try:
            self._send_request(request)
        except (IOError, NoConnection) as e:
            if not self.reconn:
                raise e
            self.reconnect()
            self._send_request(request)

        return self._get_answer()

    def authenticate(self):
        """
        Send the parsed cookie and return the answer.

        :return: Data reveived from the socket after the authentication
        """
        # this is actually ID ^cookie TINC_CTL_VERSION_CURRENT
        auth = "0 ^%s 0\n" % self.cookie
        ans = self.communicate(auth)
        return ans

    def _send_request(self, request):
        if not self.connection:
            raise NoConnection

        if not self._validate_request(request):
            raise InvalidRequest

        if request in self.available_requests:
            req = self.available_requests[request]
        else:
            req = request

        self.connection.send(req)

    def _get_answer(self):
        answer = []
        tmp = " "
        while tmp:
            try:
                tmp = self.connection.recv(self.buf_size)
                answer.append(tmp)
            except socket.timeout:
                tmp = None

        return "".join(answer)

    def _validate_request(self, request):
        return request in self.available_requests or\
               re.match("^0 \^.{64} 0\n$", request)

    def _sleep_time(self, count):
        return int(math.ceil(math.exp(count)))

    def __del__(self):
        self.disconnect()
