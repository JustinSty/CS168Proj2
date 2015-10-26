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
        next_msg = self.infile.read(1440)
        window, next_msg, end_seq, add_seq = self.fill_window(window, next_msg, 0, seqno)
        repeat = 0
        sacks = []
        while True:
            r_pck = self.receive(0.5)
            if r_pck == None:
                repeat = 0
                # resent the entire window
                for pck in window:
                    pck_seq = self.get_seq(pck)
                    if not pck_seq in sacks:
                        self.send(pck)
            else:
                r_seqno, r_sum, sacks = self.check_packet(r_pck)
                if r_sum:
                    if r_seqno == end_seq + 1:
                        break
                    elif r_seqno == window_seqno:
                        repeat = repeat + 1
                        if repeat >= 3:
                            repeat = 0
                            for pck in window:
                                if self.get_seq(pck) == r_seqno:
                                    self.send(pck)
                                    break
                    elif r_seqno > window_seqno:
                        repeat = 0
                        window_seqno = r_seqno
                        window = self.window_remove(r_seqno, window)
                        window, next_msg, end_seq, add_seq = self.fill_window(window, next_msg, end_seq, add_seq)
        return


    def fill_window(self, window, next_msg, end_seq, add_seq):
        while len(window) < 7 and next_msg != '':
            msg = next_msg
            next_msg = self.infile.read(1440)
            add_seq = add_seq + 1
            if next_msg != '':
                pck = self.make_packet('dat', add_seq, msg)
                window.append(pck)
                self.send(pck)
            else:
                pck = self.make_packet('fin', add_seq, msg)
                window.append(pck)
                self.send(pck)
                end_seq = add_seq
        return window, next_msg, end_seq, add_seq


    def get_seq(self, pck):
        pieces = pck.split('|')
        return int(pieces[1])


    def window_remove(self, seq, window):
        remove = []
        for pck in window:
            pck_seq = self.get_seq(pck)
            if pck_seq < seq:
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
