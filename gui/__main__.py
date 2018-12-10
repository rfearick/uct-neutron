from PyQt5 import Qt
import sys
import gui
from gui.testgui import NeutronAnalysisDemo
def main():
    # Admire! 
    app = Qt.QApplication(sys.argv)
    demo=NeutronAnalysisDemo()
    demo.setWindowTitle("The Amazing List File Sorter")
    demo.show()
    #demo.startSorting()
    #app.aboutToQuit.connect(demo.closeAll)
    sys.exit(app.exec_())

if __name__=="__main__":        
    main()
