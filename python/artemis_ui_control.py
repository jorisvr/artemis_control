#!/usr/bin/python3

import sys
import optparse
import time
import socket
import select
import serial

#import PIL.ImageGrab
import ctypes
import win32api
import win32con

VERBOSE = 1


class WinMouseInput(ctypes.Structure):
    _fields_ = [        
        ('dx',          ctypes.c_int),
        ('dy',          ctypes.c_int),
        ('mouseData',   ctypes.c_uint),
        ('dwFlags',     ctypes.c_uint),
        ('time',        ctypes.c_uint),
        ('dwExtraInfo', ctypes.c_void_p) ]

class WinKeybdInput(ctypes.Structure): 
    _fields_ = [
        ('wVk',         ctypes.c_ushort),
        ('wScan',       ctypes.c_ushort),
        ('dwFlags',     ctypes.c_uint),
        ('time',        ctypes.c_uint),
        ('dwExtraInfo', ctypes.c_void_p) ]

class WinHardwareInput(ctypes.Structure):    
    _fields_ = [
        ('uMsg',        ctypes.c_uint),
        ('wParamL',     ctypes.c_ushort),
        ('wParamH',     ctypes.c_ushort) ]

class WinInput(ctypes.Structure):

    class __InputUnion(ctypes.Union):
        _fields_ = [
            ('mi',      WinMouseInput),
            ('ki',      WinKeybdInput),
            ('hi',      WinHardwareInput) ]

    _fields_ = [
        ('type',        ctypes.c_uint),
        ('u',           __InputUnion) ]


class WinError(Exception):
    pass


class WinStuff:
    """Dirty Win32 tricks to control the game."""

    BUTTON_LEFT = 0
    BUTTON_RIGHT = 1
    BUTTON_MIDDLE = 2

    __wGetLastError     = ctypes.windll.kernel32.GetLastError
    __wFormatMessage    = ctypes.windll.kernel32.FormatMessageW
    __wGetDC            = ctypes.windll.user32.GetDC
    __wReleaseDC        = ctypes.windll.user32.ReleaseDC
    __wGetSystemMetrics = ctypes.windll.user32.GetSystemMetrics
    __wSendInput        = ctypes.windll.user32.SendInput
    __wGetPixel         = ctypes.windll.gdi32.GetPixel

    def __init__(self, eventDelay=0.001):
        """Create required system handles."""

        self.eventDelay = eventDelay

        if VERBOSE: print("creating device context")
        self.hdc = self.__wGetDC(None)
        if not self.hdc:
            raise WinError("Can not get Device Context for display (%s)" %
                           self.getLastErrorStr())

#        setdpiaware = getattr(ctypes.windll.shcore, 'SetProcessDpiAwareness',
#                              None)
#        if setdpiaware is not None:
#            setdpiaware(1)

    def __del__(self):

        if self.hdc:
            self.__wReleaseDC(None, self.hdc)
            self.hdc = 0

    def close(self):
        """Release system handles."""

        assert self.hdc
        self.__wReleaseDC(None, self.hdc)
        self.hdc = 0

    def getScreenSize(self):
        """Return screen size as a tuple (xpixels, ypixels)."""

        xsize = self.__wGetSystemMetrics(win32con.SM_CXSCREEN)
        ysize = self.__wGetSystemMetrics(win32con.SM_CYSCREEN)
        return (xsize, ysize)

    def getPixel(self, xpos, ypos):
        """Return color of specified pixel as
        (R,G,B) tuple in range 0 .. 255."""

        assert self.hdc
        rgb = self.__wGetPixel(self.hdc, xpos, ypos)
        return (rgb & 0xff, (rgb >> 8) & 0xff, (rgb >> 16) & 0xff)

    def moveMouse(self, xpos, ypos):
        """Move the mouse cursor to the specified absolute mouse coordinates.
        
        Coordinate range is 0 .. 65535, where (0,0) is the upper left corner
        and (65535,65535) is the lower right corner of the screen.
        """

        inp = WinInput()
        inp.type = win32con.INPUT_MOUSE
        inp.u.mi.dx = xpos
        inp.u.mi.dy = ypos
        inp.u.mi.mouseData = 0
        inp.u.mi.dwFlags = win32con.MOUSE_MOVED | win32con.MOUSEEVENTF_ABSOLUTE
        inp.u.mi.time = 0
        inp.u.mi.dwExtraInfo = None

        nInputs = 1
        pInputs = ctypes.byref(inp)
        cbSize = ctypes.sizeof(inp)
        ret = self.__wSendInput(nInputs, pInputs, cbSize)

        if ret != 1:
            raise WinError("Can not send mouse move input event (%s)" %
                           self.getLastErrorStr())

    def mouseButton(self, button, state):
        """Press or release a mouse button.

        button = 0 for left button, 1 for right button, 2 for middle button.
        state = 1 for press, 0 for release.
        """

        assert button in (0, 1, 2)
        if button == 0:
            ev = ( win32con.MOUSEEVENTF_LEFTDOWN if state
                   else win32con.MOUSEEVENTF_LEFTUP )
        elif button == 1:
            ev = ( win32con.MOUSEEVENTF_RIGHTDOWN if state
                   else win32con.MOUSEEVENTF_RIGHTUP )
        elif button == 2:
            ev = ( win32con.MOUSEEVENTF_MIDDLEDOWN if state
                   else win32con.MOUSEEVENTF_MIDDLEUP )

        inp = WinInput()
        inp.type = win32con.INPUT_MOUSE
        inp.u.mi.dx = 0
        inp.u.mi.dy = 0
        inp.u.mi.mouseData = 0
        inp.u.mi.dwFlags = ev
        inp.u.mi.time = 0
        inp.u.mi.dwExtraInfo = None

        nInputs = 1
        pInputs = ctypes.byref(inp)
        cbSize = ctypes.sizeof(inp)
        ret = self.__wSendInput(nInputs, pInputs, cbSize)

        if ret != 1:
            raise WinError("Can not send mouse click input event (%s)" %
                           self.getLastErrorStr())

    def mouseClick(self, xpos, ypos, button):
        """Optionally move the mouse, then click the specified button."""

        time.sleep(self.eventDelay)
        self.moveMouse(xpos, ypos)
        time.sleep(self.eventDelay)
        self.mouseButton(button, 1)
        time.sleep(self.eventDelay)
        self.mouseButton(button, 0)

    def keyEvent(self, key, state):
        """Press or release the specified key."""

        inp = WinInput()
        inp.type = win32con.INPUT_KEYBOARD
        if isinstance(key, str):
            inp.u.ki.wVk = ord(key)
        elif isinstance(key, bytes):
            (inp.u.ki.wVk,) = key
        else:
            inp.u.ki.wVk = key
        inp.u.ki.wScan = 0
        inp.u.ki.dwFlags = 0 if state else win32con.KEYEVENTF_KEYUP
        inp.u.ki.time = 0
        inp.u.ki.dwExtraInfo = None

        nInputs = 1
        pInputs = ctypes.byref(inp)
        cbSize = ctypes.sizeof(inp)
        ret = self.__wSendInput(nInputs, pInputs, cbSize)

        if ret != 1:
            raise WinError("Can not send keyboard input event (%s)" %
                           self.getLastErrorStr())

    def keyType(self, key):
        """Type the specified key.

        key = '0' .. '9' or 'A' .. 'Z' or win32con.VK_xxx constant
        """

        time.sleep(self.eventDelay)
        self.keyEvent(key, 1)
        time.sleep(self.eventDelay)
        self.keyEvent(key, 0)

    def getLastErrorStr(self):
        """Return error message for last error."""

        buffer = ctypes.create_unicode_buffer(128)

        dwMessageId = self.__wGetLastError()

        dwFlags = win32con.FORMAT_MESSAGE_FROM_SYSTEM
        lpSource = None
        dwLanguageId = 0
        lpBuffer = ctypes.byref(buffer)
        nSize = 128
        Arguments = None

        self.__wFormatMessage(dwFlags, lpSource, dwMessageId, dwLanguageId,
                              lpBuffer, nSize, Arguments)

        return buffer.value.rstrip()


class DisplayDevice(ctypes.Structure):
    _fields_ = [
        ('cb',           ctypes.c_uint),
        ('DeviceName',   ctypes.c_wchar * 32),
        ('DeviceString', ctypes.c_wchar * 128),
        ('StateFlags',   ctypes.c_uint),
        ('DeviceID',     ctypes.c_wchar * 128),
        ('DeviceKey',    ctypes.c_wchar * 128) ]


def enumDisplayDevices():
    """Return the full list of display devices in the system as
    a list of DisplayDevice objects."""

    devs = [ ]
        
    i = 0
    while True:

        displayDevice = DisplayDevice()
        displayDevice.cb = ctypes.sizeof(displayDevice)
        lpDevice = None
        iDevNum = i
        lpDisplayDevice = ctypes.byref(displayDevice)
        dwFlags = 0

        ret = ctypes.windll.user32.EnumDisplayDevicesW(lpDevice,
                                                       iDevNum,
                                                       lpDisplayDevice,
                                                       dwFlags)

        if not ret:
            break

        devs.append(displayDevice)
        i += 1

    return devs


def isDesktopPrimaryDisplay(displayDevice):
    """Return True if the specified DisplayDevices is aDISPLAY_DEVICE_ATTACHED_TO_DESKTOPttached
    to the primary desktop."""

    return (displayDevice.StateFlags & win32con.DISPLAY_DEVICE_PRIMARY_DEVICE) != 0


def createDeviceContext(deviceName):
    """Create device context for the specified display device
    and return the device handle, or return None in case of failure."""

    lpszDriver = "DISPLAY"
    lpszDevice = str(deviceName)
    lpszOutput = None
    lpInitData = None
    
    ret = ctypes.windll.gdi32.CreateDeviceW(lpszDriver,
                                            lpszDevice,
                                            lpszOutput,
                                            lpInitData)

    return ret


class TcpServer:
    
    def __init__(self, port, handler):
        self.port = port
        self.handler = handler
        self.srvsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srvsock.bind(('', port))
        self.srvsock.listen(1)
        self.clients = []
        self.rxbufs = { }
        self.stop = False

    def run(self):
        while not self.stop:
            self.step()

    def step(self):
        rfds = [ self.srvsock ] + self.clients
        (rfds, wfds, xfds) = select.select(rfds, [], [])
        for sock in rfds:
            if sock is self.srvsock:
                conn, addr = sock.accept()
                print("New client", conn)
                self.clients.append(conn)
                conn.sendall(b'Hello\n')
            else:
                sock.setblocking(False)
                w = sock.recv(4096)
                sock.setblocking(True)
                if w:
                    if sock in self.rxbufs:
                        w = self.rxbufs[sock] + w
                    cmds = w.split(b'\n')
                    self.rxbufs[sock] = cmds[-1]
                    for cmd in cmds[:-1]:
                        self.handlecmd(sock, cmd.strip())
                else:
                    print("Client", sock, "closed connection")
                    sock.close()
                    if sock in self.rxbufs:
                        del self.rxbufs[sock]
                    self.clients.remove(sock)

    def handlecmd(self, sock, cmd):
        print("Got command", repr(cmd), "from", sock)
        if cmd.lower() == b'pause':
            self.handler.pause()
            sock.sendall(b'Ok\n')
        else:
            sock.sendall(b'Unknown_Cmd\n')


def commandLoop(dev, handler):
    """Command loop for serial port interfacing."""

    while True:
        s = dev.readline()
        s = s.strip()
        print("Got command", repr(s))
        if s.lower() == b'pause':
            handler.pause()
            dev.write(b'Ok\n')
        else:
            print("ERROR: Unknown command", repr(s))


def ctrlc_handler(ctrlType):
    # needed to be able to Ctrl-C out of select() on Windows
    sys.exit(1)


def main():

    if VERBOSE: print("starting main")

    parser = optparse.OptionParser()
    parser.add_option("--tcp", action="store_true",
                      help="Enable TCP server for accepting control messages")
    parser.add_option("--port", action="store", type="int", default=5123,
                      help="TCP port number for control messages")
    parser.add_option("--serial", action="store", type="string",
                      help="Read control messages from serial port")
    parser.add_option("--baud", action="store", type="int", default=38400,
                      help="Baud rate of serial port")
    (options, args) = parser.parse_args()

    if args:
        print("ERROR: Unexpected arguments", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    if (not options.tcp) and (not options.serial):
        print("ERROR: Specify either --tcp or --serial <port>", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    if options.tcp and options.serial:
        print("ERROR: Combination of --tcp and --serial not supported", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    if VERBOSE: print("setting ctrlc handler")
    win32api.SetConsoleCtrlHandler(ctrlc_handler)

    if VERBOSE: print("initializing Windows stuff")
    w = WinStuff()

    class Handler:

        def pause(self):
            # press ESC
            w.keyType(win32con.VK_ESCAPE)
            time.sleep(0.02)
            # click pause button (coordinates in range 0 .. 65535 for full screen)
            PAUSE_BUTTON_X = 6143
            PAUSE_BUTTON_Y = 6675
            w.mouseClick(PAUSE_BUTTON_X, PAUSE_BUTTON_Y, w.BUTTON_LEFT)
            time.sleep(0.02)
            # press ESC again
            w.keyType(win32con.VK_ESCAPE)
            time.sleep(0.02)

    if VERBOSE: print("initializing command handler")
    handler = Handler()

    if options.tcp:
        srv = TcpServer(options.port, handler)
        print("Waiting for TCP connections on port", options.port)
        srv.run()

    elif options.serial:
        if VERBOSE: print("opening serial port")
        dev = serial.Serial(port=options.serial, baudrate=options.baud)
        print("Reading commands from serial port", options.serial)
        commandLoop(dev, handler)

"""    
    i = 0
    while 1:
        
        (xs,ys) = w.getScreenSize()
        print("Screen size", xs, "x", ys)

        t1 = time.time()
        img = PIL.ImageGrab.grab()
        i += 1
#        img.save('image%04d.png' % i)
        t2 = time.time()
        print(t2-t1)

        time.sleep(2)
"""
    
if __name__ == '__main__':
    main()

