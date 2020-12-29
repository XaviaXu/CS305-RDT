import struct
from typing import Union


class RDTSegment:
    """
    Reliable Data Transfer Segment

    Segment Format:

      0   1   2   3   4   5   6   7   8   9   a   b   c   d   e   f   10
    +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+----+
    |SYN|FIN|ACK|     SEQ       |     SEQACK    |      LEN      |CHECKSUM|
    +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+----+
    |                                                                    |
    /                            PAYLOAD                                 /
    /                                                                    /
    +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+----+

    bytes: [(0..GFIN,SYN,FIN,ACK),SEQ,

    Protocol Version:           1

    Flags:
     - SYN                      Synchronize
     - FIN                      Finish
     - ACK                      Acknowledge

    Ranges:
     - Payload Length           0 - 1440  (append zeros to the end if length < 1440)
     - Sequence Number          0 - 255
     - Acknowledgement Number   0 - 255

    Checksum Algorithm:         16 bit one's complement of the one's complement sum

    Size of sender's window     16
    """

    HEADER_LEN = 6
    MAX_PAYLOAD_LEN = 440
    SEGMENT_LEN = MAX_PAYLOAD_LEN + HEADER_LEN
    SEQ_NUM_BOUND = 256

    def __init__(self, seq_num: int, ack_num: int, syn: bool = False, fin: bool = False,
                 ack: bool = False, sack: int = 1, payload: bytes = None, len: int = 0,
                 gfin: bool = False):
        self.syn = syn
        self.fin = fin
        self.ack = ack
        self.sack = sack
        # SEQ
        self.seq_num = seq_num
        # SEQACK
        self.ack_num = ack_num

        #Global
        self.gfin = gfin

        self.len = len
        self.checksum = 0
        self.payload = payload

    def encode(self) -> bytes:
        head = 0x0
        if self.gfin:
            head |= 0x8
        if self.syn:
            head |= 0x4
        if self.fin:
            head |= 0x2
        if self.ack:
            head |= 0x1
        arr = bytearray(struct.pack('!BIIIH', head, self.seq_num, self.ack_num, self.len, 0))
        if self.payload:
            arr.extend(self.payload)
        checksum = RDTSegment.calc_checksum(arr)
        arr[13] = checksum >> 8
        arr[14] = checksum & 0xFF
        return bytes(arr)

    #set SACK by hand
    def setSACK(self, sack):
        self.sack = sack

    @staticmethod
    def parse(segment: Union[bytes, bytearray]) -> 'RDTSegment':
        head, = struct.unpack('!B', segment[0:1])
        gfin = (head & 0x8) != 0
        syn = (head & 0x4) != 0
        fin = (head & 0x2) != 0
        ack = (head & 0x1) != 0
        seq_num, ack_num, len, checksum = struct.unpack('!IIIH', segment[1:15])
        payload = segment[15:15+len]
        return RDTSegment(seq_num, ack_num, syn, fin, ack, 1, payload, len, gfin)

    @staticmethod
    def calc_checksum(segment: Union[bytes, bytearray]) -> int:
        i = iter(segment)
        bytes_sum = sum(((a << 8) + b for a, b in zip(i, i)))  # for a, b: (s[0], s[1]), (s[2], s[3]), ...
        if len(segment) % 2 == 1:  # pad zeros to form a 16-bit word for checksum
            bytes_sum += segment[-1] << 8
        # add the overflow at the end (adding twice is sufficient)
        bytes_sum = (bytes_sum & 0xFFFF) + (bytes_sum >> 16)
        bytes_sum = (bytes_sum & 0xFFFF) + (bytes_sum >> 16)
        return ~bytes_sum & 0xFFFF

    @staticmethod
    def check_checksum(segment, segment_raw):
        checksum = struct.unpack('!H', segment_raw[13:15])
        test = segment.encode()
        testsum = struct.unpack('!H', test[13:15])
        return testsum == checksum
