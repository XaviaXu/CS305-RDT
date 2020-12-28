import math
import re
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
        self.cwnd = 1.0
        self.sst=2
        self.TIME_LIMIT = 1
        self.settimeout(100)
        self.Seq = 0
        self.Ack = 100
        self.recv_close = False

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
            sock.setblocking(False)
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
            #adding: 3rd handshake timeout
            time.sleep(1)
            # while True:
            #     try:
            #         data, addr_1 = self.recvfrom(100 * RDTSegment.SEGMENT_LEN)
            #     except BlockingIOError:
            #         self.sendto(handShake2.encode(), address)
            #         time.sleep(1)
            #         continue
            #     break
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
        ack = RDTSegment(seq_num=expected, ack_num=expected, ack=True)
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
            #todo: check gfin
            segment = RDTSegment.parse(segment_raw)
            print("receiver recv, seq:" + str(segment.seq_num))

            if segment.gfin:
                print("recv global fin")
                ack.ack_num = segment.seq_num+1
                ack.seq_num = segment.seq_num+1
                self.sendto(ack.encode(),self._send_to)
                print("send second handshake")
                self.recv_close = True
                return data
            if segment.seq_num == expected:
                data.extend(segment.payload)
                # print(segment.payload.decode())
                expected = expected + 1
                if segment.fin:
                    ack.ack_num = expected
                    ack.seq_num = ack.ack_num
                    self.sendto(ack.encode(), remote_addr)

                    print("receiver send, ack:", ack.ack_num)
                    print("recv FIN pkt")
                    break

                # flag = False
                while len(buffer) != 0 and buffer[0].seq_num == expected:
                    queue_seg = buffer[0]
                    buffer.pop(0)
                    data.extend(queue_seg.payload)
                    # print(segment.payload.decode())
                    expected += 1
                    print("add out-of-order pkt.seq:",queue_seg.seq_num,"expected",expected)
                    if queue_seg.fin:
                        ack.ack_num = expected
                        ack.seq_num = expected
                        self.sendto(ack.encode(),remote_addr)
                        print("receiver send, ack:", ack.ack_num)
                        print("recv FIN pkt")
                        return data
                    # flag = True

                # if flag:
                #     OOOseg.pop(0)
                #     if len(OOOseg) != 0:
                #         ack.SLE, ack.SRE = OOOseg[0]
                #     else:
                #         ack.SLE, ack.SRE = (-1, -1)
                ack.ack_num = expected
                ack.seq_num = ack.ack_num
                self.sendto(ack.encode(), remote_addr)
                print("receiver send, ack:", ack.ack_num)
            elif segment.seq_num > expected:
                if expected==0:
                    continue
                buffer.append(segment)
                buffer.sort(key=lambda x: x.seq_num)
                self.sendto(ack.encode(), remote_addr)
                print("recv out-of-order segment,recv:",segment.seq_num,"expected:",expected)
                print("receiver send, ack:", ack.ack_num)
            else:
                self.sendto(ack.encode(), remote_addr)
                print("recv out-of-order segment,recv:", segment.seq_num, "expected:", expected)
                print("receiver send, ack:", ack.ack_num)



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
            lim = min(base + self.cwnd, pkt_len)
            while nxt < lim:
                # send pkt[nxt]
                # if nxt == pkt_len - 1: FIN = 1, break
                fin = False
                if nxt == pkt_len - 1:
                    fin = True
                seq = RDTSegment(payload=pkt_list[nxt], seq_num=nxt, ack_num=nxt, fin=fin, len=len(pkt_list[nxt]))
                # print(pkt_list[nxt].decode())
                self.sendto(seq.encode(), self._send_to)
                # tmp = seq.encode()
                # detmp = RDTSegment.parse(tmp)
                print("sender send, seq:", nxt, "base:", base, "lim:", lim)
                nxt += 1

            if not timer.running():
                timer.start()

            while timer.running() and not timer.timeout():
                # print("loop")
                try:
                    segment_raw, remote_addr = self.recvfrom(100 * RDTSegment.SEGMENT_LEN)
                    # print(len(segment_raw), remote_addr)
                except BlockingIOError:
                    continue
                # if remote_addr != self._recv_from:
                #     continue
                segment = RDTSegment.parse(segment_raw)
                if self.cwnd <= self.sst:
                    self.cwnd += 1
                else:
                    self.cwnd += 1.0 / self.cwnd
                print("sender recv, ack:", segment.ack_num, "fin:", pkt_len - 1, "cwnd:", self.cwnd)
                # todo: if wrong checksum of segment: continue
                # if segment.ack_num == pkt_len:
                #     finished = True
                #     break
                if base <= segment.ack_num - 1 < lim:
                    base = segment.ack_num
                    timer.stop()
                    break

            # if finished:
            #     return

            if timer.timeout():
                timer.stop()
                nxt = base
                self.sst = int(self.cwnd / 2)
                self.cwnd = 1.0

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
        # finpkt = RDTSegment(fin=True, seq_num=0, ack_num=0)
        # self.sendto(finpkt.encode(), self._send_to)
        if self.recv_close:
            print("close passively")
            finpkt = RDTSegment(fin=True,gfin=True,seq_num=10,ack_num=10)
            timer = Timer(self.TIME_LIMIT)
            while True:
                print("send third handshake")
                self.sendto(finpkt.encode(), self._send_to)
                timer.start()
                while timer.running() and not timer.timeout():
                    # print("timer running")
                    try:
                        data_raw, addr = self.recvfrom(100*RDTSegment.SEGMENT_LEN)
                    except BlockingIOError:
                        continue
                    #TODO: ADD CHECKSUM CHECK
                    data = RDTSegment.parse(data_raw)
                    if data.ack_num==finpkt.seq_num+1 and data.ack:
                        print("recv fourth handshake")
                        timer.stop()
                if not timer.timeout() and not timer.running():
                    break
                if timer.timeout():
                    timer.stop()
                    print("timeout, retransmit third handshake")
        else:
            print("close actively")
            #首次提出关闭请求
            finpkt = RDTSegment(gfin=True,fin=True,seq_num=0,ack_num=0)

            timer = Timer(self.TIME_LIMIT)
            while True:
                self.sendto(finpkt.encode(),self._send_to)
                print("send first handshake")
                timer.start()
                while timer.running() and not timer.timeout():
                    try:
                        data_raw, addr = self.recvfrom(100*RDTSegment.SEGMENT_LEN)
                    except BlockingIOError:
                        continue
                    #TODO: ADD CHECKSUM CHECK
                    data = RDTSegment.parse(data_raw)
                    if data.gfin:
                        print("recv third handshake")
                        timer.stop()
                if not timer.timeout() and not timer.running():
                    finpkt4 = RDTSegment(ack=True, ack_num=data.seq_num + 1, seq_num=data.seq_num + 1)
                    break
                if timer.timeout():
                    print("time out, retransmit first handshake")
                    timer.stop()

            self.sendto(finpkt4.encode(),self._send_to)
            print("send fourth handshake")
            # time.sleep(2)
            timer_close = Timer(4*self.TIME_LIMIT)
            timer_close.start()


            while not timer_close.timeout():
                try:
                    data_raw,addr = self.recvfrom(100*RDTSegment.SEGMENT_LEN)
                except BlockingIOError:
                    continue
                self.sendto(finpkt4.encode(), self._send_to)
                print("retransmit fourth handshake")

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        print("close connection")
        super().close()

    def set_send_to(self, send_to):
        self._send_to = send_to

    def set_recv_from(self, recv_from):
        self._recv_from = recv_from


"""
You can define additional functions and classes to do thing such as packing/unpacking packets, or threading.

"""
