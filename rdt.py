import math
import re
import struct
from collections import deque

from USocket import UnreliableSocket
import threading
import time
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
        self.client = False
        self._rate = rate
        self._send_to = None
        self._recv_from = None
        self.debug = debug
        self.WIN_SIZE = 4
        self.TIME_LIMIT = 0.1
        self.settimeout(100)
        self.Seq = 0
        self.Ack = 100

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
        self.client = False
        self.setblocking(True)
        while True:
            self.setblocking(True)
            try:
                data, address = self.recvfrom(100 * RDTSegment.SEGMENT_LEN)
            except TypeError:
                continue
            print("receive accept at address: " + str(address))
            handShake = RDTSegment.parse(data)
            print("accept seq:" + str(handShake.seq_num) + " ack:" + str(handShake.ack_num))
            # if handShake.calc_checksum(data) != handShake.checksum or not handShake.syn:
            if not handShake.syn:
                print("checkSum/not SYN")
                continue
            # TODO: CHECK CHECKSUM

            # elif RDTSegment.calc_checksum(data)!=handShake.checksum:
            #     print(RDTSegment.calc_checksum(data))
            #     print("checkSum")
            #     continue
            sock = RDTSocket()
            sock.bind(('127.0.0.1', 0))
            self.setblocking(False)
            self.Ack = handShake.seq_num + 1
            self.Seq = handShake.ack_num
            send_addr = sock.getsockname()
            payload = send_addr[0] + ':' + str(send_addr[1])
            handShake2 = RDTSegment(syn=True, seq_num=self.Seq, ack=True, ack_num=self.Ack, payload=payload.encode(),
                                    len=len(payload.encode()))
            # print(len(handShake2.payload))
            print("send ack: " + str(self.Ack) + "  seq:" + str(self.Seq))
            self.sendto(handShake2.encode(), address)
            print("send syn at accept to address: " + str(address))
            conn, addr = sock, address
            conn._send_to = address
            conn._recv_from = address
            # 接收确认地址？
            break

        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################

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
        self.client = True
        self.setblocking(flag=False)
        handShake_1 = RDTSegment(syn=True, seq_num=self.Seq, ack_num=self.Ack)
        print("send handshake1. seq:" + str(self.Seq) + " ack:" + str(self.Ack))
        while True:
            self.sendto(handShake_1.encode(), address)
            print("send first handshake")
            time.sleep(1)
            try:
                data, addr_1 = self.recvfrom(100 * RDTSegment.SEGMENT_LEN)
            except BlockingIOError:
                time.sleep(1)
                continue
            except TypeError:
                time.sleep(1)
                continue
            print("recv data at address: " + str(address))

            handShake_2 = RDTSegment.parse(data)
            addr_str = handShake_2.payload.decode().split(':')
            address = (addr_str[0], int(addr_str[1]))

            print("recv seq:" + str(handShake_2.seq_num) + " ack:" + str(handShake_2.ack_num))
            # if handShake_2.syn and handShake_2.ack and handShake_2.ack_num == self.Seq + 1:
            # todo: determine seq and ack in connection
            if handShake_2.syn and handShake_2.ack:
                print("receive syn ack correctly")
                break
            else:
                time.sleep(1)
        self.Seq += 1
        self.Ack = handShake_2.ack_num + 1

        self.Ack = handShake_2.seq_num + 1
        self.Seq = handShake_2.ack_num
        handShake_3 = RDTSegment(seq_num=self.Seq, ack_num=self.Ack, ack=True, syn=True)
        print("send handshake3. seq:" + str(self.Seq) + " ack:" + str(self.Ack))
        self.sendto(handShake_3.encode(), address)
        # 重复确认？
        print("finish connect")
        self._recv_from = address
        self._send_to = address

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
        buffer = []
        expected = 0
        ack = RDTSegment(seq_num=0, ack_num=expected, ack=True)
        OOOseg = []
        while True:
            try:
                segment_raw, remote_addr = self.recvfrom(100 * RDTSegment.SEGMENT_LEN)
            except BlockingIOError:
                continue

            # addr判断？
            # print("recv data")
            if remote_addr != self._recv_from: continue
            # todo: checkSum checking
            segment = RDTSegment.parse(segment_raw)
            if RDTSegment.check_checksum(segment, segment_raw): continue
            print("receiver recv, seq:" + str(segment.seq_num))
            if segment.fin:
                ack.ack_num = segment.seq_num + 1
                self.sendto(ack.encode(), remote_addr)
                data.extend(segment.payload)
                print("receiver send, ack: ", ack.ack_num)
                break
            if segment.syn: continue
            if segment.seq_num == expected:
                data.extend(segment.payload)
                expected = expected + 1
                # 判断queue
                flag = False
                while len(buffer) != 0 and buffer[0].seq_num == expected:
                    queue_seg = buffer[0]
                    buffer.pop(0)
                    data.extend(queue_seg.payload)
                    expected += 1
                    flag = True

                if flag:
                    OOOseg.pop(0)
                    if len(OOOseg) != 0:
                        ack.SLE, ack.SRE = OOOseg[0]
                    else:
                        ack.SLE, ack.SRE = (-1, -1)
                ack.ack_num = expected
                self.sendto(ack.encode(), remote_addr)
                print("receiver send, ack: ", ack.ack_num)
            elif segment.seq_num > expected:

                if len(OOOseg) == 0 or segment.seq_num != OOOseg[-1][1]:
                    buffer.append(segment)
                    OOOseg.append((segment.seq_num, (segment.seq_num + segment.len) % RDTSegment.SEQ_NUM_BOUND))
                    temp = OOOseg[0]
                    (ack.SLE, ack.SRE) = OOOseg[0]
                    self.sendto(ack.encode(), remote_addr)
                    print("receiver send, ack: ", ack.ack_num)
                else:
                    buffer.append(segment)
                    OOOseg[-1][1] = (OOOseg[-1][1] + segment.len) % RDTSegment.SEQ_NUM_BOUND
                    self.sendto(ack.encode(), remote_addr)
                    print("receiver send, ack: ", ack.ack_num)

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
            pkt_list.append(data[i * pld_size: (i + 1) * pld_size])

        finished = False
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
                # tmp = seq.encode()
                # detmp = RDTSegment.parse(tmp)
                print("sender send, seq:", nxt, "base:", base)
                nxt += 1

            if not timer.running():
                timer.start()

            while timer.running() and not timer.timeout():
                try:
                    segment_raw, remote_addr = self.recvfrom(100 * RDTSegment.SEGMENT_LEN)
                    # print(len(segment_raw), remote_addr)
                except BlockingIOError:
                    continue
                # if remote_addr != self._recv_from:
                #     continue
                segment = RDTSegment.parse(segment_raw)
                print("sender recv, ack:", segment.ack_num, "fin:", pkt_len - 1)
                # todo: if wrong checksum of segment: continue
                if segment.ack_num == pkt_len:
                    finished = True
                    break
                if base <= segment.ack_num - 1 < lim:
                    base = segment.ack_num
                    break

            if finished:
                return

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
        finpkt = RDTSegment(fin=True, seq_num=0, ack_num=0)
        self.sendto(finpkt.encode(), self._send_to)
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        super().close()

    def set_send_to(self, send_to):
        self._send_to = send_to

    def set_recv_from(self, recv_from):
        self._recv_from = recv_from


"""
You can define additional functions and classes to do thing such as packing/unpacking packets, or threading.

"""
