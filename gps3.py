import sys
import threading
import serial
import time
from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication, QMainWindow, QInputDialog
from folium import Map, CircleMarker 
import webbrowser
from pathlib import Path

#qtcreator_file  = "gps.ui"
qtcreator_file  = os.path.join(sys._MEIPASS, "gps.ui")
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtcreator_file)
lock = threading.Lock()

class MyApp(QMainWindow, Ui_MainWindow,QObject):
    stopped = pyqtSignal(int)
    started = pyqtSignal(int)
    showmap = pyqtSignal(int)
    def __init__(self):
        QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.Stop.clicked.connect(self.stopped.emit)
        self.Display.clicked.connect(self.started.emit)
        self.Map.clicked.connect(self.showmap.emit)
        self.displayMessage("Click buttons to see data or map")
    def slotData (self, lat, long, tim, sat):
        self.tim.setText(tim)
        self.lat.setText(lat)
        self.long_2.setText(long)
        self.sat.setText(sat) 
    def takeInput(self):
        name, done1 = QInputDialog.getText(
             self, 'Input Dialog', 'Enter your COM: "COMX":')
        if done1:
             self.comChoice.setText(str(name))
             global portNr
             portNr = name
    def displayMessage(self,string):
        self.message.setText(string)
        
class DataFromGPS():
    def __init__(self, lat, longi, time, sat):
        self.lat = lat
        self.longi = longi
        self.time = time
        self.sat = sat

class DisplayData(QObject):
    valueChanged = pyqtSignal(str, str, str, str)
    text = pyqtSignal(str)
    choice = 0
    def __init__(self, gps, port):
        super(DisplayData, self).__init__()
        self.gps = gps
        self.port = port
    def calculate(self,lat,ns,longi,ew,tim):
        latDeg = int(lat / 100)
        longiDeg = int(longi / 100)
        latMin = round((lat / 100 - latDeg) * 100 / 60, 8)
        longiMin = round((longi / 100 - longiDeg) * 100 / 60, 8)
        latitude = latDeg + latMin
        longitude = longiDeg + longiMin
        time = tim[0:2] + ":" + tim[2:4] + ":" + tim[4:6]
        if ns == "S":
            latitude *= (-1)
        if ew == "W":
            longitude *= (-1)
        return [latitude, longitude, time]
    def getAndDisplay(self):
        while(1):
            if self.choice == 1:
                with lock:
                    data = str(port.readline())
                    if "$GPGLL" in data:
                        d = data.split(",")
                        try:
                            [gps.lat, gps.longi, gps.time] = self.calculate(d[1], d[2], d[3], d[4], d[5])
                            self.valueChanged.emit(gps.lat, gps.longi, gps.time, gps.sat)
                        except:
                            self.text.emit("Invalid data!")
                    elif "$GPGGA" in data:
                        d = data.split(",")
                        try:
                            [gps.lat, gps.longi, gps.time] = self.calculate(d[2], d[3], d[4], d[5], d[1])
                            gps.sat = d[7]
                            self.valueChanged.emit(gps.lat, gps.longi, gps.time, gps.sat)
                        except:
                            self.text.emit("Invalid data!")     
            elif self.choice == 0:
                pass
    def start(self):
        self.choice = 1
    def stop(self):
        self.choice = 0
    def sendData(self):
        try:
            data = [gps.lat, gps.longi]
            mapHere = Map(tiles = 'openstreetmap', zoom_start = 15, max_zoom = 25, control_scale = True, location = data)
            CircleMarker(location = data, radius = 20, fill = True).add_to(mapHere)
            mapHere.save("Map.html")
            webbrowser.open("Map.html", new = 2)
            self.text.emit("Map opens in browser")
        except:
            self.text.emit("No data available")
        
if __name__ == "__main__":
    
    portNr = "0"
    gps = DataFromGPS(' ', ' ', ' ', ' ')
    app = QApplication(sys.argv)
    window = MyApp()
    window.takeInput()
    port = serial.Serial(portNr, 9600, timeout = 0.5)
    data = DisplayData(gps, port)
    display = threading.Thread(target = data.getAndDisplay, args = (), daemon = True)
    data.text.connect(window.displayMessage)
    data.valueChanged.connect(window.slotData)
    window.stopped.connect(data.stop)
    window.started.connect(data.start)
    window.showmap.connect(data.sendData)
    display.start()
    window.show()
    
    ret = app.exec_()
    port.close()
    sys.exit(ret)

