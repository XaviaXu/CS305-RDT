from udp import UDPsocket
import struct
import hashlib
import threading
import time
import datetime
import queue
TIMEOUT = 0.5
TIMED_WAIT_TIME = 2.5
MAX_RETRANSMIT_ATTEMPT = 50
COLOR_PAIR = {
    "WR": "\033[41;37m",
    "WG": "\033[42;37m",
    "WY": "\033[43;37m",
    "WDB": "\033[44;37m",
    "WP": "\033[45;37m",
    "WB": "\033[46;37m"
}
COLOR_PAIR["Info"] = COLOR_PAIR["WDB"]
COLOR_PAIR["Warn"] = COLOR_PAIR["WY"]
COLOR_PAIR["Error"] = COLOR_PAIR["WR"]

def dbg_print(level: str, module_name: str, message: str, color_pair=None):
    color_str_begin = COLOR_PAIR[level] if color_pair==None else COLOR_PAIR[color_pair]
    color_str_end = "\033[0m"
    print("[{}] {}: {}{}{}".format(level, module_name, color_str_begin, message, color_str_end))

class rdt_packet_util():
    @staticmethod
    def unpack_flag(flag: int):
        syn = (flag>>7 & 0x1) == 0x1
        fin = (flag>>6 & 0x1) == 0x1
        ack = (flag>>5 & 0x1) == 0x1
        seq_ack_num = flag&0xF
        return syn, fin, ack, seq_ack_num
    
    @staticmethod
    def pack_flag(syn: bool, fin: bool, ack: bool, seq_ack_num: int):
        flag = syn<<7 | fin<<6 | ack<<5 | (seq_ack_num & 0xF)
        flag = struct.pack("B", flag)
        return flag

    @staticmethod
    def pack(syn: bool, fin: bool, ack: bool, seq_ack_num: int, msg: bytes):
        if type(msg) == str: msg = msg.encode('utf-8')
        flag = rdt_packet_util.pack_flag(syn, fin, ack, seq_ack_num)
        data = flag + msg
        checksum = hashlib.md5(data).digest()
        checksum = checksum[0:16]
        return checksum + data
        
    @staticmethod
    def unpack(packet: bytes):
        flag = packet[16:17]
        flag = struct.unpack("B", flag)[0]
        syn, fin, ack, seq_ack_num = rdt_packet_util.unpack_flag(flag)
        msg = packet[17:]
        return msg, syn, fin, ack, seq_ack_num
    
    @staticmethod
    def is_corrupt(packet: bytes):
        if len(packet)<16: return True
        checksum = packet[0:16]
        data = packet[16:]
        return not checksum == hashlib.md5(data).digest()

class rdt_pkt_collector():
    BUFFER_SIZE = 1024
    def __init__(self, udp_send, udp_recv):
        self.tx_buffer = queue.Queue(self.BUFFER_SIZE)
        self.msg_buffer = queue.Queue(self.BUFFER_SIZE)
        self.ack_buffer = queue.Queue(self.BUFFER_SIZE)
        self.udp_send = udp_send
        self.udp_recv = udp_recv
        self.enable_tx()
        self.enable_rx()
        self.tx_enable = True
        self.rx_enable = True
        # self.on_recv_msg = None
        # self.on_recv_ack = None
    
    def __async_recv(self):
        while self.rx_enable:
            time.sleep(0.1)
            try:
                data = self.udp_recv(2048)
                if not data: continue
            except Exception as e:
                # print(e)
                continue
            data, src_addr = data
            msg, syn, fin, ack, seq_ack_num = rdt_packet_util.unpack(data)
            packet = {
                "data": data,
                "src_addr": src_addr,
                "msg":  msg,
                "syn":  syn,
                "fin":  fin,
                "ack":  ack,
            }
            if rdt_packet_util.is_corrupt(data):
                dbg_print("Error", "Collector", "Found corrupt packet")
                continue
            if ack:
                packet["ack_num"] = seq_ack_num
                self.ack_buffer.put(packet)
            else:
                packet["seq_num"] = seq_ack_num
                self.msg_buffer.put(packet)
            
        dbg_print("Info", "Collector", "Thread RX Stopped.")
    
    def __async_send(self):
        while self.tx_enable:
            while not self.tx_buffer.empty():
                packet = self.tx_buffer.get()
                data = rdt_packet_util.pack(packet["syn"], packet["fin"], packet["ack"], packet["seq_ack_num"], packet["msg"])
                self.udp_send(data, packet["dst_addr"])
            time.sleep(0.1)
        dbg_print("Info", "Collector", "Thread TX Stopped.")
        
    def enable_tx(self):
        self.tx_enable = True
        timer = threading.Timer(0, self.__async_send)
        timer.start()
    
    def enable_rx(self):
        self.rx_enable = True
        timer = threading.Timer(0, self.__async_recv)
        timer.start()
    
    def disable_tx(self):
        self.tx_enable = False
    
    def disable_rx(self):
        self.rx_enable = False

    def aync_send(self, packet: dict):
        if "dst_addr" not in packet: packet["dst_addr"] = packet["src_addr"]
        if packet["ack"]: packet["seq_ack_num"] = packet["ack_num"]
        else: packet["seq_ack_num"] = packet["seq_num"]
        self.tx_buffer.put(packet)
    
    def aync_recv_msg(self):
        if self.msg_buffer.empty(): return None
        else: return self.msg_buffer.get()
    
    def aync_recv_ack(self):
        if self.ack_buffer.empty(): return None
        else: return self.ack_buffer.get()

class rdt_sender(): 
    BUFFER_SIZE = 1024
    def __init__(self, collector: rdt_pkt_collector, dst_addr=None):
        self.seq_num = 0
        self.collector = collector
        self.dst_addr = dst_addr
    
    def set_dst_addr(self, dst_addr):
        self.dst_addr = dst_addr
    
    def send(self, tx_pkt: dict):
        attempt = 0
        tx_pkt["ack"] = False
        tx_pkt["seq_num"] = self.seq_num
        tx_pkt["dst_addr"] = self.dst_addr
        
        flag_success = False
        while (not flag_success) and self.collector.tx_enable and self.collector.rx_enable and attempt<=MAX_RETRANSMIT_ATTEMPT:
            dbg_print("Info", "RDT_Sender", "Send PKT{}, attempt:{}".format(tx_pkt, attempt), "WP")
            attempt += 1

            self.collector.aync_send(tx_pkt)
            
            time.sleep(TIMEOUT)

            flag_success = False
            flag_timeout = True
            while True:
                rx_pkt = self.collector.aync_recv_ack()
                if not rx_pkt:
                    if flag_timeout: dbg_print("Warn", "RDT_Sender", "Timeout.")
                    break
                flag_timeout = False
                if rdt_packet_util.is_corrupt(rx_pkt["data"]):
                    dbg_print("Warn", "RDT_Sender", "ACK{} is corrupt.".format(self.seq_num))
                    continue
                if rx_pkt["ack_num"] != self.seq_num:
                    dbg_print("Warn", "RDT_Sender", "Expected ACK{}, got ACK{}.".format(self.seq_num, rx_pkt["ack_num"]))
                    continue
                else:
                    flag_success = True
                    # print("[Info] RDT_Sender: Got Expected ACK{}.".format(self.seq_num))
                    break

        dbg_print("Info", "RDT_Sender", "Send PKT{}, success.".format(tx_pkt, attempt), "WG")
        self.seq_num = (self.seq_num+1)&0xF
        if tx_pkt["callback"] != None: tx_pkt["callback"]()

class rdt_receiver():
    def __init__(self, collector: rdt_pkt_collector):
        self.ack_num = 0
        self.collector = collector
    
    def recv(self):
        flag_success = False
        while (not flag_success) and self.collector.tx_enable and self.collector.rx_enable:
            rx_pkt = self.collector.aync_recv_msg()
            if not rx_pkt:
                time.sleep(0.1)
                continue
            if rdt_packet_util.is_corrupt(rx_pkt["data"]):
                dbg_print("Warn", "RDT_Recevier", "PKT{} is corrupt.".format(self.ack_num))
                self.nak(rx_pkt)
                continue
            if rx_pkt["seq_num"] != self.ack_num:
                dbg_print("Warn", "RDT_Recevier", "Expected PKT{}, got PKT{}.".format(self.ack_num, rx_pkt["seq_num"]))
                self.nak(rx_pkt)
                continue
            dbg_print("Info", "RDT_Recevier", "Received PKT{}".format(rx_pkt), "WG")
            self.ack(rx_pkt)
            self.ack_num = (self.ack_num+1)&0xF
            return rx_pkt

    def ack(self, rx_pkt: dict, ack_num=None):
        if ack_num==None: ack_num = self.ack_num
        rx_pkt["ack"] = True
        rx_pkt["ack_num"] = ack_num
        rx_pkt["dst_addr"] = rx_pkt["src_addr"]
        dbg_print("Info", "RDT_Recevier", "Send ACK{}".format(ack_num), "WP")
        self.collector.aync_send(rx_pkt)

    def nak(self, rx_pkt: dict):
        nak_num = (self.ack_num + 0xF) & 0xF
        self.ack(rx_pkt, nak_num)

class tcp_fsm():
    BUFFER_SIZE = 1024
    STATE = {
        "CLOSED": 0,
        "LISTEN": 10,
        "SYNSENT": 20,
        "SYNRCVD": 21,
        "ESTAB": 30,
        "FIN_WAIT1": 40,
        "FIN_WAIT2": 50,
        "TIMED_WAIT": 60,
        "CLOSE_WAIT": 41,
        "LAST_ACK": 51
    }
    
    def __init__(self, udp_send, udp_recv):
        super().__init__()
        self.udp_send = udp_send
        self.udp_recv = udp_recv
        self.state = self.STATE["CLOSED"]
        self.rx_buffer = queue.Queue(self.BUFFER_SIZE)
        self.tx_buffer = queue.Queue(self.BUFFER_SIZE)
        self.tx_enable = True
        self.rx_enable = True
        self.tx_busy = False
        self.STATE_NAME = {v : k for k, v in self.STATE.items()}
        
    def send(self, msg=b"", syn=False, fin=False, callback=None):
        packet = {
            "msg": msg,
            "syn": syn,
            "fin": fin,
            "callback": callback
        }
        self.tx_buffer.put(packet)
    
    def recv(self):
        if self.rx_buffer.empty(): return None
        else: return self.rx_buffer.get()
    
    def __async_recv(self):
        while self.rx_enable:
            if self.on_receive: self.on_receive( self.rdt_recv.recv() )
            time.sleep(0.1) 
        dbg_print("Info", "TCP_FSM", "Thread RX Stopped.")
    
    def __async_send(self):
        while self.tx_enable:
            if self.tx_buffer.empty():
                self.tx_busy = False
                time.sleep(0.1)
            else:
                self.tx_busy = True
                self.rdt_send.send( self.tx_buffer.get() )
        dbg_print("Info", "TCP_FSM", "Thread TX Stopped.")
    
    def enable_tx(self, rdt_send: rdt_sender):
        self.rdt_send = rdt_send
        self.tx_enable = True
        timer = threading.Timer(0, self.__async_send)
        timer.start()
    
    def enable_rx(self, rdt_recv: rdt_receiver, on_receive=None):
        self.rdt_recv = rdt_recv
        self.on_receive = on_receive
        self.rx_enable = True
        timer = threading.Timer(0, self.__async_recv)
        timer.start()
    
    def tx_barrier(self):
        while self.tx_busy or (not self.tx_buffer.empty()): time.sleep(0.1)

    def disable_tx(self):
        self.tx_barrier()
        self.tx_enable = False
    
    def disable_rx(self):
        self.rx_enable = False
    
    def is_at_state(self, state: str):
        return self.state == self.STATE[state]

    def transit_state(self, next_state: str, assert_current_state=None):
        if assert_current_state!=None and (not self.is_at_state( assert_current_state )):
            dbg_print("Error", "TCP FSM", "Unexpected state transition: {} (Expected: {}) -> {}".format(self.STATE_NAME[self.state], assert_current_state, next_state))
            return
        dbg_print("Info", "TCP FSM", "Transit state: {} -> {}".format(self.STATE_NAME[self.state], next_state))
        self.state = self.STATE[next_state]

    def SYNRCVD_to_ESTAB(self):
        self.transit_state("ESTAB", "SYNRCVD")
    
    def SYNSENT_to_ESTAB(self):
        self.transit_state("ESTAB", "SYNSENT")
    
    def LAST_ACK_to_CLOSED(self):
        self.transit_state("CLOSED", "LAST_ACK")
        timer = threading.Timer(2*TIMED_WAIT_TIME, self.stop_threads)
        timer.start()
    
    def FIN_WAIT1_to_FIN_WAIT2(self):
        self.transit_state("FIN_WAIT2", "FIN_WAIT1")

    def on_receive(self, rx_pkt):
        if self.is_at_state("LISTEN"):
            if rx_pkt["syn"]:
                self.transit_state("SYNRCVD")
                self.client_addr = rx_pkt["src_addr"]
                self.enable_tx( rdt_sender(self.pkt_collector, self.client_addr) )
                self.send(syn=True, callback=self.SYNRCVD_to_ESTAB)
        
        elif self.is_at_state("SYNRCVD"):
            self.transit_state("ESTAB")
            self.on_receive(rx_pkt)
        elif self.is_at_state("ESTAB"):
            if rx_pkt["syn"]: pass
            if rx_pkt["fin"]:
                self.transit_state("CLOSE_WAIT")
                self.tx_barrier()
                self.transit_state("LAST_ACK")
                self.send(fin=True, callback=self.LAST_ACK_to_CLOSED)
            if (not rx_pkt["fin"]) and (not rx_pkt["syn"]):
                self.rx_buffer.put(rx_pkt["msg"])
        
        elif self.is_at_state("FIN_WAIT1") or self.is_at_state("FIN_WAIT2"):
            if rx_pkt["syn"]: pass
            if rx_pkt["fin"]:
                self.transit_state("TIMED_WAIT")
            if (not rx_pkt["fin"]) and (not rx_pkt["syn"]):
                self.rx_buffer.put(rx_pkt["msg"])
    
    def stop_threads(self):
        self.disable_rx()
        self.disable_tx()
        self.pkt_collector.disable_rx()
        self.pkt_collector.disable_tx()
    
    def state_barrier(self, expected_state):
        while not self.is_at_state(expected_state): time.sleep(0.1)
    
    def close(self):
        if not self.is_at_state("ESTAB"): return
        self.transit_state("FIN_WAIT1")
        self.send(fin=True, callback=self.FIN_WAIT1_to_FIN_WAIT2)
        self.state_barrier("TIMED_WAIT")
        time.sleep(TIMED_WAIT_TIME)
        self.transit_state("CLOSED")
        self.stop_threads()
        time.sleep(TIMED_WAIT_TIME)
    
class tcp_client_fsm(tcp_fsm):
    def connect(self, dest_addr):
        self.pkt_collector = rdt_pkt_collector(self.udp_send, self.udp_recv)
        rdt_send = rdt_sender(self.pkt_collector, dest_addr)
        rdt_recv = rdt_receiver(self.pkt_collector)
        self.enable_tx(rdt_send)
        self.enable_rx(rdt_recv, self.on_receive)
        self.transit_state("SYNSENT")
        self.send(syn=True, callback=self.SYNSENT_to_ESTAB)

class tcp_server_fsm(tcp_fsm):
    def listen(self):
        self.pkt_collector = rdt_pkt_collector(self.udp_send, self.udp_recv)
        rdt_recv = rdt_receiver(self.pkt_collector)
        self.enable_rx(rdt_recv, self.on_receive)
        self.transit_state("LISTEN")
    
    def close(self):
        pass

class socket(UDPsocket):
    def __init__(self):
        super(socket, self).__init__()
        self.setblocking(False)
        self.role = None

    def connect(self, address):
        self.role = "client"
        self.fsm = tcp_client_fsm(super().sendto, super().recvfrom)
        self.fsm.connect(address)
        self.fsm.state_barrier("ESTAB")

    # def bind(self, address):
    #    return super().bind(address)
    
    def accept(self):
        self.role = "server"
        self.fsm = tcp_server_fsm(super().sendto, super().recvfrom)
        self.fsm.listen()
        self.fsm.state_barrier("ESTAB")
        return self, self.fsm.client_addr

    def close(self):
        self.fsm.close()
        self.fsm.state_barrier("CLOSED")
        if self.role == "client": super().close()
        # return super().close()
    
    def recv(self, bufsize):
        while not self.fsm.is_at_state("CLOSED"):
            msg = self.fsm.recv()
            if msg: return msg
    
    def send(self, data):
        self.fsm.send(msg=data)

if __name__ == "__main__":
    pass