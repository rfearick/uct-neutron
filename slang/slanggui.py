"""
===========
slanggui.py
===========

GUI for Shared Listmode Analyser for Neutrons and Gammas.

Sort lst files and display histograms for NE213 and FC detectors.

Also permits calibration of NE213 spectra.

-----
"""
#!/usr/bin/env python

# working multithread pyqt5 code
# taken from develop/testbed3.py

"""
TODO
SpectrumPlot -- too many names
SpectrumPlot -- handle start of sort/interaction with update timer
"""

import sys
import os
from . import __path__ as packagepath

from .eventlist import Histogram, Sorter, EventSource
from .eventlist import EventFlags, Gate2d, gatelist

#simplify event flags
TIMER   =EventFlags.TIMER
PAD     =EventFlags.PAD
RTC     =EventFlags.RTC
SYNCHRON=EventFlags.SYNCHRON
ADCEVENT=EventFlags.ADCEVENT
ADC1=EventFlags.ADC1
ADC2=EventFlags.ADC2
ADC3=EventFlags.ADC3
ADC4=EventFlags.ADC4

# event groups
GROUP_NE213=ADC1+ADC2+ADC3
GROUP_MONITOR=ADC4
GROUP_FC=ADC1+ADC3

from PyQt5 import Qt, QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import numpy as np
import matplotlib
# Make sure that we are using QT5
matplotlib.use('Qt5Agg')
#matplotlib.rcParams['toolbar'] = 'toolmanager'
matplotlib.rcParams['toolbar'] = 'toolbar2'
import matplotlib.pyplot as plt
import matplotlib.path as path
from matplotlib.widgets import SpanSelector, PolygonSelector
import configparser

import logging
logger=logging.getLogger("neutrons")
logger.propagate=False  # don't log message via root logger to console
logger.setLevel(logging.INFO)

from .supportclasses import PlotTreeModel, PlotTreeView, EditMatplotlibToolbar
from .analysisdata import Calibration, AnalysisData

import slang.icons as icons   # part of this package -- toolbar icons
import time

plt.ion()       # turn on interactive mode of matplotlib

from matplotlib.backend_tools import ToolBase, ToolToggleBase

def generatepathname( basename, extension=".dat" ):
    """
    Generate a new unique  file name from base name + sequence number

    Parameters
    ----------

    basename:   str, base name from which filename is constructed
    extension:  optional str, file name extension

    Returns
    -------

    filename:   str, full path for generated file name

    Note: unused for now.
    """
    i=1
    filename="{}{}{}".format(basename, str(i).zfill(4), extension)
    while os.path.exists(filename):
        i += 1
        filename = "{}{}{}".format(basename, str(i).zfill(4), extension)
    return filename

    
class SpectrumPlotter(Qt.QObject):
    """
    define a spectrum plot

    Parameters
    ----------

    parent:    main window; defines the plot model we use
    h     :    histogram to plot
    tree  :    StardardItemModel row into which plot is inserted in TreeView
    name  :    name given to histogram
    xname :    label for x axis -- default to None
    yname :    label for y axis -- default to None
    """

    openplotlist=[]

    def __init__( self, parent, h, tree, name, xname=None, yname=None  ):
        super().__init__(parent=parent)
        self.plotmodel=parent.plotmodel
        self.parent=parent
        self.histo=h
        self.unsorted=True
        self.opened=False
        self.tree=tree
        self.branchname=tree.text()
        self.name=name
        self.xname=xname if xname is not None else "channel"
        self.yname=yname if yname is not None else "counts per channel"
        self.fig=None
        self.figure=None
        self.lasso=None
        self.gate=None
        self.calibration=Calibration()
        self.timer=Qt.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.update)
        parent.bthread.finished.connect(self.stop_update)
   
    def openPlot(self):
        """
        Called from PlotTreeView to display the plot.
        Plots data corresponding to histogram.
        If sorting in progress, starts a timer to update plot at intervals.
        """
        h=self.histo
        fig=plt.figure(self.branchname+' - '+self.name, constrained_layout=True)
        self._initToolbar(fig)
        nfig=fig.number
        #print('fig',plt.get_fignums(),nfig, self.fig, h.dims, self.unsorted, self.lasso)
        self.drawPlot(h)
        self.opened=True
        fig.canvas.draw_idle()
        self.fig=nfig
        self.figure=fig
        fig.canvas.manager.window.closing.connect(self.closed)
        if self.unsorted: self.timer.start()
        # toolmanager: does not work well yet (mpl 2.2)
        #fig.canvas.manager.toolbar.add_toolitem(
        #    'Dump', "mygroup",0, "drive.png", "DumpTool",False)
        #fig.canvas.manager.toolmanager.add_tool('Dump', self.nDumpTool)
        self.openplotlist.append(self)

    def _initToolbar(self, fig):
        """
        Add our icons to the toolbar
        """
        self._actions={}
        self._active=None
        #tb=fig.canvas.manager.toolbar
        tb=EditMatplotlibToolbar(fig)
        tb.addSeparator()
        a=tb.addAction(Qt.QIcon(packagepath[0]+"/images/select_roi.png"), "roi", self._select_roi)
        a.setCheckable(True)
        self._actions["roi"]=a
        a.setToolTip("Select region of interest")
        a=tb.addAction(Qt.QIcon(packagepath[0]+"/images/save_histo.png"), "saveh", self._save_histo)
        #a.setCheckable(True)
        self._actions["saveh"]=a
        a.setToolTip("Save histo data to file")
        
    def _select_roi(self):
        if self._active == 'roi':
            self._active=None
            self._actions['roi'].setChecked(False)
            self.lasso=None
        else:
            self._active='roi'
            self._actions['roi'].setChecked(True)
            # lasso disappears if window closed and reopened. Must check super
            if not self.unsorted:#self.fig is None:
                ax=self.figure.gca()
                h=self.histo
                if h.dims==2:
                    #from polygonlasso import MyLassoSelector
                    #self.lasso=MyLassoSelector(ax,self.select2dGate,useblit=False)
                    self.lasso=PolygonSelector(ax,self.select2dGate,useblit=False,
                            lineprops=dict(color='c', linestyle='-',
                                           linewidth=2, alpha=0.5))
                else:
                    self.lasso=SpanSelector(ax,self.select1dregion,"horizontal",
                            rectprops = dict(facecolor='blue', alpha=0.5))
       
    def _save_histo(self):
        #print("Listing the spectrum")
        for p in SpectrumPlotter.openplotlist:
            if p.figure==self.figure:
                filename,_=Qt.QFileDialog.getSaveFileName(None,'Save file',
                                                      '.',"Text data (*.dat)")
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
                self.printtofile(filename)

    def printtofile(self, filename):
        """
        print histo to file
        """
        p=self
        h=p.histo
        if h.dims==1:
            adc=h.adc1
            x,xl=p._getCalibratedScale(adc,h,"chan.",h.size1) ##xl->self.xname?
            if x is None:
                x=np.arange(0.0,float(h.size1))
            with open(filename,"w") as f:
                for j in range(len(x)):
                    print(x[j], p.histo.data[j], file=f)
        elif h.dims==2:
            adc=h.adc1
            x,xl=p._getCalibratedScale(h.adc1,h,"chan.",h.size1) ##xl->self.xname?
            if x is None:
                x=np.arange(0.0,float(h.size1))
            y,yl=p._getCalibratedScale(h.adc2,h,"chan.",h.size2) ##xl->self.xname?
            if y is None:
                y=np.arange(0.0,float(h.size2))
            with open(filename,"w") as f:
                for i,xi in enumerate(x):
                    for j,yj in enumerate(y):
                        print(xi, yj, p.histo.data[i][j], file=f)
  
    def select1dregion(self,lo,hi):
        h=self.histo
        x,xl=self._getCalibratedScale(h.adc1,h,"",h.size1)
        #print("lohi",lo,hi)
        ilo,ihi=np.searchsorted(x,(lo,hi))
        #print(ilo,ihi)
        mean=np.sum(x[ilo:ihi]*h.data[ilo:ihi])/np.sum(h.data[ilo:ihi])
        #print("pos",mean)
        plt.axvline(mean)
        if h.dims==1 and h.adc1=="ADC3":
            # update TOF gamma
            #print("update Tgamma")
            if 'TAC' in self.parent.calibration.keys():
                #print("update")
                self.parent.filepick.editTgamma.setText("%.2f"%(mean,))
                self.parent.setAnalysisData("Tgamma", mean)
            self._select_roi() # delselect roi

    def select2dGate(self, verts):
        #print(verts)
        text,ok=Qt.QInputDialog.getItem(self.parent, "Gates",
                                        "Select gate:",
                                        ["neutrons","gammas"], 0, False)
        self.gate=Gate2d(text, verts)
        gatelist[text]=self.gate
        h=self.histo
        adc1=h.adc1
        adc2=h.adc2
        
        if h.dims==2:
            x,xl=self._getCalibratedScale(h.adc1,h,"",h.size1)
            y,yl=self._getCalibratedScale(h.adc2,h,"",h.size2)
            data,xl,yl=h.get_plotdata()
            self.gate.gatearray=np.full_like(data,False,dtype=np.bool)
            nx,ny=np.shape(self.gate.gatearray)
            #print('gate',nx,ny)
            p=path.Path(verts)
            for ix in range(nx):
                for iy in range(ny):
                    #if p.contains_point((float(iy),float(ix))):
                    if p.contains_point((x[iy],y[ix])):
                        self.gate.gatearray[ix,iy]=True
                        #print(ix,iy,'True')
                    #else: print(ix,iy, 'False')
                  
            h.set_gate(text)
            logger.info("Gate %s set"%(text,))
            self._select_roi() # deselectroi

    def drawPlot(self,h):
        """
        Draw the plot on matplotlib canvas.
        """
        if h.dims==1:
            adc=h.adc1
            data,yl,xl=h.get_plotdata()
            x,xl=self._getCalibratedScale(adc,h,xl,h.size1) ##xl->self.xname?
            if x is None:
                plt.plot(data,drawstyle='steps-mid')
                plt.ylabel(yl+' -  '+self.yname)
                plt.xlabel(self.xname)
            else:
                plt.plot(x,data,drawstyle='steps-mid')
                plt.ylabel(yl+' -  '+self.yname)
                plt.xlabel(xl)
                
        else:
            adc1=h.adc1
            adc2=h.adc2
            data,xl,yl=h.get_plotlabels()
            x,xl=self._getCalibratedScale(adc1,h,xl,h.size1)
            y,yl=self._getCalibratedScale(adc2,h,yl,h.size2)
            if x is None: x=[0,h.size1]
            if y is None: y=[0,h.size2]
            plt.imshow(data,origin='lower',vmax=2000,
                       extent=[x[0],x[-1],y[0],y[-1]],
                       aspect='auto')
            ax=plt.gca()
            plt.xlabel(xl+' '+self.xname)
            plt.ylabel(yl+' '+self.yname)

    def _getCalibratedScale(self, adc, h, xl, size):
        """
        Return a calibrated x-axis for the plot.
        """
        x=None
        if 'NE213' not in self.tree.text():
            return x,xl
        if h.calib == None:
            calib=self.calibration
            try:
                # must compensate for histo size
                factor=1024//size  # don't use divisor because 2-d
                if adc==calib.EADC:
                    m=calib.slope*factor  ## /
                    c=calib.intercept*factor ## /
                    x=np.arange(0.0,float(size),1.0)
                    x=m*x+c #(1.0/m)*x-c/m
                    xl="Energy [MeVee]"
                elif adc==calib.TADC:
                    m=calib.TAC*factor  ## /
                    x=np.arange(0.0,float(size),1.0)
                    x=x*m  ## m/x
                    xl="T [ns]"
                else:
                    x=np.arange(0.0,float(size),1.0)
                   
            except:
                x=np.arange(0.0,float(size),1.0)
        else:
            m,xl=h.calib
            x=np.arange(0.0,float(size),1.0)*m
        return x, xl

    @pyqtSlot()
    def update(self):
        """
        Update the plot if timer is active (i.e. sorting active).
        """
        nfig=self.fig
        fig=plt.figure(nfig)
        plt.cla()
        self.drawPlot(self.histo)

    @pyqtSlot()
    def stop_update(self):
        """
        Stop updating plot when sorting done.
        """
        #print('fig',self.fig, ' end update')
        self.unsorted=False
        self.timer.stop()

    @pyqtSlot()
    def closed(self):
        """
        Stop timer when window closed.
        """
        # ignore if close icon clicked twice
        if (self.opened is False) or not self in self.openplotlist: return 
        self.opened=False
        self.openplotlist.remove(self)
        self.timer.stop()

ne213pass=0

def SetupSort(parent):
    """
    Setup a sort of data
    This is hardwired here.
    At some point this will change; there should be some sort builder program.
    """
    global ne213pass

    filepicker=parent.filepick
    maxeventcount=parent.maxeventcount
    
    #infile=filepath+fileNE213
    infile=filepicker.files['NE213']
    #print(infile)
    logger.info(infile)
    # check if spectrum calibrated
    calibration=Calibration()
    if(len(calibration.asDict())==5):
        logger.info("Spectrum is calibrated")

    cutL=2.5
    logger.info("cutL at 2.5 Mev in ch %6.2f"%(calibration.channel(2.5),))
    
    # check if TOF start position calculated
    analysisdata=AnalysisData()
    Tgamma=analysisdata.Tgamma
    TOFStartSet=Tgamma != 0.0
    #print("TOF Tgamma is ",Tgamma)
    logger.info("TOF Tgamma is %.2f",Tgamma)
    
    # set up event source
    E=EventSource(infile)
    
    # define histograms
    h1=Histogram(E, GROUP_NE213, 'ADC1', 512)
    h2=Histogram(E, GROUP_NE213, 'ADC2', 512)
    h3=Histogram(E, GROUP_NE213, 'ADC3', 512)
    h4=Histogram(E, GROUP_MONITOR, 'ADC4', 512)
    h21=Histogram(E, GROUP_NE213, ('ADC1','ADC2'), (256,256),label=('L','S'))
    h13=Histogram(E, GROUP_NE213, ('ADC1','ADC3'), (256,256),label=('L','T'))
    histlist=[h1,h2,h3,h4,h21,h13]

    # hack in gate
    if 'neutrons' in gatelist:
        h21.set_gate('neutrons')
        
    # define sort process
    S=Sorter( E, histlist, gatelist=gatelist, maxcount=maxeventcount)

    # create tree for plots widget
    tree=parent.plotmodel
    ne213pass += 1
    branch=tree.appendGroup( "NE213 data (pass %d)"%(ne213pass,) )

    # create plot items 
    CreatePlot( parent, tree, branch, h1, "NE213 Adc 1" )
    CreatePlot( parent, tree, branch, h2, "NE213 Adc 2" )
    CreatePlot( parent, tree, branch, h3, "NE213 Adc 3" )
    CreatePlot( parent, tree, branch, h4, "NE213 Adc 4" )
    CreatePlot( parent, tree, branch, h21, "NE213 Adc1 v Adc2", xname="Long", yname="Short" )
    CreatePlot( parent, tree, branch, h13, "NE213 Adc1 v Adc3", xname="Long", yname="TOF" )

    if Tgamma > 0.0: # Tgamma is set
        if 'neutrons' in gatelist:
            h1g=Histogram(E, GROUP_NE213, 'ADC1', 512)
            h2g=Histogram(E, GROUP_NE213, 'ADC2', 512)
            h3g=Histogram(E, GROUP_NE213, 'ADC3', 512)
            h4g=Histogram(E, GROUP_MONITOR, 'ADC4', 512)
            h21g=Histogram(E, GROUP_NE213, ('ADC1','ADC2'), (256,256),label=('L','S'))
            h13g=Histogram(E, GROUP_NE213, ('ADC1','ADC3'), (256,256),label=('L','T'))

        h3t=Histogram(E, GROUP_NE213, 'ADC3', 1024)
        hE=Histogram(E, GROUP_NE213, 'Cal3', 1024, label="En", calib=(250.0/1024,"En [MeV]"))
        hv=Histogram(E, GROUP_NE213, 'Cal3', 1024, label="vn", calib=(0.001,"beta_n"))
        CreatePlot( parent, tree, branch, h3t, "Calc tof", yname="tof" )
        CreatePlot( parent, tree, branch, hE, "Calc E", yname="n Energy" )
        CreatePlot( parent, tree, branch, hv, "Calc v", yname="v_n" )
        if 'neutrons' in gatelist:
            CreatePlot( parent, tree, branch, h1g, "NE213 Adc 1 (gated)" )
            CreatePlot( parent, tree, branch, h2g, "NE213 Adc 2 (gated)" )
            CreatePlot( parent, tree, branch, h3g, "NE213 Adc 3 (gated)" )
            CreatePlot( parent, tree, branch, h4g, "NE213 Adc 4 (gated)" )
            CreatePlot( parent, tree, branch, h21g, "NE213 Adc1 v Adc2 (gated)", xname="Long", yname="Short" )
            CreatePlot( parent, tree, branch, h13g, "NE213 Adc1 v Adc3 (gated)", xname="Long", yname="TOF" )
            histlist2=[h3t,hE,hv,h1g,h2g,h3g,h4g,h21g,h13g]
        else:
            histlist2=[h3t,hE,hv]
            
        c=CalculatedEventSort(None)
        S.setExtraSorter(c.sort, histlist2)

    return S

    """
    # some of this to be included in future
    sortadc=[]
    deadtimer=[]
    t0=time.perf_counter()
    """

def CreatePlot( parent, tree, branch, histo, name, xname=None, yname=None ):
    """
    Create a plot object and insert into plot tree.

    Parameters
    ----------
    parent : object
        Qt parent of plot, i.e. top level gui.
    tree : PlotTreeModel
        Tree into which plot is inserted.
    branch : tree node
        Branch in tree to which plot is linked.
    histo : Histogram
        Histogram to be plotted
    name : str
        Name user will see for histogram.
    """
    s=SpectrumPlotter( parent, histo, branch, name, xname=xname, yname=yname)
    tree.appendAt( branch, name, s)
    

class CalculatedEventSort(object):
    """
    Placeholder, not integrated with rest of code.
    """
    def __init__( self, calibration ):

        calibration=Calibration()
        data=AnalysisData()
        self.analysisdata=data
        speed_of_light=data.speed_of_light # m/ns
        target_distance=data.target_distance # m , flight path target to detector
        slope_Tof=calibration.TAC # TAC calibration in channel/ns
        #choffset=(target_distance/speed_of_light)*slope_Tof# channel offset due to flight path
        choffset=(target_distance/speed_of_light)/slope_Tof # channel offset due to flight path
        chT0=self.analysisdata.Tgamma/slope_Tof + choffset # channel of gamma flash at detector ## *
        self.chT0=chT0 # keep copy
        self.choffset=choffset
        self.chTgamma2=self.chT0-5 # arbitrary cutoff
        self.cutL=calibration.channel(data.L_threshold) # convert to channel
        logger.info("chT0, choffset, chTgamma = %5.1f, %5.1f, %5.1f"%(chT0,choffset,chT0-choffset))
        self.start=0
        
    def sort(self,a,v,h):
                         
        v2 = v[2]
        v0 = v[0]
        h3t = h[0]
        hE = h[1]
        hv = h[2]
        if 'neutrons' in gatelist:
            h1g=h[3]            
            h2g=h[4]            
            h3g=h[5]            
            h4g=h[6]            
            h21g=h[7]            
            h13g=h[8]            
        
        Tof=self.chT0-v2+np.random.rand()-0.5   # calculate TOF and spread randomly over channel
        if v0<self.cutL: return
        if 'neutrons' in gatelist:
            gate=gatelist['neutrons']
            #if self.start==0:
                #print(gate,gate.name)
                #print(gate.name, gate.ingate)
            ingate=gate.ingate
            if not ingate:
                #print('gate',ingate)
                return
        #elif self.start==0:
            #print("No gate")
        self.start=1
        h3t.increment([0,0,int(Tof),0])
        # if Tof too small to be n, ignore rest
        if v2>self.chTgamma2: return

        # calculate neutron energy from relativistic kinematics
        betan=self.choffset/Tof
        if betan>= 1.0:
            #print("sqrt",v2,betan,Tof)
            return
        En=939.565*(1.0/np.sqrt(1.0-betan*betan)-1.0)
        En=int(En*1024/250.0+0.5)&1023

        #print(Tof,vn,En,int(Tof))
        #h1cut.increment(v)
        #h2cut.increment(v)
        hE.increment([0,0,En,0])
        #h3.increment(v)
        hv.increment([0,0,int(betan*1000.0+0.5),0])

        h1g.increment(v)
        h2g.increment(v)
        h3g.increment(v)
        h4g.increment(v)
        h21g.increment(v)
        h13g.increment(v)

def SetupFCSort(parent):
    """
    Setup a sort of fission chamber data
    This is hardwired here.
    At some point this will change; there should be some sort builder program.
    """
    filepicker=parent.filepick
    
    infile=filepicker.files['FC']

    # define event source
    E=EventSource(infile)

    # set up histograms
    h1=Histogram(E, GROUP_FC, 'ADC1', 512)
    h3=Histogram(E, GROUP_FC, 'ADC3', 512)
    h4=Histogram(E, GROUP_MONITOR, 'ADC4', 512)
    h13=Histogram(E, GROUP_FC, ('ADC1','ADC3'), (256,256),label=('L','T'))
    histlist=[h1,h3,h4,h13]

    # define sort task
    S=Sorter( E, histlist)

    # create tree for plots widget
    tree=parent.plotmodel
    branch=tree.appendGroup( "Fission Chamber" )
    
    # create plot items
    CreatePlot( parent, tree, branch, h1, "FC Adc 1")
    CreatePlot( parent, tree, branch, h3, "FC Adc 3")
    CreatePlot( parent, tree, branch, h4, "FC Adc 4")
    CreatePlot( parent, tree, branch, h13, "FC Adc1 v Adc3",
                xname="Long", yname="TOF")
    return S


class Task(Qt.QObject):
    """
    Define a task potentially run in background
    """
    finished=pyqtSignal()
    def __init__(self, sorter):
        super().__init__()
        self.task = task

    def starttask(self):
        """
        start the sort task; emit signal when done to release background thread
        """
        logger.info("start task")
        # task.start() ?
        sortadc=self.task.start()
        logger.info("end task")
        self.finished.emit()

class BackgroundSort(Qt.QObject):
    """
    Run sort in a background thread
    """
    finished=pyqtSignal()
    def __init__(self, sorter):
        super().__init__()
        self.sorter = sorter
        
    def task(self):
        """
        start the sort task; emit signal when done to release background thread
        """
        #logger.info("start sorting task")
        sortadc=self.sorter.sort()
        #logger.info("end sorting task")
        self.finished.emit()     
        # sort returns histogram data of adc distribution -- do something with it
    
# initial analysis tasks
analysis_tasks=["Calibrate","Sort NE213","Sort FC"]

class ListLogger(object):
    """
    Stream python logger output to a QtListView.

    Parameters
    ----------
    list : listview
        A listview for output.
    
    """
    def __init__(self, list):
        self.list=list

    def write(self,data):
        """
        Write data to list view.

        1) must remove line feed at end
        2) seems to be a spurious line feed coming through as well
        """
        if len(data)<=1: return
        if data[-1] in ['\r','\n']: data=data[0:-1]
        Qt.QListWidgetItem(data,self.list)

    def flush(self):
        pass

class NeutronAnalysisGui(Qt.QMainWindow):
    """
    Main application container  widget

    Handles toolbar and status.
    """
    def __init__(self, *args):
        Qt.QMainWindow.__init__(self, *args)

        self.calibrator=None
        self.calibration=Calibration()
        d=AnalysisData()
        d.Tgamma=0.0
        """
        calibration values:
        Only the NE213 spectra are calibrated.
        Calibration is stored in a dict()
        The following keys are known:
        'EADC':      adc used for calibrating energy
        'TADC':      adc used for calibrating TOF
        'slope':     gamma calibration slope in MeVee/ch
        'intercept': gamma calibration intercept in MeVee
        'TAC':       TDC slope in ns/ch
        'Tgamma':    Time of gamma burst in raw TOF, used to calc T0 
        """
        self.mainwin=Qt.QSplitter(self)
        self.logwin=Qt.QListWidget(self)
        vlayout=Qt.QVBoxLayout()
        vlayout.addWidget(self.mainwin)
        label=self.makeLabel("Analysis log")
        vlayout.addWidget(label)
        vlayout.addWidget(self.logwin)
        self.setGeometry(10,10,1024,768)
        #self.setCentralWidget(self.mainwin)
        w=Qt.QWidget()
        w.setLayout(vlayout)
        self.setCentralWidget(w)
        logstream=ListLogger(self.logwin)
        loghandler=logging.StreamHandler(logstream)
        loghandler.setFormatter(logging.Formatter(fmt='%(asctime)s : %(levelname)s : %(message)s'))
        logger.addHandler(loghandler)
                
        self.filewidget=Qt.QWidget()
        vlayout=Qt.QVBoxLayout()
        from .fileentry import FilePicker
        self.filepick=FilePicker()
        label=self.makeLabel("Analysis Files")
        vlayout.addWidget(label)
        vlayout.addWidget(self.filepick)
        vlayout.setContentsMargins(1,1,1,1) # cut down margins from 11px
        self.filewidget.setLayout(vlayout)
        self.mainwin.addWidget(self.filewidget)

        self.taskwidget=Qt.QWidget()
        vlayout=Qt.QVBoxLayout()
        self.tasklist=Qt.QListWidget(self)
        self.tasklistitems={}  # keep a dict of these, may expand in future
        for task in analysis_tasks:
            item=Qt.QListWidgetItem(task,self.tasklist)
            item.setFlags(item.flags()&~QtCore.Qt.ItemIsEnabled)
            self.tasklistitems[task]=item
        self.tasklist.setDragDropMode(Qt.QAbstractItemView.InternalMove)
        label=self.makeLabel("Task list")
        vlayout.addWidget(label)
        vlayout.addWidget(self.tasklist)
        vlayout.setContentsMargins(1,1,1,1) # cut down margins from 11px
        self.taskwidget.setLayout(vlayout)
        self.mainwin.addWidget(self.taskwidget)

        # set up user interface
        self.setupMenuBar()
        # toolbar example code taken from dualscopeN.py
        toolBar = Qt.QToolBar(self)
        self.addToolBar(toolBar)
        sb=self.statusBar()
        sbfont=Qt.QFont("Helvetica",12)
        sb.setFont(sbfont)
        sb.showMessage("Status=1")

        # !! use addAction instead ?
        self.btnOpenExpt = Qt.QToolButton(toolBar)
        self.btnOpenExpt.setText("Open expt")
        self.btnOpenExpt.setIcon(Qt.QIcon(Qt.QPixmap(icons.stopicon)))
        #self.btnOpenExpt.setCheckable(True)
        self.btnOpenExpt.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        self.btnOpenExpt.setToolTip("Open list of experiment file names")
        toolBar.addWidget(self.btnOpenExpt)
        
        self.btnSaveExpt = Qt.QToolButton(toolBar)
        self.btnSaveExpt.setText("Save expt")
        self.btnSaveExpt.setIcon(self.style().standardIcon(Qt.QStyle.SP_DriveFDIcon))
        self.btnSaveExpt.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        self.btnSaveExpt.setToolTip("Save list of experiment file names")
        toolBar.addWidget(self.btnSaveExpt)

        """
        self.btnPrint = Qt.QToolButton(toolBar)
        self.btnPrint.setText("Print")
        self.btnPrint.setIcon(Qt.QIcon(Qt.QPixmap(icons.print_xpm)))
        self.btnPrint.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        self.btnPrint.setToolTip("One day, may print something")
        toolBar.addWidget(self.btnPrint)
        """
        
        self.btnSaveData = Qt.QToolButton(toolBar)
        self.btnSaveData.setText("data")
        self.btnSaveData.setIcon(Qt.QIcon(packagepath[0]+"/images/drive.png"))
        self.btnSaveData.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        self.btnSaveData.setToolTip("Save all histogram data to hdf file")
        toolBar.addWidget(self.btnSaveData)

        toolBar.addSeparator()

        self.maxeventcount=None

        self.lblMaxevent = Qt.QLabel("Max event count:",toolBar)
        self.lblMaxevent.setToolTip("Set maximum number of events sorted, or None")
        toolBar.addWidget(self.lblMaxevent)
        self.editMaxevent = Qt.QLineEdit(toolBar)
        self.editMaxevent.setFixedWidth(100)
        self.editMaxevent.editingFinished.connect(self.setMaxEvent)
        self.editMaxevent.setText("None")
        toolBar.addWidget(self.editMaxevent)
        
       # set up a model for spectra plots
        self.plotwidget=Qt.QWidget()
        vlayout=Qt.QVBoxLayout()
        self.plotview=PlotTreeView(self)
        self.plotmodel=PlotTreeModel(self)
        self.plotview.setModel(self.plotmodel)
        self.plotview.setDragDropMode(Qt.QAbstractItemView.InternalMove)
        label=self.makeLabel("Plot list")
        vlayout.addWidget(label)
        vlayout.addWidget(self.plotview)
        vlayout.setContentsMargins(1,1,1,1) # cut down margins from 11px
        self.plotwidget.setLayout(vlayout)
        self.mainwin.addWidget(self.plotwidget)

        # connect signals
        self.tasklist.doubleClicked.connect(self.runTask)
        self.filepick.fileChanged.connect(self.setFilePaths)
        self.filepick.dataChanged.connect(self.setAnalysisData)
        self.filepick.valueChanged.connect(self.setFilePaths)
        self.btnOpenExpt.clicked.connect(self.openFile)
        self.btnSaveExpt.clicked.connect(self.saveFile)
        self.btnSaveData.clicked.connect(self.saveDataAsHDF)
        self.bthread = None

    def makeLabel(self, title):
        """
        Centralize label creation here so all customisation in one place.

        Parameters
        ----------
        title : str
            Text of label.

        Returns
        -------
            label : A Qt label.
        """
        font=Qt.QFont("Helvetica",12,Qt.QFont.Bold)
        label=Qt.QLabel(title)
        label.setFont(font)
        label.setMargin(6)
        label.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
        label.setFrameStyle(Qt.QFrame.StyledPanel|Qt.QFrame.Raised)
        label.setContentsMargins(1,2,1,2)
        return label

    def setupMenuBar(self):
        """
        Configure the menu bar
        """
        import platform
        # Mac (Darwin) needs special treatment
        if platform.system()=="Darwin":
            menuBar=Qt.QMenuBar(None)
        else:
            menuBar=self.menuBar()
        self.mbar=menuBar
        #menuBar.setNativeMenuBar(False)
        menu=menuBar.addMenu("&File")
        action=Qt.QAction('Open Filelist...',None)
        menu.addAction(action)
        self.openfileaction=action
        action.triggered.connect(self.openFile)
        action=Qt.QAction('Save Filelist...',None)
        menu.addAction(action)
        self.savefileaction=action
        action.triggered.connect(self.saveFile)
        action=Qt.QAction('Save Data to HDF...',None)
        menu.addAction(action)
        self.savehdfaction=action
        action.triggered.connect(self.saveDataAsHDF)

    def startSorting(self, setupsorter):
        """
        Start a sort process.

        This will evolve to dispatch different sorts at various times.

        Parameters
        ----------
        setupsorter: function
            Function to set up the sort process.
        """
        # setup sort in background
        if self.bthread is None:
            pass
        elif self.bthread.isRunning():
            logger.warn("Sort already in progress")
            return
        self.bthread=Qt.QThread()
        S=setupsorter(self)
        bobj=BackgroundSort(S)
        bobj.moveToThread(self.bthread)
        self.bthread.started.connect(bobj.task)
        bobj.finished.connect(self.cleanupThread)
        self.bobj=bobj # keep reference
        
        # start sort
        self.bthread.start()
        self.bthread.setPriority(0)
        logger.info("Start background task: "+self.sorttype)
        #print('thread',self.bthread.isRunning())

    @pyqtSlot()
    def cleanupThread(self):
        """
        Quit background thread when sorting done.
        """
        #print("cleanup")
        self.bthread.quit()
        logger.info("End background task: "+self.sorttype)
        if self.sorttype=="Calibrate":
            from . import calibrate as calibrator
            tree=self.plotmodel
            branch=tree.appendGroup( "Calibration" )
            #item=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),"calib")       
            self.calibplot=calibrator.CalibrationPlotter(self.calibrator)
            for k in self.calibplot.histo.keys():
                h=self.calibplot.histo[k]
                if h is not None:
                    tree.appendAt(branch, h.label, self.calibplot)
            self.calibplot.openPlot()
        self.sorttype=None

    def runTask(self,p):
        """
        Placeholder...

        Run an analysis task.

        Should be replaced by something else when all tasks have been decided.

        Parameters
        ----------
        p : index
            A Qt index from task list indicating which task has been double
            clicked.
        """
        m=self.tasklist.itemFromIndex(p)
        sorttype=m.text()
        self.sorttype=sorttype
        logger.info("Run task: "+sorttype)
        if sorttype=="Sort NE213":
            self.startSorting(SetupSort)
        elif sorttype=="Sort FC":
            self.startSorting(SetupFCSort)
        elif sorttype=="Calibrate":
            from . import calibrate as calibrator
            # use 'get' below so default None is returned by no-shows.
            self.calibrator=calibrator.Calibrator(self.filepick.files.get('Na'),
                                                  self.filepick.files.get('Co'),
                                                  self.filepick.files.get('Cs'),
                                                  self.filepick.files.get('AmBe'),
                                                  self.filepick.files.get('TAC'))
            def _SetupCalibSort(self):
                return self.calibrator
            self.startSorting(_SetupCalibSort)
    """
    def updateCalibration(self):
        pass
        if self.calibrator is not None:
            self.calibration.update(self.calibrator.calibration)
    """
        
    def openFile(self,p):
        """
        Read a file name from open file dialog.

        Parameters
        ----------
        p : ignored
        """
        filename,_=Qt.QFileDialog.getOpenFileName(self,'Open file',
                                                  '.',"Experiment (*.exp)")
        if filename == '': return
        C=configparser.ConfigParser(strict=False,inline_comment_prefixes=(';',))
        C.optionxform=lambda option: option
        C.read(filename)
        try:
            files=C.items('Files')
            k=dict(files).keys()
            if 'Na' in k or 'Co' in k or 'Cs' in k or 'AmBe' in k:
                self.filepick.setCalibTab(style='sortfiles')
            self.filepick.setFiles(dict(files))
        except:
            pass
        try:
            data=C.items('Data')
            AnalysisData().setData(dict(data))
            self.filepick.setDataTab()
        except:
            pass # configparser.NoSectionError
        try:
            data=C.items('Calibration')
            self.filepick.setCalibTab(style='entervalues',data=dict(data))
            self.calibration.setData(dict(data))
        except:
            pass # configparser.NoSectionError
        logger.info("Open file "+filename)

    def saveFile(self,p):
        """
        Save a file to file picked in save file dialog.

        Parameters
        ----------
        p : ignored
        """
        if self.filepick.files is None:
            logger.warn("Nothing to save")
            return
        filename,_=Qt.QFileDialog.getSaveFileName(self,'Save file',
                                                  '.',"Experiment (*.exp)")
        if filename == '': return
        C=configparser.ConfigParser(strict=False,inline_comment_prefixes=(';',))
        C.optionxform=lambda option: option
        filedict={}
        filedict['Files']=self.filepick.files
        fd=filedict['Files']
        for key in fd:
            fd[key]=str(fd[key])
        data=AnalysisData().getData()
        if len(data) != 0:
            filedict['Data']=data
        data=self.calibration.getData()
        if len(data) != 0:
            filedict['Calibration']=data
        C.read_dict(filedict)
        # future: ask on existing file - but not needed on OSX !
        f=open(filename,"w")
        C.write(f)
        f.close()
        logger.info("Write file: "+filename)

    def saveDataAsHDF(self, p):
        """
        Save histogram data to hdf5 file.

        Parameters
        ----------
        p : ignored
        """
        #if self.filepick.files is None:
        #    logger.warn("Nothing to save")
        #    return
        import h5py
        def _savedata(path, sp):
            histo=sp.histo
            if isinstance(histo, Histogram):
                _savehisto(path, histo)
            elif isinstance(histo, list):
                """
                For calibration plots.
                CalibrationPlotter keeps a list of histograms.
                We must pick out the one that matches the path from the ListView.
                """
                for h in histo:
                    if h.label in path:
                        _savehisto(path, h)
            else:
                logger.info("saveData got an unknown item")
        def _savehisto(path, h):
            if h.dims==1:
                #print(path+"/data")
                dset=f.create_dataset(path+"/data",data=h.data)
                dset.attrs['type']="h1"
                dset.attrs['adc']=h.adc1
                dset.attrs['adcrange']=h.adcrange1
                dset.attrs['size']=h.size1
                dset.attrs['divisor']=h.divisor1
                #print(h.adc1,h.size1,h.adcrange1,h.divisor1,len(h.data))
            elif h.dims==2:
                #print(path+"/data")
                dset=f.create_dataset(path+"/data",data=h.data)
                dset.attrs['type']="h2"
                dset.attrs['adc1']=h.adc1
                dset.attrs['adc2']=h.adc2
                dset.attrs['adcrange1']=h.adcrange1
                dset.attrs['adcrange2']=h.adcrange2
                dset.attrs['size1']=h.size1
                dset.attrs['size2']=h.size2
                dset.attrs['divisor1']=h.divisor1
                dset.attrs['divisor2']=h.divisor2
                #print(h.adc1,h.size1,h.adcrange1,h.divisor1,len(h.data))
        filename,_=Qt.QFileDialog.getSaveFileName(self,'Save file',
                                                  '.',"HDF Data File (*.hdf5)")
        if filename == '': return
        f=h5py.File(filename,"w")
        self.plotmodel.saveData(_savedata)

    @pyqtSlot('QString')
    @pyqtSlot(int)
    def setFilePaths(self, count):
        """
        Save files entered in text entry widgets.
        """
        if isinstance(count, int):
            #print("filepaths int",count)
            files=self.filepick.files
            calibfiles=set(self.filepick.calibtags)
            if calibfiles.issubset(files.keys()):
                item=self.tasklistitems["Calibrate"]
                #print(calibfiles)
                item.setFlags(item.flags()|QtCore.Qt.ItemIsEnabled)
            if "NE213" in files.keys():
                item=self.tasklistitems[analysis_tasks[1]]
                item.setFlags(item.flags()|QtCore.Qt.ItemIsEnabled)
            if "FC" in files.keys():
                item=self.tasklistitems[analysis_tasks[2]]
                item.setFlags(item.flags()|QtCore.Qt.ItemIsEnabled)
        elif isinstance(count, str):
            # old code for Tgamma field in file tab
            #print("not here?")
            try:
                Tg=float(count)
                d=AnalysisData()
                #print("d",d.Tgamma)
                d.Tgamma=Tg
                if 'TAC' in self.calibration.keys():
                    Tcon=d.target_distance/d.speed_of_light  # in ns
                    T0=Tg+Tcon
                    #print("Tcon, T0=",Tcon,T0)
                    #d.T0=T0
            except:
                logger.error("Tgamma is not a float")

    @pyqtSlot('QString','QString')
    def setAnalysisData(self, tag, data):
        """
        tag is same as attribute name
        """
        if data=='': return
        try:
            fdata=float(data)
        except:
            logger.error(tag+" is not a float")
            return
        #print(tag, data)
            
        d=AnalysisData()
        c=Calibration()
        if tag == 'Tgamma':
            #print("d",d.Tgamma)
            d.Tgamma=fdata
            if 'TAC' in self.calibration.keys():
                Tcon=d.target_distance/d.speed_of_light  # in ns
                logger.info("Tgamma set to %.3f, Tcon=%5.1f, T0=%5.1f"%(fdata,Tcon,d.T0))
            else:
                logger.info("Tgamma set to %.3f"%(fdata,))
                
        elif tag == 'target_distance':
            d.target_distance=fdata
            if 'TAC' in self.calibration.keys():
                Tcon=d.target_distance/d.speed_of_light  # in ns
                logger.info("Tdist set to %5.3f, Tcon=%5.1f, T0=%5.1f"%(fdata,Tcon,d.T0))
            else:
                logger.info("Tdist set to %5.3f"%(fdata,))
        elif tag == 'calibration_gain':
            d.calibration_gain=fdata
            logger.info("Extra calibration gain set to %4.1f"%(fdata,))
        elif tag == 'TAC_interval':
            d.TAC_interval=fdata
            logger.info("TAC interval set to %4.1f"%(fdata,))
        elif tag == "L_threshold":
            d.L_threshold=fdata
            logger.info("L threshold set to %4.1f"%(fdata,))
        elif tag == 'TAC':
            c.TAC=fdata
            logger.info("TAC calibration set to %.3f"%(fdata,))
        elif tag == 'slope':
            c.slope=fdata
            logger.info("slope set to %.4f"%(fdata,))
        elif tag == 'intercept':
            c.intercept=fdata
            logger.info("intercept set to %.4f"%(fdata,))
        else:
            logger.error("Invalid input")

    def setMaxEvent(self):
        maxevent=self.editMaxevent.text()
        #print("maxevent",maxevent)
        if maxevent == 0 or maxevent == "None" or maxevent == "none":
            self.maxeventcount = None
        else:
            try:
                self.maxeventcount = int(maxevent)
                logger.info("Maxevent set to %d"%(self.maxeventcount,))
            except:
                logger.error("Invalid input")
        #self.editMaxevent.setText("None")
        
    """        
    def printPlot(self):
        '''
        Placeholder.
        '''
        p = QPrinter()
    """
        
if __name__=="__main__":        
    # Admire! 
    app = Qt.QApplication(sys.argv)
    gui=NeutronAnalysisGui()
    gui.setWindowTitle("Shared Listmode Analyser for Neutrons and Gammas")
    gui.show()
    #demo.startSorting()
    #app.aboutToQuit.connect(demo.closeAll)
    sys.exit(app.exec_())
