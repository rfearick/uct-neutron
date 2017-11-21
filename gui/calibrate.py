# for mac
import platform
if platform.system()=="Darwin":
    import matplotlib
    matplotlib.use("Qt5Agg")

filepath="../../../All raw data and analyses from iTL neutrons 2009/100MeV/NE213/"
fileNa="NE213_032.lst"
fileCs="NE213_034.lst"
fileAmBe="NE213_035.lst"
fileTAC="NE213_037.lst"

    
from eventlist import *

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import MultiCursor
from scipy.stats import linregress

"""
Calibrate neutron detector using gamma ray sources.

Calibration mainly uses Compton edges, and first escape peak (12C) of AmBe source.

Energies: 
   22Na      1.062 MeV
  137Cs      0.477 MeV
   12C       3.42, 4.20 MeV  (AmBe source)

Differentiating the spectrum and choosing the lowest point in the region of the 
Compton edge seems to work well enough for scintillation detectors.
See Safari et al., ArXiv 1610.09185

This simple demo presents 3 different calibration spectra and allows the user
to select the calibration points. When all calibration points are selected, the 
calibration is calculated via linear regression, and plotted in a 4th view.
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

# calibration data
chans=[None,None,None,None]
edges=[1.062,0.477,3.42,4.20]
slope,intercept=0.0,0.0
calibration=(None,None)

    
cid_multi=None
fcur=None
multi=None



class Calibrator(object):
    """
    Handle calibration of neutron detection system
    Liquid scintillator calibrated by using gamma sources: 22na, 137Cs and AmBe.
    TAC calibrated using TAC calibrator
    Four calibration list files are specified.
    This object handles the histograms and sorting process.
    input:
        infileNa, infileCs, infileAmBe, infileTAC: 
            file paths to respective list files
    """
    def __init__( self, infileNa, infileCs, infileAmBe, infileTAC):
        self.infileNa = infileNa
        self.infileCs = infileCs
        self.infileAmBe = infileAmBe
        self.infileTAC = infileTAC
        self.hNa = None
        self.hCs = None
        self.hAmBe = None
        self.hTAC = None
        self.calibration=(None,None)

    def sort( self ):
        """
        Define event sources and histograms, then sort data
        """
        # define event sources
        ENa=EventSource(self.infileNa)
        ECs=EventSource(self.infileCs)
        EAmBe=EventSource(self.infileAmBe)
        ETAC=EventSource(self.infileTAC)

        # get event generators
        GNa=ENa.eventstream()
        GCs=ECs.eventstream()
        GAmBe=EAmBe.eventstream()
        GTAC=ETAC.eventstream()

        hNa=Histogram(ENa, ADC1+ADC2+ADC3, 'ADC1', 512, label="22Na")
        hCs=Histogram(ECs, ADC1+ADC2+ADC3, 'ADC1', 512, label="137Cs")
        hAmBe=Histogram(EAmBe, ADC1+ADC2+ADC3, 'ADC1', 512, label='AmBe')
        hTAC=Histogram(EAmBe, ADC1+ADC2+ADC3, 'ADC3', 1024, label='TAC')

        # sort data. eventually must make multistream sorter!
        SNa=Sorter(ENa, [hNa] )
        sortadc=SNa.sort()

        SCs=Sorter(ECs, [hCs] )
        sortadc=SCs.sort()

        SAmBe=Sorter(EAmBe, [hAmBe] )
        sortadc=SAmBe.sort()

        STAC=Sorter(ETAC, [hTAC] )
        sortadc=STAC.sort()

        # keep reference to histograms
        self.hNa = hNa
        self.hCs = hCs
        self.hAmBe = hAmBe
        self.hTAC = hTAC

    def calibrateTAC(self,data):
        """
        Calibrate the TAC spectrum by linear regression on the peak positions 
        in the histogram, which are determined by the TAC calibrator.
        Spacing of peaks is 20.0 ns
        input: data -- data array from histogram hTAC
        return: tacslope, tacintercept, peakpos
                slope, intercept in channel/ns,channel
                peakpos is list of peak positions in spectrum, may be used in plots
        """

        peakpos=[]
        N=len(data)
        # scan through data and get mean peak positions in a fairly crude search
        x=np.arange(N)
        i=2
        #print(N)
        while i<N-6:
            if data[i]==0 and data[i+5]==0:
                s=np.sum(data[i:i+6])
                if s>10:
                    s=np.sum(data[i:i+6]*x[i:i+6])
                    s=s/np.sum(data[i:i+6])
                    peakpos.append(s)
                    #print(i,s,data[i])
                    #print(data[i:i+6],x[i:i+6])
                    i=i+5
                else:
                    i=i+1
            else:
                i=i+1
        #print(i)

        #calculate tac calibration in channels/ns
        #print(peakpos)
        peakpos=np.array(peakpos)
        N=len(peakpos)//2
        taccalstep=20.0 #ns
        diff=0.0
        # from peakpos, avoid 'method of fools'
        for i in range(N):
            #print(peakpos[i+N]-peakpos[i])
            diff+=(peakpos[i+N]-peakpos[i])/N**2
        print('mean peak spacing in TAC spectrum=', diff)
        print('TAC calibration=',diff/taccalstep," ch/ns (for 20 ns tac calibrator)")
        # from linregress
        tacslope, tacintercept,r,p,stderr=linregress(np.arange(len(peakpos)),peakpos)
        print('TAC calibration=',tacslope/taccalstep," ch/ns (linregress)",tacintercept)
        return tacslope/taccalstep,tacintercept/taccalstep,peakpos

    def calibrateGamma(self,edges,chans):
        """
        Calibrate gamma spectra using peaks and Compton edges.
        Calibration by linear regression on positions determined by user on plots
        input: 
            edges,chans -- lists of calibration energies and positions in channels
        returns:
            slope, intercept -- channel/MeVee,channel
        """
        slope, intercept,r,p,stderr=linregress(edges,chans)
        calibration=(slope,intercept)
        self.calibration=calibration
        print("L calibration: slope,intercept",slope*2, " ch/MeV", intercept*2, " ch")
        print("Calibration corrected to full event size (1024)")
        return slope, intercept


class CalibrationPlotter(object):
    """
    Plot the calibration spectra defined by Calibrator 
    """
    def __init__(self, calibrator):
        self.calibrator=calibrator
        # copy these for convenience
        self.hNa = calibrator.hNa
        self.hCs = calibrator.hCs
        self.hAmBe = calibrator.hAmBe
        self.hTAC = calibrator.hTAC


        
    # Make 3 pairs of axes for spectra and their 1st derivatives, and one for
    # calibrations.
    def plot_calib_spectrum( self, axgroup, hist, calib, xlimits, ylimits):
        """
        Plot a calibration spectrum of hist in axes of axgroup
        axgroup: pair of axes in tuple
        hist:    histogram containing spectrum
        calib:   calibration tuple (slope, intercept); may be (None,None)
        """
        ax1,ax2=axgroup
        data,yl,xl=hist.get_plotlabels()
        slope,intercept=calib
        iscalib=slope!=None and intercept!=None
        isylimit=ylimits[0]!=None and ylimits[1]!=None
        e=np.arange(hist.size1)
        label="channel"
        if iscalib:
            e=(e-intercept)/slope
            label="Energy (MeVee)"
            xlimits=((xlimits[0]-intercept)/slope,(xlimits[1]-intercept)/slope)
        ax1.plot(e,data,drawstyle='steps-mid')
        ax1.set_ylabel(yl)
        ax1.set_xlabel(label)
        ax1.set_xlim(*xlimits)
        if isylimit: ax1.set_ylim(*ylimits)
        diffdata=np.zeros(len(data))
        diffdata[1:-1]=(data[2:]-data[0:-2])/2
        ax2.plot(e,diffdata,drawstyle='steps-mid')
        ax2.set_ylabel(yl)
        ax2.set_xlabel(label)
        ax2.set_xlim(*xlimits)
        # kludge ...
        if isylimit: ax2.set_ylim(-ylimits[1]/4,ylimits[1]/4)

    def plot_gamma_spectra( self ):
        """
        Plot the three gamma spectra
        """
        calibration=self.calibrator.calibration
        self.f1=plt.figure("Gamma calibration",(8,8))
        self.f1.canvas.draw_idle()
        ax11=plt.subplot2grid( (4,4), (0,0),colspan=2)
        ax12=plt.subplot2grid( (4,4), (1,0),colspan=2)
        self.axesgroup1=(ax11,ax12)
        self.plot_calib_spectrum( self.axesgroup1, self.hNa, calibration, (0,120), (None,None))

        ax21=plt.subplot2grid( (4,4), (0,2),colspan=2)
        ax22=plt.subplot2grid( (4,4), (1,2),colspan=2)
        self.axesgroup2=(ax21,ax22)
        self.plot_calib_spectrum( self.axesgroup2, self.hCs, calibration, (0,50), (None,None))

        ax31=plt.subplot2grid( (4,4), (2,0),colspan=2)
        ax32=plt.subplot2grid( (4,4), (3,0),colspan=2)
        self.axesgroup3=(ax31,ax32)
        self.plot_calib_spectrum( self.axesgroup3, self.hAmBe, calibration, (50,150), (0,2000))

        self.ax4 =plt.subplot2grid( (4,4), (2,2),colspan=2,rowspan=2)
        plt.xlabel('Energy [MeV]')
        plt.ylabel('Channel')
        plt.tight_layout()


        self.cid_click=self.f1.canvas.mpl_connect('button_press_event',self.pos_callback)
        self.cid_enter=self.f1.canvas.mpl_connect('axes_enter_event',self.fig_callback)


    def plot_TAC_spectra(self):
        """
        Plot TAC spectrum and calibration line
        """
        taccalstep=20.0 #ns
        f2=plt.figure("TAC calibration")
        f2.canvas.draw_idle()
        data,yl,xl=self.calibrator.hTAC.get_plotlabels()
        tacslope,tacintercept,peakpos=self.calibrator.calibrateTAC(data)
        plt.subplot(211)
        plt.plot(data,drawstyle='steps-mid')
        plt.ylabel(yl)
        plt.xlabel("Channel")
        for x in peakpos:
            plt.axvline(x,color='r',alpha=0.4)
        plt.subplot(212)
        plt.plot(np.arange(len(peakpos))*taccalstep,peakpos,'bo')
        plt.plot(np.arange(len(peakpos))*taccalstep,(np.arange(len(peakpos))*tacslope+tacintercept)*taccalstep)
        plt.xlabel("Time [ns]")
        plt.ylabel("Channel")
        plt.tight_layout()

    def plot_gamma_calibration(self, slope, intercept):
        """
        replot the gamma spectrum using a calibration
        """
        xt=np.linspace(0.0,5.0,100.0)
        self.ax4.cla()
        self.ax4.plot(edges,chans,'bo')
        self.ax4.plot(xt,intercept+xt*slope)
        self.ax4.set_xlabel("Energy (MeVee)")
        self.ax4.set_ylabel("Channel")
        self.axesgroup1[0].cla()
        self.axesgroup1[1].cla()
        calibration=(slope,intercept)
        self.plot_calib_spectrum( self.axesgroup1, self.hNa, calibration, (0,120), (None,None))
        self.axesgroup2[0].cla()
        self.axesgroup2[1].cla()
        self.plot_calib_spectrum( self.axesgroup2, self.hCs, calibration, (0,50), (None,None))
        self.axesgroup3[0].cla()
        self.axesgroup3[1].cla()
        self.plot_calib_spectrum( self.axesgroup3, self.hAmBe, calibration, (50,150), (0,2000))
        #plt.draw()
        
    def plot_all_spectra(self):
        """
        Plot all calibration spectra
        """
        self.plot_gamma_spectra()
        self.plot_TAC_spectra()
        #plt.show()

    def openPlot(self):
        self.plot_all_spectra()

       
    def insertPlot(self, tree, ploticon):
        """
        insert plot repr into list view widget
        """
        #self.plotmodel.appendRow(plot)
        tree.appendRow(ploticon)
        ploticon.setData(self)

        
    # define callbacks for matplotlib multicursor
    def pos_callback(self, event):
        """
        read position in data coords when mouse button clicked.
        put data into chan array at correct index.
        when all 4 data points, calibrate and plot line 
        """
        ax=event.inaxes
        if ax in self.axesgroup1:
            currentaxes=self.axesgroup1
            chans[0]=event.xdata
        elif ax in self.axesgroup2:
            currentaxes=self.axesgroup2
            chans[1]=event.xdata
        elif ax in self.axesgroup3:
            currentaxes=self.axesgroup3
            if chans[2]==None:
                chans[2]=event.xdata
            elif chans[3]==None:
                chans[3]=event.xdata
        else:
            return
        currentaxes[0].axvline(event.xdata)
        currentaxes[1].axvline(event.xdata)
        if chans[0] is not None and chans[1] is not None and chans[2] is not None and chans[3] is not None:
            if chans[2]>chans[3]:
                c3=chans[2]
                c2=chans[3]
                chans[2]=c2
                chans[3]=c3
            slope,intercept=self.calibrator.calibrateGamma(edges,chans)
            self.plot_gamma_calibration(slope,intercept)


        #print(event.xdata)

    def fig_callback(self, event):
        """
        Turn on multicursor when cursor is over gamma calibration axes.
        """
        global multi
        ax=event.inaxes
        if ax in self.axesgroup1:
            currentaxes=self.axesgroup1
        elif ax in self.axesgroup2:
            currentaxes=self.axesgroup2
        elif ax in self.axesgroup3:
            currentaxes=self.axesgroup3
        else:
            return
        #if multi is not None: multi.delete()
        self.multi=MultiCursor(self.f1.canvas, currentaxes, color='r', lw=1.5,
                        horizOn=False, vertOn=True, useblit=False)
