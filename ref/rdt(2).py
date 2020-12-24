from udp import UDPsocket # import provided class
import time
def calc_checksum(payload):
    sum = 0
    for byte in payload:
        sum += byte
        sum = sum % 65536
    return (sum & 0xFFFF)
def add_checksum(payload):
    return payload[:13]+int.to_bytes(calc_checksum(payload),byteorder='little',length=2)+payload[13:]

class socket(UDPsocket):
    def init_paramter(self):
        self.base = 1
        self.nextseqnum = 1
        self.start = 0
        self.expectedseqnum = 1
        self.timer = 200
        self.wait_time = 0.01
        self.addr = ""
        self.port = 0
        self.revport = 0
        self.pktlen = 1460
        self.N = 4
        self.revtimeout = 0.002
        self.acktimeout=0.0002
        self.sndpkt = self.make_pkt(ACK=1, SEQ_ACK=0)
    def __init__(self):
        super(socket, self).__init__()
        #see in PPT
        self.init_paramter()
    def connect_rdt( self,SERVER_ADDR, SERVER_PORT):
        # send syn; receive syn, ack; send ack
        # your code here
        self.addr=SERVER_ADDR
        self.port=int(SERVER_PORT)
        self.send_rdt(SYN=1,message="#hello#")
    def accept_rdt(self):
        self.init_paramter()
        data=bytes(0)
        while(True):
            data,addr = self.recvfrom_rdt(2048)
            if(data.decode()!="#hello#"):self.expectedseqnum=1
            else:break
        return (self,addr)
        # receive syn; send syn, ack; receive ack
        # your code here
    def close(self):
        # send fin; receive ack; receive fin; send ack
        # your code here
        for i in range(20):
            self.sendto(self.make_pkt(FIN=1,SEQ=self.nextseqnum),(self.addr,self.port))

    def slice_pkt(self,data,have_send):
        last = min(len(data),have_send+self.pktlen)
        return data[have_send:last],last
    def make_pkt(self,SYN=0,FIN=0,ACK=0,SEQ=0,SEQ_ACK=0,data=b''):
        payload=int.to_bytes(SYN*4+FIN*2+ACK*1,byteorder='little',length=1)
        payload=payload+int.to_bytes(SEQ,byteorder='little',length=4)
        payload=payload+int.to_bytes(SEQ_ACK,byteorder='little',length=4)
        payload=payload+int.to_bytes(len(data),byteorder='little',length=4)
        payload=payload+data
        payload=add_checksum(payload)
        return payload
    def not_corrupt(self,data):
        payload=data[:13]+data[15:]
        check_sum=int.from_bytes(data[13:15],byteorder='little')
        if(calc_checksum(payload)==check_sum):
            return True
        else:
            return False
    def get_acknum(self,data):
        ACK=int.from_bytes(data[0:1],byteorder='little')
        ACK=ACK%2
        if(ACK==0):return 0
        else:
            return int.from_bytes(data[5:9],byteorder='little')
    def get_state(self,data):
        num = int.from_bytes(data[0:1],byteorder='little')
        state={}
        state["FIN"]=num/2%2
        state["SYN"]=num/4%2
        return state
    def get_seqnum(self,data):
        seq_num=int.from_bytes(data[1:5],byteorder='little')
        return seq_num
    def get_payload(self,data):
        return data[15:]
    def recvfrom_rdt(self,bufsize):
        full_data=bytes(0)
        while(True):
            if(self.addr!=""):self.sendto(self.sndpkt, (self.addr, self.port))
            self.settimeout(self.revtimeout)
            try:
                data,addr = self.recvfrom(bufsize)
            except:
                data=None
            if(data!=None and self.not_corrupt(data)):print("seq=",self.get_seqnum(data),"expect=",self.expectedseqnum)
            if(data!=None and self.not_corrupt(data) and self.get_seqnum(data)==self.expectedseqnum):
                if (self.addr == ""):
                    self.addr = addr[0]
                    self.port = int(addr[1])
                print("data="+str(data))
                if(self.get_state(data)["FIN"]==1):#when one message is over ,prepare for new message
                    self.expectedseqnum=self.expectedseqnum+1
                    break
                data = self.get_payload(data)
                self.sndpkt = self.make_pkt(ACK=1,SEQ_ACK=self.expectedseqnum)
                self.sendto(self.sndpkt,(self.addr,self.port))
                full_data=full_data+data
                self.expectedseqnum=self.expectedseqnum+1
            self.settimeout(None)
        return full_data,addr
    def recv_rdt(self,bufsize):
        data,addr=self.recvfrom_rdt(bufsize)
        return data
    def send_rdt(self,SYN=0,ACK=0,FIN=0,message=""):
        data=message.encode()
        have_send=0
        sndpkt={}
        while(have_send<len(data) or self.base<self.nextseqnum):# all data should be sent
            if(self.nextseqnum<(self.base+self.N) and have_send<len(data)):
                slice_data,have_send= self.slice_pkt(data,have_send)
                sndpkt[self.nextseqnum]=self.make_pkt(SYN=SYN,ACK=ACK,FIN=FIN,SEQ=self.nextseqnum,data=slice_data)
                self.sendto(sndpkt[self.nextseqnum],(self.addr,self.port))
                if(self.base==self.nextseqnum):
                    self.start=time.time()
                    self.timer = self.wait_time
                self.nextseqnum = self.nextseqnum+1
            if(time.time()>self.start+self.timer):
                print("loss,retransmit")
                self.start=time.time()
                self.timer=self.wait_time
                i=self.base
                while(i<self.nextseqnum):
                    self.sendto(sndpkt[i], (self.addr, self.port))
                    i=i+1
            self.settimeout(self.acktimeout)
            try:
                rev_data,target_addr=self.recvfrom(2048)
            except:
                rev_data,target_addr=("","")
            self.settimeout(None)
            #if(rev_data!="" and self.not_corrupt(rev_data)):print("acknum=",self.get_acknum(rev_data))
            if(rev_data!="" and self.not_corrupt(rev_data) ):
                if(self.get_acknum(rev_data)+1>self.base and self.get_acknum(rev_data)+1<=self.nextseqnum):
                    print("ack=",self.get_acknum(rev_data),"data=",rev_data)
                    self.base=self.get_acknum(rev_data)+1
                    self.start = time.time()
                    self.timer = self.wait_time
                if(self.base==self.nextseqnum):
                    self.timer=1000000000
            print("base=",self.base,"nextseqnum=",self.nextseqnum)
        for i in range(20):
            self.sendto(self.make_pkt(FIN=1,SEQ=self.nextseqnum),(self.addr,self.port))
        self.base=self.base+1
        self.nextseqnum=self.nextseqnum+1
