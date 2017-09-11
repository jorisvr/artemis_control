#!/usr/bin/python3

"""
Command-line Artemis client for protocol debugging.

Usage: testcli.py <serveripaddr>
"""

import sys
import enum
import socket
import struct
import time


def dbg(msg):
    tstamp = time.time()
    tstr = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(tstamp)))
    tstr += '.%03d' % max(0, min(999, int(1000 * (tstamp - int(tstamp)))))
    print(tstr, msg, file=sys.stderr)


class ProtocolError(Exception):
    pass


class ConnectionType(enum.Enum):
    Server = 1
    Client = 2

class PacketType(enum.Enum):
    DifficultyPacket = 0x3de66711
    VersionPacket = 0xe548e74a
    WelcomePacket = 0x6d04b3da


class ArtemisClientConnection:
    """Client side of Artemis network connection."""

    def __init__(self, serverhost):

        self.sock = None
        self.serverhost = serverhost

    def connect(self):

        assert self.sock is None

        dbg('Connecting to server ...')
        serverport = 2010
        self.sock = socket.create_connection((self.serverhost, serverport))
        dbg('Connected to server')

    def close(self):

        if self.sock is not None:
            dbg('Closing connection ...')
            self.sock.close()
        self.sock = None

    def isConnected(self):

        return self.sock is not None

    def getPacket(self, timeout=None):

        assert self.sock is not None

        self.sock.settimeout(timeout)

        try:
            hdr = self.sock.recv(24)
        except socket.timeout:
            return None

        if timeout is not None:
            self.sock.settimeout(None)

        while len(hdr) < 24:
            s = self.sock.recv(24 - len(hdr))
            if not s:
                dbg('Server dropped connection')
                self.close()
                return None
            hdr += s

        assert len(hdr) == 24

        (preamb, plen, origin, padding, remain, ptype
            ) = struct.unpack('<IIIIII', hdr)

        if preamb != 0xdeadbeef:
            raise ProtocolError('Expected preamble 0xdeadbeef but got 0x%08x' %
                                preamb)

        if plen < 24 or plen > 65536:
            raise ProtocolError('Got invalid packet length %d' % plen)

        if origin != ConnectionType.Server.value:
            raise ProtocolError('Expected origin=%r but got %d' %
                                (ConectionType.Server, origin))

        if remain != plen - 20:
            raise ProtocolError('Expected remain=%d for plen=%d but got %d' %
                                (remain, plen, remain))

        payload = b''
        while len(payload) < plen - 24:
            s = self.sock.recv(plen - 24 - len(payload))
            if not s:
                dbg('Server dropped connection')
                self.close()
                return None
            payload += s

        return (ptype, payload)

    def sendPacket(self, ptype, payload):

        assert self.sock is not None

        preamb = 0xdeadbeef
        plen = 24 + len(payload)
        origin = 2
        padding = 0
        remain = 4 + len(payload)

        hdr = struct.pack('<IIIII',
                          preamb, plen, origin, padding, remain, ptype)

        self.sock.send(hdr + payload)


class ArtemisClientProtocol:
    """Artemis client-side packet parser/formatter."""

    def __init__(self, conn):
        self.conn = conn
        self.handler = None

    def handlePacket(self, ptype, payload):
        """Decode received packet and pass it to the client message handler."""

        if ptype == PacketType.DifficultyPacket.value and len(payload) == 8:
            (difficulty, gametype) = struct.unpack('<II', payload)
            self.handler.handleDifficulty(difficulty, gametype)

        elif ptype == PacketType.WelcomePacket.value:
            msg = payload.decode('latin-1')
            self.handler.handleWelcome(msg)

        elif ptype == PacketType.VersionPacket and len(payload) == 24:
            version = struct.unpack('<III', payload)
            self.handler.handleVersion(version)

        else:
            dbg('WARNING: Got unknown packet ptype=0x%08x payload_len=%d' %
                (ptype, len(payload)))


class ArtemisClientHandler:
    """Artemis client-side command handler."""

    def __init__(self, proto):
        self.proto = proto

    def handleDifficulty(self, difficulty, gametype):
        dbg('DifficultyPacket: difficulty=%d gametype=%d' % (difficulty, gametype))    

    def handleVersion(self, version):
        dbg('VersionPacket: %r' % (version,))

    def handleWelcome(self, msg):
        dbg('WelcomePacket: %r' % (msg,))


def main():

    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    serverhost = sys.argv[1]

    conn = ArtemisClientConnection(serverhost)
    conn.connect()

    proto   = ArtemisClientProtocol(conn)
    handler = ArtemisClientHandler(proto)
    proto.handler = handler

    while conn.isConnected():

        pkt = conn.getPacket()
        if pkt is not None:
            (ptype, payload) = pkt
            proto.handlePacket(ptype, payload)


if __name__ == '__main__':
    main()

