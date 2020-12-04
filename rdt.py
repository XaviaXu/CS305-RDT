from udp import UDPsocket
class socket(UDPsocket):
    def __init__(self):
        super(socket,self).__init__()
    def connect(self):

        pass
    def accept(self):
        pass

    def close(self):
        pass

    def recv(self, bufsize):
        pass

    def send(self, data: bytes, flags: int = ...) -> int:
        pass