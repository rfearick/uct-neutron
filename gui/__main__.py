from PyQt5 import Qt
import sys
import gui
from gui.slanggui import NeutronAnalysisGui
def main():
    # Admire! 
    app = Qt.QApplication(sys.argv)
    gui=NeutronAnalysisGui()
    gui.setWindowTitle("The Amazing List File Sorter")
    gui.show()
    #demo.startSorting()
    #app.aboutToQuit.connect(demo.closeAll)
    sys.exit(app.exec_())

if __name__=="__main__":        
    main()
