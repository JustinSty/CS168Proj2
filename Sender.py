import sys
import getopt
import random

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
    
    def printsend(self, pck, re = False, print_mode = 0):
        if print_mode:
            pieces = pck.split('|')
            msg_type, pck_seq = pieces[0:2]
            msg = '|'.join(pieces[2:-1])
            checksum = pieces[-1]
            if re == True:
                print "resend ", msg_type, pck_seq, checksum
            else:
                print "send ", msg_type, pck_seq, checksum

    # Main sending loop.
    def start(self):
        seqno = random.randint(1, 2**31)
        self.handshake(seqno)
        self.simple_window(seqno)
        exit()


    def handshake(self, seqno):
        syn_pck = self.make_packet('syn', seqno, '')
        r_pck, r_seqno, r_sum = None, 0, True
        while r_pck == None or r_seqno != seqno + 1 or not r_sum:
            self.send(syn_pck)
            r_pck = self.receive(0.5)
            if r_pck != None:
                r_seqno, r_sum, sacks = self.check_packet(r_pck)


    def simple_window(self, seqno):
        window, window_seqno = [], seqno + 1
        send_unfin, msg_type = True, 'dat'
        window, partition_unfin, end_seq, add_seq = self.fill_window(window, True, 0, seqno)
        repeat = 0
        while send_unfin:
            r_pck = self.receive(0.5)
            if r_pck == None:
                for pck in window:
                    self.send(pck)
                    self.printsend(pck)
            else:
                r_seqno, r_sum, sacks = self.check_packet(r_pck)
                if r_sum:
                    if r_seqno == end_seq + 1:
                        break
                    elif r_seqno > window_seqno:
                        window_seqno = r_seqno
                        repeat = 0
                        window = self.window_remove(r_seqno, sacks, window)
                        window, partition_unfin, end_seq, add_seq = self.fill_window(window, partition_unfin, end_seq, add_seq)
                    if r_seqno == window_seqno:
                        repeat = repeat + 1
                        if repeat >= 3:
                            repeat = 0
                            for pck in window:
                                if self.get_seq(pck) == r_seqno:
                                    self.send(pck)
                                    self.printsend(pck, re=True)
                                    break
        return


    def fill_window(self, window, partition_unfin, end_seq, add_seq):
        while len(window) < 7 and partition_unfin:
            msg = self.infile.read(1440)
            if msg != '':
                add_seq = add_seq + 1
                pck = self.make_packet('dat', add_seq, msg)
                window.append(pck)
                self.send(pck)
            else:
                partition_unfin = False
                pck = window.pop()
                pieces = pck.split('|')
                pck_seqno = int(pieces[1])
                msg = '|'.join(pieces[2:-1])
                pck = self.make_packet('fin', pck_seqno, msg)
                window.append(pck)
                self.send(pck)
                end_seq = pck_seqno
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
            seqno = self.get_seq(r_pck)
            return seqno, Checksum.validate_checksum(r_pck), []

        
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
