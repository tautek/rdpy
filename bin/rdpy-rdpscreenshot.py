#!/usr/bin/python
#
# Copyright (c) 2014 Sylvain Peyrefitte
#
# This file is part of rdpy.
#
# rdpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

"""
example of use rdpy
take screenshot of login page
"""

import sys, os, getopt

from PyQt4 import QtCore, QtGui
from rdpy.protocol.rdp import rdp
from rdpy.ui.qt4 import RDPBitmapToQtImage
import rdpy.base.log as log
from twisted.internet import task

#set log level
log._LOG_LEVEL = log.Level.INFO

class RDPScreenShotFactory(rdp.ClientFactory):
    """
    @summary: Factory for screenshot exemple
    """
    __INSTANCE__ = 0
    def __init__(self, width, height, path, timeout):
        """
        @param width: width of screen
        @param height: height of screen
        @param path: path of output screenshot
        @param timeout: close connection after timeout s without any updating
        """
        RDPScreenShotFactory.__INSTANCE__ += 1
        self._width = width
        self._height = height
        self._path = path
        self._timeout = timeout
        
    def clientConnectionLost(self, connector, reason):
        """
        @summary: Connection lost event
        @param connector: twisted connector use for rdp connection (use reconnect to restart connection)
        @param reason: str use to advertise reason of lost connection
        """
        log.info("connection lost : %s"%reason)
        RDPScreenShotFactory.__INSTANCE__ -= 1
        if(RDPScreenShotFactory.__INSTANCE__ == 0):
            reactor.stop()
            app.exit()
        
    def clientConnectionFailed(self, connector, reason):
        """
        @summary: Connection failed event
        @param connector: twisted connector use for rdp connection (use reconnect to restart connection)
        @param reason: str use to advertise reason of lost connection
        """
        log.info("connection failed : %s"%reason)
        RDPScreenShotFactory.__INSTANCE__ -= 1
        if(RDPScreenShotFactory.__INSTANCE__ == 0):
            reactor.stop()
            app.exit()
        
        
    def buildObserver(self, controller, addr):
        """
        @summary: build ScreenShot observer
        @param controller: RDPClientController
        @param addr: address of target
        """
        class ScreenShotObserver(rdp.RDPClientObserver):
            """
            @summary: observer that connect, cache every image received and save at deconnection
            """
            def __init__(self, controller, width, height, path, timeout):
                """
                @param controller: RDPClientController
                @param width: width of screen
                @param height: height of screen
                @param path: path of output screenshot
                @param timeout: close connection after timeout s without any updating
                """
                rdp.RDPClientObserver.__init__(self, controller)
                controller.setScreen(width, height);
                self._buffer = QtGui.QImage(width, height, QtGui.QImage.Format_RGB32)
                self._path = path
                self._timeout = timeout
                self._startTimeout = False
                
            def onUpdate(self, destLeft, destTop, destRight, destBottom, width, height, bitsPerPixel, isCompress, data):
                """
                @summary: callback use when bitmap is received 
                """
                image = RDPBitmapToQtImage(destLeft, width, height, bitsPerPixel, isCompress, data);
                with QtGui.QPainter(self._buffer) as qp:
                #draw image
                    qp.drawImage(destLeft, destTop, image, 0, 0, destRight - destLeft + 1, destBottom - destTop + 1)
                if not self._startTimeout:
                    self._startTimeout = False
                    reactor.callLater(self._timeout, self.checkUpdate)
                   
            def onReady(self):
                """
                @summary: callback use when RDP stack is connected (just before received bitmap)
                """
                log.info("connected %s"%addr)
            
            def onClose(self):
                """
                @summary: callback use when RDP stack is closed
                """
                log.info("save screenshot into %s"%self._path)
                self._buffer.save(self._path)
                
            def checkUpdate(self):
                self._controller.close();
        
        return ScreenShotObserver(controller, self._width, self._height, self._path, self._timeout)
        
def help():
    print "Usage: rdpy-rdpscreenshot [options] ip[:port]"
    print "\t-w: width of screen default value is 1024"
    print "\t-l: height of screen default value is 800"
    print "\t-o: file path of screenshot default(/tmp/rdpy-rdpscreenshot.jpg)"
    print "\t-t: timeout of connection without any updating order (default is 2s)"
        
if __name__ == '__main__':
    #default script argument
    width = 1024
    height = 800
    path = "/tmp/"
    timeout = 5.0
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hw:l:o:t:")
    except getopt.GetoptError:
        help()
    for opt, arg in opts:
        if opt == "-h":
            help()
            sys.exit()
        elif opt == "-w":
            width = int(arg)
        elif opt == "-l":
            height = int(arg)
        elif opt == "-o":
            path = arg
        elif opt == "-t":
            timeout = float(arg)
    
    #create application
    app = QtGui.QApplication(sys.argv)
    
    #add qt4 reactor
    import qt4reactor
    qt4reactor.install()
    
    from twisted.internet import reactor
        
    for arg in args:      
        if ':' in arg:
            ip, port = arg.split(':')
        else:
            ip, port = arg, "3389"
            
        reactor.connectTCP(ip, int(port), RDPScreenShotFactory(width, height, path + "%s.jpg"%ip, timeout))
        
    reactor.runReturn()
    app.exec_()