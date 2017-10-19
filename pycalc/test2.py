# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'test2.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class KWidget(QtGui.QWidget):
    def __init__(self,parent=None):
        super(KWidget,self).__init__(parent)
        #self.initUI()
        #self.mainwindow = None
    #def get_mainwindow(self, mainwindow):
    #    self.mainwindow = mainwindow
        self.key_tool = parent
        self.key_tool.st()
    def keyReleaseEvent(self,  e):
        if e.key() == QtCore.Qt.Key_Left:
            self.key_tool.hold()
            #print "Key_Left!!!!!!!!"
        if e.key() == QtCore.Qt.Key_Right:
            self.key_tool.hold()
            #print "Key_Right!!!!!!!!"
        if e.key() == QtCore.Qt.Key_Up:
            self.key_tool.hold()
            #print "FRONT!!!!!!!!"
        if e.key() == QtCore.Qt.Key_Down:
            self.key_tool.hold()
            #print "back!!!!!!!!"
        if e.key() == QtCore.Qt.Key_W:
            self.key_tool.hold()
            #print "up!!!!!!!!"
        if e.key() == QtCore.Qt.Key_S:
            self.key_tool.hold()
            #print "Key_Down!!!!!!!!"
        if e.key() == QtCore.Qt.Key_A:
            self.key_tool.hold()
            #print "turn left!!!!!!!!"
        if e.key() == QtCore.Qt.Key_D:
            self.key_tool.hold()
            #print "turn_right!!!!!!!!"
        
        
        
    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
            print "exiSt!!!!!!!!"
        if e.key() == QtCore.Qt.Key_Left:
            self.key_tool.left()
            #print "Key_Left!!!!!!!!"
        if e.key() == QtCore.Qt.Key_Right:
            self.key_tool.right()
            #print "Key_Right!!!!!!!!"
        if e.key() == QtCore.Qt.Key_Up:
            self.key_tool.front()
            #print "FRONT!!!!!!!!"
        if e.key() == QtCore.Qt.Key_Down:
            self.key_tool.back()
            #print "back!!!!!!!!"
        if e.key() == QtCore.Qt.Key_W:
            self.key_tool.up()
            #print "up!!!!!!!!"
        if e.key() == QtCore.Qt.Key_S:
            self.key_tool.down()
            #print "Key_Down!!!!!!!!"
        if e.key() == QtCore.Qt.Key_A:
            self.key_tool.turn_left()
            #print "turn left!!!!!!!!"
        if e.key() == QtCore.Qt.Key_D:
            self.key_tool.turn_right()
            #print "turn_right!!!!!!!!"
        if e.key() == QtCore.Qt.Key_K:
            self.key_tool.disarm()
            #print "turn_right!!!!!!!!"
        if e.key() == QtCore.Qt.Key_R:
            self.key_tool.arm()
        if e.key() == QtCore.Qt.Key_T:
            self.key_tool.st()
            #self.key_tool.takeoff()
        if e.key() == QtCore.Qt.Key_O:
            self.key_tool.offboard()
        if e.key() == QtCore.Qt.Key_P:
            #self.key_tool.offboard()  
            self.key_tool.position()          
        if e.key() == QtCore.Qt.Key_M:
            self.key_tool.manual()
        if e.key() == QtCore.Qt.Key_N:
            self.key_tool.altitude()
        if e.key() == QtCore.Qt.Key_L:
            self.key_tool.land()



class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(679, 600)
        #self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget = KWidget(MainWindow)
        #self.centralwidget.get_mainwindow(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.pushButton_offboard = QtGui.QPushButton(self.centralwidget)
        self.pushButton_offboard.setGeometry(QtCore.QRect(210, 80, 75, 23))
        self.pushButton_offboard.setObjectName(_fromUtf8("pushButton_offboard"))
        self.lineEdit = QtGui.QLineEdit(self.centralwidget)
        self.lineEdit.setGeometry(QtCore.QRect(80, 80, 113, 20))
        self.lineEdit.setObjectName(_fromUtf8("lineEdit"))
        self.pushButton_takeoff = QtGui.QPushButton(self.centralwidget)
        self.pushButton_takeoff.setGeometry(QtCore.QRect(320, 80, 75, 23))
        self.pushButton_takeoff.setObjectName(_fromUtf8("pushButton_takeoff"))
        self.pushButton_front = QtGui.QPushButton(self.centralwidget)
        self.pushButton_front.setGeometry(QtCore.QRect(140, 200, 75, 23))
        self.pushButton_front.setObjectName(_fromUtf8("pushButton_front"))
        self.pushButton_back = QtGui.QPushButton(self.centralwidget)
        self.pushButton_back.setGeometry(QtCore.QRect(140, 350, 75, 23))
        self.pushButton_back.setObjectName(_fromUtf8("pushButton_back"))
        self.pushButton_left = QtGui.QPushButton(self.centralwidget)
        self.pushButton_left.setGeometry(QtCore.QRect(20, 270, 75, 23))
        self.pushButton_left.setObjectName(_fromUtf8("pushButton_left"))
        self.pushButton_right = QtGui.QPushButton(self.centralwidget)
        self.pushButton_right.setGeometry(QtCore.QRect(260, 270, 75, 23))
        self.pushButton_right.setObjectName(_fromUtf8("pushButton_right"))
        self.pushButton_turn_left = QtGui.QPushButton(self.centralwidget)
        self.pushButton_turn_left.setGeometry(QtCore.QRect(120, 260, 31, 41))
        self.pushButton_turn_left.setObjectName(_fromUtf8("pushButton_turn_left"))
        self.pushButton_up = QtGui.QPushButton(self.centralwidget)
        self.pushButton_up.setGeometry(QtCore.QRect(440, 220, 75, 23))
        self.pushButton_up.setObjectName(_fromUtf8("pushButton_up"))
        self.pushButton_down = QtGui.QPushButton(self.centralwidget)
        self.pushButton_down.setGeometry(QtCore.QRect(440, 320, 75, 23))
        self.pushButton_down.setObjectName(_fromUtf8("pushButton_down"))
        self.pushButton_land = QtGui.QPushButton(self.centralwidget)
        self.pushButton_land.setGeometry(QtCore.QRect(430, 80, 75, 23))
        self.pushButton_land.setObjectName(_fromUtf8("pushButton_land"))
        self.pushButton_download_log = QtGui.QPushButton(self.centralwidget)
        self.pushButton_download_log.setGeometry(QtCore.QRect(440, 470, 101, 23))
        self.pushButton_download_log.setObjectName(_fromUtf8("pushButton_download_log"))
        self.lineEdit_2 = QtGui.QLineEdit(self.centralwidget)
        self.lineEdit_2.setGeometry(QtCore.QRect(212, 470, 191, 20))
        self.lineEdit_2.setObjectName(_fromUtf8("lineEdit_2"))
        self.pushButton_turn_right = QtGui.QPushButton(self.centralwidget)
        self.pushButton_turn_right.setGeometry(QtCore.QRect(200, 260, 31, 41))
        self.pushButton_turn_right.setObjectName(_fromUtf8("pushButton_turn_right"))
        self.verticalSlider = QtGui.QSlider(self.centralwidget)
        self.verticalSlider.setGeometry(QtCore.QRect(560, 190, 22, 160))
        self.verticalSlider.setMinimum(1)
        self.verticalSlider.setMaximum(1000)
        self.verticalSlider.setPageStep(1)
        self.verticalSlider.setOrientation(QtCore.Qt.Vertical)
        self.verticalSlider.setObjectName(_fromUtf8("verticalSlider"))
        self.lcdNumber = QtGui.QLCDNumber(self.centralwidget)
        self.lcdNumber.setGeometry(QtCore.QRect(600, 250, 31, 23))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.lcdNumber.setFont(font)
        self.lcdNumber.setSmallDecimalPoint(False)
        self.lcdNumber.setNumDigits(3)
        self.lcdNumber.setObjectName(_fromUtf8("lcdNumber"))
        self.widget = QtGui.QWidget(self.centralwidget)
        self.widget.setGeometry(QtCore.QRect(40, 440, 120, 80))
        self.widget.setObjectName(_fromUtf8("widget"))
        self.radioButton = QtGui.QRadioButton(self.widget)
        self.radioButton.setGeometry(QtCore.QRect(50, 30, 89, 16))
        self.radioButton.setObjectName(_fromUtf8("radioButton"))
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 679, 23))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QObject.connect(self.pushButton_offboard, QtCore.SIGNAL(_fromUtf8("clicked()")), MainWindow.offboard)
        QtCore.QObject.connect(self.pushButton_takeoff, QtCore.SIGNAL(_fromUtf8("clicked()")), MainWindow.takeoff)
        QtCore.QObject.connect(self.pushButton_front, QtCore.SIGNAL(_fromUtf8("pressed()")), MainWindow.front)
        QtCore.QObject.connect(self.pushButton_front, QtCore.SIGNAL(_fromUtf8("released()")), MainWindow.hold)
        QtCore.QObject.connect(self.pushButton_back, QtCore.SIGNAL(_fromUtf8("pressed()")), MainWindow.back)
        QtCore.QObject.connect(self.pushButton_back, QtCore.SIGNAL(_fromUtf8("released()")), MainWindow.hold)
        QtCore.QObject.connect(self.pushButton_left, QtCore.SIGNAL(_fromUtf8("pressed()")), MainWindow.left)
        QtCore.QObject.connect(self.pushButton_left, QtCore.SIGNAL(_fromUtf8("released()")), MainWindow.hold)
        QtCore.QObject.connect(self.pushButton_right, QtCore.SIGNAL(_fromUtf8("pressed()")), MainWindow.right)
        QtCore.QObject.connect(self.pushButton_right, QtCore.SIGNAL(_fromUtf8("released()")), MainWindow.hold)
        QtCore.QObject.connect(self.pushButton_turn_left, QtCore.SIGNAL(_fromUtf8("pressed()")), MainWindow.turn_left)
        QtCore.QObject.connect(self.pushButton_turn_left, QtCore.SIGNAL(_fromUtf8("released()")), MainWindow.hold)
        QtCore.QObject.connect(self.pushButton_up, QtCore.SIGNAL(_fromUtf8("pressed()")), MainWindow.up)
        QtCore.QObject.connect(self.pushButton_up, QtCore.SIGNAL(_fromUtf8("released()")), MainWindow.hold)
        QtCore.QObject.connect(self.pushButton_down, QtCore.SIGNAL(_fromUtf8("pressed()")), MainWindow.down)
        QtCore.QObject.connect(self.pushButton_down, QtCore.SIGNAL(_fromUtf8("released()")), MainWindow.hold)
        QtCore.QObject.connect(self.pushButton_land, QtCore.SIGNAL(_fromUtf8("clicked()")), MainWindow.land)
        QtCore.QObject.connect(self.pushButton_download_log, QtCore.SIGNAL(_fromUtf8("clicked()")), MainWindow.download_log)
        QtCore.QObject.connect(self.pushButton_turn_right, QtCore.SIGNAL(_fromUtf8("pressed()")), MainWindow.turn_right)
        QtCore.QObject.connect(self.pushButton_turn_right, QtCore.SIGNAL(_fromUtf8("released()")), MainWindow.hold)
        QtCore.QObject.connect(self.verticalSlider, QtCore.SIGNAL(_fromUtf8("valueChanged(int)")), self.lcdNumber.display)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow", None))
        self.pushButton_offboard.setText(_translate("MainWindow", "offboard", None))
        self.pushButton_takeoff.setText(_translate("MainWindow", "takeoff", None))
        self.pushButton_front.setText(_translate("MainWindow", "前", None))
        self.pushButton_back.setText(_translate("MainWindow", "后", None))
        self.pushButton_left.setText(_translate("MainWindow", "左", None))
        self.pushButton_right.setText(_translate("MainWindow", "右", None))
        self.pushButton_turn_left.setText(_translate("MainWindow", "<-", None))
        self.pushButton_up.setText(_translate("MainWindow", "上", None))
        self.pushButton_down.setText(_translate("MainWindow", "下", None))
        self.pushButton_land.setText(_translate("MainWindow", "land", None))
        self.pushButton_download_log.setText(_translate("MainWindow", "download LOG", None))
        self.pushButton_turn_right.setText(_translate("MainWindow", "->", None))
        self.radioButton.setText(_translate("MainWindow", "控制杆", None))

