import math
import re
import socket
import time


class InvalidRequest(StandardError): pass


class NoConnection(StandardError): pass


class TincConn(object):
    buf_size = 16
    timeout = 0.6 # seconds

    reconn_tries = 3

    available_requests = {"REQ_DUMP_NODES": "18 3\n",
                          "REQ_DUMP_EDGES": "18 4\n",
                          "REQ_DUMP_SUBNETS": "18 5\n",
                          "REQ_DUMP_CONNECTIONS": "18 6\n"}

    def __init__(self, pid_file, tinc_socket, reconn = False):
        self.pid_file = pid_file
        self.tinc_socket = tinc_socket

        self.reconn = reconn
        self.connection = None
        self.cookie = None
        self._parse_pid_file()

    def _parse_pid_file(self):
        with open(self.pid_file, "r") as pid_file:
            self.cookie = pid_file.read().split()[1]

    def connect(self):
        if not self.connection:
            self.connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.connection.connect(self.tinc_socket)
            self.connection.settimeout(self.timeout)
            ans = self._get_answer()
            return ans

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def reconnect(self):
        c = 0
        while c < self.reconn_tries:
            try:
                self.disconnect()
                self.connect()
                self.authenticate()
            except IOError as e:
                # errno 2: No such file or directory
                # errno 13: Permission denied
                # errno 32: Broken pipe
                if c == self.reconn_tries - 1:
                    raise e
            else:
                break
            c += 1
            time.sleep(self._sleep_time(c))

    def communicate(self, request):
        try:
            self._send_request(request)
        except (IOError, NoConnection) as e:
            if not self.reconn:
                raise e
            self.reconnect()
            self._send_request(request)

        return self._get_answer()

    def authenticate(self):
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
