import math
from collections import deque
from socket import socket, AF_INET, SOCK_DGRAM

from USocket import UnreliableSocket, sockets
from util.RDTSegment import RDTSegment
from util.timer import Timer


class RDTSocket(UnreliableSocket):
    """
    The functions with which you are to build your RDT.
    -   recvfrom(bufsize)->bytes, addr
    -   sendto(bytes, address)
    -   bind(address)

    You can set the mode of the socket.
    -   settimeout(timeout)
    -   setblocking(flag)
    By default, a socket is created in the blocking mode. 
    https://docs.python.org/3/library/socket.html#socket-timeouts

    """

    def __init__(self, rate=None, debug=True):
        super().__init__(rate=rate)
        self._rate = rate
        self._send_to = None
        self._recv_from = None
        self.debug = debug
        self.WIN_SIZE = 4
        self.TIME_LIMIT = 0.1
        self.settimeout(100)
        #############################################################################
        # TODO: ADD YOUR NECESSARY ATTRIBUTES HERE
        #############################################################################

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def accept(self) -> ('RDTSocket', (str, int)):
        """
        Accept a connection. The socket must be bound to an address and listening for 
        connections. The return value is a pair (conn, address) where conn is a new 
        socket object usable to send and receive data on the connection, and address 
        is the address bound to the socket on the other end of the connection.

        This function should be blocking. 
        """
        conn, addr = RDTSocket(self._rate), None
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        conn, addr = conn.accept()
        self._recv_from = addr
        self._send_to = addr
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return conn, addr

    def connect(self, address: (str, int)):
        """
        Connect to a remote socket at address.
        Corresponds to the process of establishing a connection on the client side.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        sockets[id(self)].connect(address)
        self._send_to = address
        self._recv_from = address
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def recv(self, bufsize: int) -> bytes:
        """
        Receive data from the socket.
        The return value is a bytes object representing the data received. 
        The maximum amount of data to be received at once is specified by bufsize. 
        
        Note that ONLY data send by the peer should be accepted.
        In other words, if someone else sends data to you from another address,
        it MUST NOT affect the data returned by this function.
        """
        data = bytearray()
        assert self._recv_from, "Connection not established yet. Use recvfrom instead."
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################

        # needed:
        # expected(From connection part)
        # peer_address
        buffer = deque(maxlen=bufsize)
        expected = 0
        ack = RDTSegment(seq_num=0, ack_num=expected, ack=True)
        peer_addr = self._recv_from
        OOOseg = deque()
        while True:
            segment_raw, remote_addr = self.recvfrom(RDTSegment.SEGMENT_LEN)
            # addr判断？
            if remote_addr != peer_addr:continue
            # todo: checkSum checking
            segment = RDTSegment.parse(segment_raw)
            if segment.fin: break
            if segment.seq_num == expected:
                data.extend(segment.payload)
                expected = (expected + segment.len) % RDTSegment.SEQ_NUM_BOUND
                # 判断queue
                flag = False
                while len(buffer) != 0 and buffer[0].seq_num == expected:
                    queue_seg = buffer.popleft()
                    data.extend(queue_seg.payload)
                    expected = (expected + queue_seg.len) % RDTSegment.SEQ_NUM_BOUND
                    flag = True

                if flag:
                    OOOseg.popleft()
                    if len(OOOseg) != 0:
                        ack.SLE, ack.SRE = OOOseg[0]
                    else:
                        ack.SLE, ack.SRE = (-1, -1)
                ack.ack_num = expected
                self.sendto(ack.encode(), remote_addr)
            elif segment.seq_num > expected:
                try:
                    assert len(buffer) != buffer.maxlen
                    if len(OOOseg) == 0 or segment.seq_num != OOOseg[-1][1]:
                        buffer.extend(segment)
                        OOOseg.extend((segment.seq_num, (segment.seq_num + segment.len)) % RDTSegment.SEQ_NUM_BOUND)
                        ack.SLE, ack.SRE = OOOseg[0]
                        self.sendto(ack.encode(), remote_addr)
                    else:
                        buffer.extend(segment)
                        OOOseg[-1][1] = (OOOseg[-1][1] + segment.len) % RDTSegment.SEQ_NUM_BOUND
                        self.sendto(ack.encode(), remote_addr)
                except AssertionError:
                    print("buffer is full, ignore")

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return data

    def send(self, data: bytes):
        """
        Send data to the socket. 
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """
        assert self._send_to, "Connection not established yet. Use sendto instead."
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################

        data_len = len(data)
        pld_size = RDTSegment.MAX_PAYLOAD_LEN

        pkt_list = []
        pkt_len = int(math.ceil(float(data_len) / pld_size))
        base = 0
        nxt = 0
        timer = Timer(self.TIME_LIMIT)

        for i in range(pkt_len):
            pkt_list.append(data[i * pld_size: i * (pld_size + 1)])

        while base < pkt_len:
            lim = min(base + self.WIN_SIZE, pkt_len)
            while nxt < lim:
                # send pkt[nxt]
                # if nxt == pkt_len - 1: FIN = 1, break
                fin = False
                if nxt == pkt_len - 1:
                    fin = True
                seq = RDTSegment(payload=pkt_list[nxt], seq_num=nxt, ack_num=nxt, fin=fin, len=len(pkt_list[nxt]))
                self.sendto(seq.encode(), self._send_to)
                nxt += 1

            if not timer.running():
                timer.start()

            while timer.running() and not timer.timeout():
                segment_raw, remote_addr = self.recvfrom(RDTSegment.SEGMENT_LEN)
                if remote_addr != self._recv_from:
                    continue
                segment = RDTSegment.parse(segment_raw)
                # todo: if wrong checksum of segment: continue
                if base <= segment.ack_num < lim:
                    base = segment.ack_num + 1
                    if nxt == base:
                        nxt += 1
                    break

            if timer.timeout():
                timer.stop()
                nxt = base

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def close(self):
        """
        Finish the connection and release resources. For simplicity, assume that
        after a socket is closed, neither futher sends nor receives are allowed.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        super().close()


"""
You can define additional functions and classes to do thing such as packing/unpacking packets, or threading.

"""
