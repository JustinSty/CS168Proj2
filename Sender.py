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

    def printpck(pck):
        print "********************************"
        print "send ", pck
        print "++++++++++++++++++++++++++++++++"

    # Main sending loop.
    def start(self):
        print "handshake"
        seqno = randint(1, 2**31)
        msg_type = 'syn'
        msg = ''
        pck = self.make_packet(msg_type, seqno, msg)
        r_msg = None
        r_seqno = 0
        while r_msg == None or r_seqno != seqno + 1:
            self.send(pck)
            r_msg = self.receive(500)
            pieces = r_msg.split('|')
            r_seqno = int(pieces[1])
        print r_seqno
        print "handshake success"
        print "================send data================"
        unfinished = 1
        msg_type = 'dat'
        while unfinished:
            msg = self.infile.read(1472)
            seqno = seqno + 1
            if msg == '':
                unfinished = 0
                print unfinished
            else:
                print "unfinished"
                r_msg = None
                r_seqno = 0
                pck = self.make_packet(msg_type, seqno, msg)
                while r_msg == None or r_seqno != seqno + 1: 
                    self.send(pck)
                    print 'send ',seqno
                    # printpck(pck)
                    r_msg = self.receive(500)
                    print r_msg
                    pieces = r_msg.split('|')
                    r_seqno = int(pieces[1])
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
