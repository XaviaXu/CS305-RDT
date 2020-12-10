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


    def __init__(self):
        self.syn = False
        self.fin = False
        self.ack = False
        # SEQ
        self.seq_num = 0
        # SEQACK
        self.ack_num = 0
        self.len = 0
        self.checksum = 0
        self.payload = bytes(0)

    def encode(self) -> bytes:
        return bytes([])

    @staticmethod
    def parse(segment: Union[bytes, bytearray]) -> 'RDTSegment':
        return RDTSegment()

    @staticmethod
    def calc_checksum(segment: Union[bytes, bytearray]) -> int:
        return 0
