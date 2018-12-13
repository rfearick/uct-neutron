from PyQt5 import Qt
import sys
import slang
from slang.slanggui import NeutronAnalysisGui

def main():
    # Admire! 
    app = Qt.QApplication(sys.argv)
    gui=NeutronAnalysisGui()
    gui.setWindowTitle("Shared Listmode Analyser for Neutrons and Gammas")
    gui.show()
    sys.exit(app.exec_())

if __name__=="__main__":        
    main()
