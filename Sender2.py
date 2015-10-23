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

    def printsend(self, pck):
        pieces = pck.split('|')
        msg_type, pck_seq = pieces[0:2]
        msg = '|'.join(pieces[2:-1])
        checksum = pieces[-1]
        print "send ", msg_type, pck_seq, checksum
        # print "+++++++++++++++++++++++++++++++++++++++++++"
        # print msg
        # print "*******************************************"


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
            msg = next_msg
        return


    def fill_window(self, window, partition_unfin, window_seq, add_seq, end_seq):
        while len(window) < 7 and partition_unfin:
            msg = self.infile.read(1472)
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
        return window, partition_unfin, add_seq, end_seq

    def get_seq(self, pck):
        pieces = pck.split('|')
        seqno = int(pieces[1])
        return seqno

    def simple_window(self, seqno):
        print "================window send data================"
        window = []
        window_seqno = seqno + 1
        send_unfin = 1
        partition_unfin = 1
        end_seq = 0
        msg_type = 'dat'
        window, partition_unfin, end_seq = self.fill_window(window, partition_unfin, window_seqno, end_seq)
        repeat = 0

        while send_unfin:
            for pck in window:
                self.printsend(pck)
                self.send(pck)
            for i in range(len(window)):
                r_pck = self.receive(0.5)
                print "r_pck: ", r_pck
                if r_pck != None:
                    #need sackMode from here
                    r_seqno, r_sum = self.check_packet(r_pck, sackMode)
                    if r_seqno == end_seq + 1:
                        send_unfin = 0
                        break
                    elif r_seqno > window_seqno and r_sum:
                        for i in range(r_seqno - window_seqno):
                            window.pop(0)
                        window_seqno = r_seqno
                    elif r_seqno == window_seqno and r_sum:
                        repeat = repeat + 1
                        # print "!!!!!!!!!!!!!!repeat", repeat
                        if repeat >= 3:
                            repeat = 0
                            break

            window, partition_unfin, end_seq = self.fill_window(window, partition_unfin, window_seqno,end_seq)
        return


    def sack_window(self, seqno):
        print "================window send data================"
        window = []
        window_seqno = seqno + 1
        send_unfin = 1
        partition_unfin = 1
        add_seq = seqno
        end_seq = 0
        msg_type = 'dat'
        window, partition_unfin, add_seq, end_seq = self.fill_window(window, partition_unfin, window_seqno, add_seq, end_seq)
        repeat = 0

        while send_unfin:
            for pck in window:
                self.printsend(pck)
                self.send(pck)
            for i in range(len(window)):
                r_pck = self.receive(0.5)
                print "r_pck: ", r_pck
                if r_pck != None:
                    #need sackMode from here
                    r_seqno, r_sum, sacks = self.check_packet(r_pck)

                    remove = []
                    for pck in window:
                        a = self.get_seq(pck)
                        if a in sacks:
                            remove.append(pck)
                    for pck in remove:
                        window.remove(pck)

                    if r_seqno == end_seq + 1:
                        send_unfin = 0
                        break
                    elif r_seqno > window_seqno and r_sum:
                        for i in range(r_seqno - window_seqno):
                            if window != []:
                                window.pop(0)
                        window_seqno = r_seqno
                    elif r_seqno == window_seqno and r_sum:
                        repeat = repeat + 1
                        # print "!!!!!!!!!!!!!!repeat", repeat
                        if repeat >= 3:
                            repeat = 0
                            break

            window, partition_unfin, add_seq, end_seq = self.fill_window(window, partition_unfin, window_seqno, add_seq, end_seq)
        return


    # Main sending loop.
    def start(self):
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
