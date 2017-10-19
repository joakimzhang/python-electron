#coding:utf-8
from PyQt5 import QtWidgets  
from test import Ui_MainWindow  
from PyQt5.QtWidgets import QFileDialog  
  
class MyWindow(QtWidgets.QMainWindow,Ui_MainWindow):  
    def __init__(self):  
        super(MyWindow,self).__init__()  
        self.setupUi(self)  
        #self.fileOpen.triggered.connect(self.openMsg)      #菜单的点击事件是triggered  
  
    def connect_flight(self):
        print ('start test')
        print (self.lineEdit.text())
    def aa(self):
        pass
if __name__=="__main__":  
    import sys  
  
    app=QtWidgets.QApplication(sys.argv)  
    myshow=MyWindow()  
    myshow.show()  
    sys.exit(app.exec_())  