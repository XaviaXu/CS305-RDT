import network
from rdt import RDTSocket
import _thread

if __name__=='__main__':
    # sock_snd = RDTSocket()
    # sock_snd.bind(('127.0.0.1', 5555))
    #
    # sock_rcv = RDTSocket()
    # sock_rcv.bind(('127.0.0.1',5550))
    # sock_snd.sendto(b'connecting',('127.0.0.1',5550))
    # for i in range(10):
    #     sock_snd.send(b'hello')
    #     print(sock_rcv.recvfrom(2048))
    rdt = RDTSocket()
    try:
        _thread.start_new_thread(rdt.send, (b'hello',))
        _thread.start_new_thread(rdt.recv, (2048,))
    except:
        print("Error: unable to start thread")






    pass