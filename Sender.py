import sys
import getopt
from random import randint

import Checksum
import BasicSender

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''
class Sender(BasicSender.BasicSender):
    def __init__(self, dest, port, filename, debug=False, sackMode=False):
        super(Sender, self).__init__(dest, port, filename, debug)
        self.sackMode = sackMode
        self.debug = debug


    def printsend(self, pck, re = False):
        pieces = pck.split('|')
        msg_type, pck_seq = pieces[0:2]
        msg = '|'.join(pieces[2:-1])
        checksum = pieces[-1]
        if re == True:
            print "resend ", msg_type, pck_seq, checksum
        else:
            print "send ", msg_type, pck_seq, checksum


    def check_packet(self, r_pck):
        if self.sackMode:
            pieces = r_pck.split('|')
            seqnums = pieces[1]
            sackpieces =  seqnums.split(';')
            seqno = int(sackpieces[0])
            sack_str = sackpieces[1]
            sacks = []
            if sack_str != '':
                sack_str = sackpieces[1].split(',')
                for i in sack_str:
                    sacks.append(int(i))

            return seqno, Checksum.validate_checksum(r_pck), sacks
        else:
            pieces = r_pck.split('|')
            seqno = int(pieces[1])
            return seqno, Checksum.validate_checksum(r_pck), []


    def stop_and_wait(self, seqno):
        #simple stop and wait
        print "================send data================"
        unfinished = 1
        msg_type = 'dat'
        msg = self.infile.read(1472)
        while unfinished:
            next_msg = self.infile.read(1472)
            seqno = seqno + 1
            if next_msg == '':
                unfinished = 0
                msg_type = 'fin'

            r_pck = None
            r_seqno = 0
            r_sum = 0
            pck = self.make_packet(msg_type, seqno, msg)
            while r_pck == None or r_seqno != seqno + 1 or not r_sum: 
                self.send(pck)
                print 'send ',seqno
                # printpck(pck)
                r_pck = self.receive(0.5)
                print r_pck
                if r_pck != None:
                    r_seqno, r_sum, sacks = self.check_packet(r_pck)
                    print sacks
            msg = next_msg
        return


    def fill_window(self, window, partition_unfin, window_seq, end_seq, add_seq):
        while len(window) < 7 and partition_unfin:
            msg = self.infile.read(1440)
            add_seq = add_seq + 1
            if (msg != ''):
                pck = self.make_packet('dat', add_seq, msg)
                window.append(pck)
            else:
                partition_unfin = 0
                pck = window.pop()
                pieces = pck.split('|')
                pck_seq = int(pieces[1])
                msg = '|'.join(pieces[2:-1])
                pck = self.make_packet('fin', pck_seq, msg)
                window.append(pck)
                end_seq = pck_seq
        return window, partition_unfin, end_seq, add_seq

    def get_seq(self, pck):
        pieces = pck.split('|')
        return int(pieces[1])



    def window_remove(self, seq, sacks, window):
        remove = []
        for pck in window:
            pck_seq = self.get_seq(pck)
            if pck_seq < seq or pck_seq in sacks:
                remove.append(pck)
        for pck in remove:
            window.remove(pck)
        return window


    def simple_window(self, seqno):
        print "================window send data================"
        window = []
        window_seqno = seqno + 1
        send_unfin = 1
        partition_unfin = 1
        add_seq = seqno
        end_seq = 0
        msg_type = 'dat'
        window, partition_unfin, end_seq, add_seq = self.fill_window(window, partition_unfin, window_seqno, end_seq, add_seq)
        repeat = 0
        fast_retransmit = 0

        while send_unfin:
            for pck in window:
                self.printsend(pck)
                self.send(pck)
            total_run = len(window) + fast_retransmit
            fast_retransmit = 0
            for i in range(total_run):
                r_pck = self.receive(0.5)
                print "try receive:",i ,"th packet:", r_pck
                if r_pck != None:
                    r_seqno, r_sum, sacks = self.check_packet(r_pck)
                    window = self.window_remove(r_seqno, sacks, window)
                    if r_seqno == end_seq + 1 and r_sum:
                        send_unfin = 0
                        break
                    elif r_seqno > window_seqno and r_sum:
                        window_seqno = r_seqno
                        repeat = 0
                    elif r_seqno == window_seqno and r_sum:
                        repeat = repeat + 1
                        print "!!!!!!!!!!!!!!repeat", repeat
                        if repeat >= 3:
                            repeat = 0
                            fast_retransmit = 0   #change handle later or now
                            for pck in window:
                                if self.get_seq(pck) == r_seqno:
                                    self.send(pck)
                                    self.printsend(pck, re = True)
                                    break
                            #handle now
                            r_pck = self.receive(0.5)
                            print "try receive resent packet:", r_pck
                            if r_pck != None:
                                r_seqno, r_sum, sacks = self.check_packet(r_pck)
                                if r_sum:
                                    window = self.window_remove(r_seqno, [], window)



            window, partition_unfin, end_seq, add_seq = self.fill_window(window, partition_unfin, window_seqno,end_seq, add_seq)
        return



    # Main sending loop.
    def start(self):
        print self.sackMode
        print "handshake"
        seqno = randint(1, 2**31)
        pck = self.make_packet('syn', seqno, '')
        r_pck = None
        r_seqno = 0
        r_sum = True
        while r_pck == None or r_seqno != seqno + 1 or not r_sum:
            self.send(pck)
            r_pck = self.receive(0.5)
            if r_pck != None:
                r_seqno, r_sum, sacks = self.check_packet(r_pck)
        print "handshake success"

        # self.stop_and_wait(seqno)
        self.simple_window(seqno)
        
        exit()


        
'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
    def usage():
        print "BEARS-TP Sender"
        print "-f FILE | --file=FILE The file to transfer; if empty reads from STDIN"
        print "-p PORT | --port=PORT The destination port, defaults to 33122"
        print "-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost"
        print "-d | --debug Print debug messages"
        print "-h | --help Print this usage message"
        print "-k | --sack Enable selective acknowledgement mode"

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                               "f:p:a:dk", ["file=", "port=", "address=", "debug=", "sack="])
    except:
        usage()
        exit()

    port = 33122
    dest = "localhost"
    filename = None
    debug = False
    sackMode = False

    for o,a in opts:
        if o in ("-f", "--file="):
            filename = a
        elif o in ("-p", "--port="):
            port = int(a)
        elif o in ("-a", "--address="):
            dest = a
        elif o in ("-d", "--debug="):
            debug = True
        elif o in ("-k", "--sack="):
            sackMode = True

    s = Sender(dest,port,filename,debug, sackMode)
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        exit()