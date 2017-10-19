#coding:utf-8
from PyQt4 import QtGui  
from test2 import Ui_MainWindow  

  
class MyWindow(QtGui.QMainWindow,Ui_MainWindow):  
    def __init__(self):  
        super(MyWindow,self).__init__()  
        self.setupUi(self)  

  
    def connect_flight(self):
        print ('start test')
        print (self.lineEdit.text())
    def aa(self):
        pass
if __name__=="__main__":  
    import sys  
  
    app=QtGui.QApplication(sys.argv)  
    myshow=MyWindow()  
    myshow.show()  
    sys.exit(app.exec_())  