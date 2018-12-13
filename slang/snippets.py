"""
Code snippets that started out in the main code and may become useful in future
"""

# start of own navigation toolbar 2
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT
class SlangToolbar2(NavigationToolbar2QT):
    toolitems=(        ('Home', 'Reset original view', 'home', 'home'),
)
    def __init__(self,canvas, parent):
        NavigationToolbar2QT.__init__(self, canvas, parent)
    def _init_toolbar(self):
        print("STB2 ************")
        self.basedir = os.path.join(matplotlib.rcParams['datapath'], 'images')

        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                self.addSeparator()
            else:
                a = self.addAction(self._icon(image_file + '.png'),
                                   text, getattr(self, callback))
                print(a)
                self._actions[callback] = a
                if callback in ['zoom', 'pan']:
                    a.setCheckable(True)
                if tooltip_text is not None:
                    a.setToolTip(tooltip_text)
                if text == 'Subplots':
                    a = self.addAction(self._icon("qt4_editor_options.png"),
                                       'Customize', self.edit_parameters)
                    a.setToolTip('Edit axis, curve and image parameters')
    def home(self):
        pass

# class for toolmanager tools
    class nDumpTool(ToolBase):
        """
        Dump listing of spectrum to file
        Uses: toolmanager
        """
        # keyboard shortcut
        default_keymap = 'd'
        description = 'Dump Tool'

        def trigger(self, *args, **kwargs):
            """
            action if button triggered
            """
            print("Listing the spectrum")
            print(self.figure)
            for p in SpectrumPlotter.openplotlist:
                if p.figure==self.figure:
                    #print("figure found",p.histo.adc1,p.histo.label1)
                    #print("# "+xl+", "+adc+" data", p.histo.label1)
                    filename,_=Qt.QFileDialog.getSaveFileName(None,'Save file',
                                                          '.',"Text data (*.dat)")
                    #print(filename)
                    if filename == '': return
                    #if os.path.exists(filename):
                        # code here to prevent overwrite
                        # NOT NEEDED ON: Mac
                        #msgExists=Qt.QMessageBox()
                        #msgExists.setText("The file already exists")
                        #msgExists.setInformativeText("Do you want to overwrite?")
                        #msgExists.setStandardButtons(Qt.QMessageBox.Save|Qt.QMessageBox.Discard)
                        #msgExists.setDefaultButton(Qt.QMessageBox.Discard)
                        #ret=msgExists.exec()
                        #if ret ==  Qt.QMessageBox.Discard:
                        #    return
                    self.printtofile(p, filename)
                            
        def printtofile(self, plotter, filename):
            """
            print histo to file
            """
            p=plotter
            h=p.histo
            adc=h.adc1
            x,xl=p._getCalibratedScale(adc,h,"chan.",h.size1) ##xl->self.xname?
            if x is None:
                x=np.arange(0.0,float(h.size1))
            with open(filename,"w") as f:
                for j in range(len(x)):
                    print(x[j], p.histo.data[j], file=f)


# sort callback
    
def SortCallback(v0,v1,v2,v3,cutL):
    """
    Callback from sorter to perform calculated sorting
    i.e. use calibrated spectrum to calculate data to sort
    taken from sort-with-calib.py
    """
    Tcon=9.159*calTof/0.3
    T0=Tgamma+Tcon
    Tof=T0-v2+rand()-0.5   # calculate TOF and spread randomly over channel
    if v0<cutL: return
    h3t.increment([0,0,int(Tof),0])
    # if Tof too small to be n, ignore rest
    if v2>Tgamma2: return

    # calculate neutron energy from relativistic kinematics
    betan=Tcon/Tof
    if betan>= 1.0:
        print("sqrt",v2,betan,Tof)
        return
    En=939.565*(1.0/np.sqrt(1.0-betan*betan)-1.0)
    En=int(En*(1024/250.0)+0.5)&1023
    
    #print(Tof,vn,En,int(Tof))
    #h1cut.increment(v)
    #h2cut.increment(v)
    hE.increment([0,0,En,0])
    #h3.increment(v)
    hv.increment([0,0,int(betan*1000.0+0.5),0])

# main toolbar bits
        """
        self.btnAutoc = Qt.QToolButton(toolBar)
        self.btnAutoc.setText("correlate")
        self.btnAutoc.setIcon(Qt.QIcon(Qt.QPixmap(icons.avge)))
        self.btnAutoc.setCheckable(True)
        self.btnAutoc.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.btnAutoc)

        self.lstLabl = Qt.QLabel("Buffer:",toolBar)
        toolBar.addWidget(self.lstLabl)
        self.lstChan = Qt.QComboBox(toolBar)
        self.lstChan.insertItem(0,"8192")
        self.lstChan.insertItem(1,"16k")
        self.lstChan.insertItem(2,"32k")
        toolBar.addWidget(self.lstChan)
        
        self.lstLR = Qt.QLabel("Channels:",toolBar)
        toolBar.addWidget(self.lstLR)
        self.lstLRmode = Qt.QComboBox(toolBar)
        self.lstLRmode.insertItem(0,"LR")
        self.lstLRmode.insertItem(1,"L")
        self.lstLRmode.insertItem(2,"R")
        toolBar.addWidget(self.lstLRmode)
        """


# from testgui.py
    #fileNE213="NE213_025.lst"  # 0deg natLi
    #fileNE213="NE213_026.lst"  # 0deg 12C 
    #fileNE213="NE213_028.lst"  # 16deg natLi
    #fileNE213="NE213_029.lst"  # 16deg 12C 

# from calibrate.py
 
filepath="../../../All raw data and analyses from iTL neutrons 2009/100MeV/NE213/"
fileNa="NE213_032.lst"
fileCs="NE213_034.lst"
fileAmBe="NE213_035.lst"
fileTAC="NE213_037.lst"

"""
# use 3 calibration runs for demo, for 3 sources.
infileCs="../NE213 100 MeV data/NE213_019_137Cs.lst"
infileNa="../NE213 100 MeV data/NE213_017_22Na.lst"
infileAmBe="../NE213 100 MeV data/NE213_020_AmBe.lst"
# add in TAC
infileTAC="../NE213 100 MeV data/NE213_022_TACcal.lst"

infileCs=filepath+fileCs
infileNa=filepath+fileNa
infileAmBe=filepath+fileAmBe
infileTAC=filepath+fileTAC
"""
