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
    MAX_PAYLOAD_LEN = 1440
    SEGMENT_LEN = MAX_PAYLOAD_LEN + HEADER_LEN
    SEQ_NUM_BOUND = 256

    def __init__(self, seq_num: int, ack_num: int, syn: bool = False, fin: bool = False,
                 ack: bool = False, payload: bytes = None, len: int = 0):
        self.syn = syn
        self.fin = fin
        self.ack = ack
        # self.sack = False
        # SEQ
        self.seq_num = seq_num
        # SEQACK
        self.ack_num = ack_num
        # SACK
        self.SLE = 0
        self.SRE = 0

        self.len = 0
        self.checksum = 0
        self.payload = payload

    def encode(self) -> bytes:
        return bytes([])

    @staticmethod
    def parse(segment: Union[bytes, bytearray]) -> 'RDTSegment':
        return RDTSegment()

    @staticmethod
    def calc_checksum(segment: Union[bytes, bytearray]) -> int:
        return 0
