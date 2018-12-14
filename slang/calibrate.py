# for mac
import platform
import matplotlib
matplotlib.use("Qt5Agg")

from .eventlist import *

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import MultiCursor
from scipy.stats import linregress
import logging

from .analysisdata import Calibration, AnalysisData

from PyQt5 import Qt
from . import __path__ as packagepath

"""
Calibrate neutron detector using gamma ray sources.

Calibration mainly uses Compton edges, and first escape peak (12C) of AmBe source.

Energies: 
   22Na      1.062 MeV, 0.340
  137Cs      0.477 MeV
   60Co      1.118 MeV, 0.963 MeV
   12C       3.42, 4.20 MeV  (AmBe source)

Differentiating the spectrum and choosing the lowest point in the region of the 
Compton edge seems to work well enough for scintillation detectors.
See Safari et al., ArXiv 1610.09185

This code presents 3 or 4  different calibration spectra and allows the user
to select the calibration points. When all calibration points are selected, the 
calibration is calculated via linear regression, and plotted in a 5th view.

Assumes all gamma calibration histos are same len.  
"""

# calibration data
chans=[None,None,None,None]
edges=[1.062,0.477,3.42,4.20]
slope,intercept=0.0,0.0
calibration=(None,None)

edges=[]
chans=[]

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
    The calibration data is kept in a dict
    """
    
    comptonedges={'Na':(0.340,1.062),
                  'Co':(0.963,1.118),
                  'Cs':(0.477,),
                  'AmBe':(3.42, 4.20)
                   } # in MeV
    comptonchannels={'Na':[None,None],
                  'Co':[None,None],
                  'Cs':[None],
                  'AmBe':[None,None]
                   }
    
    def __init__( self, infileNa, infileCo, infileCs, infileAmBe, infileTAC):
        self.activegamma=[]
        self.infileNa = infileNa
        if infileNa is not None: self.activegamma.append('Na')
        self.infileCo = infileCo
        if infileCo is not None: self.activegamma.append('Co')
        self.infileCs = infileCs
        if infileCs is not None: self.activegamma.append('Cs')
        self.infileAmBe = infileAmBe
        if infileAmBe is not None: self.activegamma.append('AmBe')
        self.infileTAC = infileTAC
        self.hNa = None
        self.hCs = None
        self.hCo = None
        self.hAmBe = None
        self.hTAC = None
        self.calibration=Calibration()
        self.TACcalibration=(None,None)
        self.logger=logging.getLogger("neutrons")


    def sort( self ):
        """
        Define event sources and histograms, then sort data
        """
        # define event sources
        sortlist=[]
        if self.infileNa is not None:
            ENa=EventSource(self.infileNa)
            hNa=Histogram(ENa, ADC1+ADC2+ADC3, 'ADC1', 512, label="22Na")
            self.hNa = hNa
            SNa=Sorter(ENa, [hNa] )
            sortlist.append(SNa)
        if self.infileCo is not None:
            ECo=EventSource(self.infileCo)
            hCo=Histogram(ECo, ADC1+ADC2+ADC3, 'ADC1', 512, label="60Co")
            self.hCo = hCo
            SCo=Sorter(ECo, [hCo] )
            sortlist.append(SCo)
        if self.infileCs is not None:
            ECs=EventSource(self.infileCs)
            hCs=Histogram(ECs, ADC1+ADC2+ADC3, 'ADC1', 512, label="137Cs")
            self.hCs = hCs
            SCs=Sorter(ECs, [hCs] )
            sortlist.append(SCs)
        if self.infileAmBe is not None:
            EAmBe=EventSource(self.infileAmBe)
            hAmBe=Histogram(EAmBe, ADC1+ADC2+ADC3, 'ADC1', 512, label='AmBe')
            self.hAmBe = hAmBe
            SAmBe=Sorter(EAmBe, [hAmBe] )
            sortlist.append(SAmBe)
            
        ETAC=EventSource(self.infileTAC)
        hTAC=Histogram(ETAC, ADC1+ADC2+ADC3, 'ADC3', 1024, label='TAC')
        STAC=Sorter(ETAC, [hTAC] )
        self.hTAC = hTAC
        sortlist.append(STAC)

        # set calibration channels
        self.calibration.EADC='ADC1'
        self.calibration.TADC='ADC3' # could be just TDC ...

        # sort data. eventually must make multistream sorter!
        for s in sortlist:
            sortadc=s.sort()

    def calibrateTAC(self,data):
        """
        Calibrate the TAC spectrum by linear regression on the peak positions 
        in the histogram, which are determined by the TAC calibrator.
        Spacing of peaks is AnalysisData.TAC_interval in ns
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
        while i<N-6:
            if data[i]==0 and data[i+5]==0:
                s=np.sum(data[i:i+6])
                if s>10:
                    s=np.sum(data[i:i+6]*x[i:i+6])
                    s=s/np.sum(data[i:i+6])
                    peakpos.append(s)
                    i=i+5
                else:
                    i=i+1
            else:
                i=i+1
 
        #calculate tac calibration in channels/ns
        peakpos=np.array(peakpos)
        N=len(peakpos)//2
        d=AnalysisData()
        taccalstep=d.TAC_interval # was fixed 20 ns
        diff=0.0
        
        # from peakpos, avoid 'method of fools'
        for i in range(N):
            diff+=(peakpos[i+N]-peakpos[i])/N**2
        #print('mean peak spacing in TAC spectrum=', diff)
        #print('TAC calibration=',taccalstep/diff," ns/ch (for 20 ns tac calibrator)")

        # from linregress
        tacslope, tacintercept,r,p,stderr=linregress(peakpos, np.arange(len(peakpos))*taccalstep)
        #print('TAC calibration=',taccalstep/tacslope," n/chs (linregress)")
        #logger=logging.getLogger("neutrons")
        self.logger.info('mean peak spacing in TAC spectrum=%4.1f ch with calibrator setting %3.0f ns'%( diff,taccalstep))
        self.logger.info('TAC calibration=%5.3f ns/ch (%3.0f ns calibrator setting)'%(taccalstep/diff,taccalstep))
        self.logger.info('TAC calibration=%5.3f %s, %5.3f'%(tacslope," ns/ch (linregress)",tacintercept))
        self.TACcalibration=(tacslope,tacintercept) # ns/ch
        self.calibration.TAC=tacslope
        
        return tacslope,tacintercept,peakpos

    def calibrateGamma(self,edges,chans):
        """
        Calibrate gamma spectra using peaks and Compton edges.
        Calibration by linear regression on positions determined by user on plots
        input: 
            edges,chans -- lists of calibration energies and positions in channels
        returns:
            slope, intercept -- channel/MeVee,channel
        """
        slope, intercept,r,p,stderr=linregress(chans,edges)
        divisor=self.hNa.divisor1
        calibration=(slope/divisor,intercept/divisor) # convert to 1024 ch
        calgamma=calibration
        d=AnalysisData()
        gain=d.calibration_gain
        calibration=(calibration[0]*gain,calibration[1]*gain) # correct for change in gain
        self.calibration.slope=calibration[0]  #MeV/ch at 1024 ch
        self.calibration.intercept=calibration[1] # MeV
        self.logger.info("L calibration corrected for extra gain of %4.0f"%(gain,))
        self.logger.info("L calibration: slope,intercept=%6.4f %s %6.4f %s"%(calibration[0], " MeVee/ch", calibration[1], " MeVee"))
        self.logger.info("Calibration corrected to full event size (1024)")
        # return the calibration for the gamma spectra, with high gain setting
        return calgamma

    def resetGammaCalibration(self):
        self.calibration.slope=None
        self.calibration.intercept=None
        del self.calibration.slope
        del self.calibration.intercept


class CalibrationPlotter(object):
    """
    Plot the calibration spectra defined by Calibrator 
    """
    def __init__(self, calibrator):
        self.calibrator=calibrator
        # copy these for convenience
        self.hNa = calibrator.hNa
        self.hCo = calibrator.hCo
        self.hCs = calibrator.hCs
        self.hAmBe = calibrator.hAmBe
        self.hTAC = calibrator.hTAC
        self.histo={'Na':self.hNa,'Co':self.hCo, 'Cs':self.hCs,'AmBe':self.hAmBe,'TAC':self.hTAC}
        self.figures={}
        
    # Make 4 pairs of axes for spectra and their 1st derivatives, and one for
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
        diffdata=np.zeros(len(data))
        diffdata[1:-1]=(data[2:]-data[0:-2])/2
        slope,intercept=calib
        iscalib=slope!=None and intercept!=None
        isylimit=ylimits[0]!=None and ylimits[1]!=None
        e=np.arange(hist.size1)
        lo,hi,dlo,dhi=self.limit_calib_spectrum(data, diffdata)
        #print(lo,hi,dlo,dhi)
        xlimits=(lo,hi+10)
        label="channel"
        if iscalib:
            e=e*slope+intercept #(e-intercept)/slope
            label="Energy (MeVee)"
            #xlimits=((xlimits[0]-intercept)/slope,(xlimits[1]-intercept)/slope)
            xlimits=xlimits[0]*slope+intercept,(xlimits[1]*slope+intercept)
        ax1.plot(e,data,drawstyle='steps-mid')
        ax1.set_ylabel(yl)
        ax1.set_xlabel(label)
        ax1.set_xlim(*xlimits)
        if isylimit: ax1.set_ylim(*ylimits)
        ax2.plot(e,diffdata,drawstyle='steps-mid')
        ax2.set_ylabel(yl)
        ax2.set_xlabel(label)
        ax2.set_xlim(*xlimits)
        # kludge ...
        if isylimit: ax2.set_ylim(-ylimits[1]/4,ylimits[1]/4)

    def limit_calib_spectrum(self, data, diffdata ):
        """
        Set axis limits to surround region of interest 
        """
        l=len(data)
        cut=max(data[l//2:l-1])*2 # wild guess
        for i in range(l):
            if data[i]>cut: break
        lo=i
        for i in range(l-2,0,-1):  # skip last channel as may hold overload.
            if data[i]>cut:
                break
        hi=i
        dlo=np.argmin(diffdata)
        dhi=np.argmax(diffdata)
        return (lo,hi,dlo,dhi)
        

    def plot_gamma_spectra( self, tag=None, style='multi' ):
        """
        Plot the gamma spectra
        """
        if style=='single': # single page
            csp=2
            rsp=1
            page=(8,8)
            top1=[(0,0),(0,2),(2,0),(2,2)]
            top2=[(1,0),(1,2),(3,0),(3,2)]
        elif style=='multi':
            page=(4,4)
            csp=4
            rsp=2
            top1=[(0,0),(0,0),(0,0),(0,0)]
            top2=[(2,0),(2,0),(2,0),(2,0)]
        else:
            raise ValueError
        #cal=self.calibrator.calibration
        cal=Calibration()
        d=AnalysisData()
        gain=d.calibration_gain
        calibrated=False
        if 'slope' in cal.keys() and 'intercept' in cal.keys():
            divisor=self.hNa.divisor1
            calibration=(cal.slope/gain*divisor,cal.intercept/gain*divisor)
            slope,intercept=calibration
            calibrated=True
        else:
            calibration=(None,None)
        #self.f1=plt.figure("Gamma calibration",(8,8), constrained_layout=True)
        if style=='single':    
            fign=plt.figure("Gamma spectra",page)
            plt.tight_layout()
        active=self.calibrator.activegamma
        for source in active:
            if style=='multi':
                fign=plt.figure(source,page)
            f1=fign
            # plots are interactive - redraw on idle
            f1.canvas.draw_idle()
            # 2 plots per source -- show derivative as well for edge selection
            ax11=plt.subplot2grid( (4,4), top1[0],colspan=csp,rowspan=rsp)
            ax12=plt.subplot2grid( (4,4), top2[0],colspan=csp,rowspan=rsp)
            axesgroup=(ax11,ax12)
            # what we plot
            h=self.histo[source]
            # plot spectrum
            self.plot_calib_spectrum( axesgroup, h, calibration, (0,120), (None,None))
            # save info indict
            self.figures[source]={}
            self.figures[source]['figure']=f1
            self.figures[source]['axes']=axesgroup
            self.figures[source]['histo']=h
            # set callbacks for mouse actions
            self.figures[source]['click']=f1.canvas.mpl_connect('button_press_event',
                                                  self.pos_callback)
            self.figures[source]['enter']=f1.canvas.mpl_connect('axes_enter_event',
                                                  self.fig_callback)
            plt.tight_layout()
            
        # separate plot for the actual calibration
        self.f5=plt.figure("Gamma calibration",(4,4))
        self.f5.canvas.draw_idle()
        # add our stuff to the toolbar
        tb=self.f5.canvas.manager.toolbar
        tb.addSeparator()
        a=tb.addAction(Qt.QIcon(packagepath[0]+"/images/select_ok.png"), "ok", self._calib_ok)
        a.setToolTip("Accept calibration")
        a=tb.addAction(Qt.QIcon(packagepath[0]+"/images/reject.png"), "cancel", self._calib_retry)
        a.setToolTip("Undo calibration")
        self.ax5 =plt.subplot2grid( (4,4), (0,0),colspan=4,rowspan=4)
        if calibrated:
            chmax=max(chans)
            xt=np.linspace(0.0,chmax*1.1,100.0)
            self.ax5.plot(chans,edges,'bo')
            self.ax5.plot(xt,intercept+xt*slope)       
        plt.xlabel('Energy [MeV]')
        plt.ylabel('Channel')
        plt.tight_layout()

    def _calib_ok(self):
        """
        When enough calibration points have been added click on "ok" on plot window
        to send message to here.
        Perform the calibration in this callback.
        """
        global edges, chans
        cal=self.calibrator.activegamma
        totlen=0
        totnone=0
        edges=[]
        chans=[]
        for source in cal:
            v=self.calibrator.comptonchannels[source]
            e=self.calibrator.comptonedges[source]
            l=len(v)
            totlen+=l
            for i in range(l):
                if v[i]!=None:
                    chans.append(v[i])
                    edges.append(e[i])
            #print(chans,edges)
        if len(edges)>3:
            slope,intercept=self.calibrator.calibrateGamma(edges,chans)
            self.plot_gamma_calibration(slope,intercept)
    
    def _calib_retry(self):
        """
        Cancel calibration event comes here.
        Reset the calibration to None and permit adding more points
        """
        self.calibrator.resetGammaCalibration()
        self.plot_gamma_calibration(None,None)

    def plot_TAC_spectra(self):
        """
        Plot TAC spectrum and calibration line
        """
        d=AnalysisData()
        taccalstep=d.TAC_interval #ns
        #f2=plt.figure("TAC calibration", constrained_layout=True)
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
        plt.plot(peakpos,np.arange(len(peakpos))*taccalstep,'bo')
        #plt.plot(np.arange(len(peakpos))*taccalstep,
        #         (np.arange(len(peakpos))*tacslope+tacintercept)*taccalstep)
        plt.plot(np.arange(1000.0),
                 np.arange(1000.0)*tacslope+tacintercept)
        plt.ylabel("Time [ns]")
        plt.xlabel("Channel")
        plt.tight_layout()

    def plot_gamma_calibration(self, slope, intercept):
        """
        replot the gamma spectrum using a calibration
        """
        self.ax5.cla()
        active=self.calibrator.activegamma
        calibration_done=slope is not None and intercept is not None
        self.ax5.plot(chans,edges,'bo')
        chmax=int(max(chans)*1.1)
        xt=np.linspace(0.0,chmax,100.0)
        if calibration_done:
            # all sources sorted into same length histo, so pick first...
            divisor=self.figures[active[0]]['histo'].divisor1
            slope=slope*divisor
            intercept=intercept*divisor
            self.ax5.plot(xt,intercept+xt*slope)
        else:
            temp_slope, temp_intercept,r,p,stderr=linregress(chans,edges)
            self.ax5.plot(xt,temp_intercept+xt*temp_slope,alpha=0.5)           
        self.ax5.set_ylabel("Energy (MeVee)")
        self.ax5.set_xlabel("Channel")
        if calibration_done:
            calibration=(slope,intercept)
            for source in active:
                axesgroup=self.figures[source]['axes']
                h=self.figures[source]['histo']
                axesgroup[0].cla()
                axesgroup[1].cla()
                self.plot_calib_spectrum( axesgroup, h,
                                      calibration, (0,120), (None,None))
        
    def plot_all_spectra(self):
        """
        Plot all calibration spectra
        """
        self.plot_gamma_spectra()
        self.plot_TAC_spectra()

    def openPlot(self):
        self.plot_all_spectra()

       
    def insertPlot(self, tree, ploticon):
        """
        insert plot repr into list view widget
        """
        tree.appendRow(ploticon)
        ploticon.setData(self)

    def pos_callback(self, event):
        """
        To read position of multicursor when mouse button clicked.
        Read position in data coords when mouse button clicked.
        This also has to handle adjustment of calibration when calibrated.
        Gets tricky for AmBe.
        """
        #global chans, edges
        #print('Enter pos_callback')
        #tb=self.f1.canvas.manager.toolbar
        tb=event.canvas.manager.toolbar
        if tb._active is not None and ('PAN' in tb._active or 'ZOOM' in tb._active):
            return
        # different approach if using toolmanager
        #tm=self.f1.canvas.manager.toolmanager
        #if 'pan' in tm.active_toggle['default']:
        #    return
        ax=event.inaxes
        xdata=event.xdata
        cal=Calibration()
        if 'slope' in cal.keys() and 'intercept' in cal.keys():
            # calibrated, xdata is in MeV: convert to channels
            xdata=cal.channel(xdata) # convert to channel
            divisor=self.hNa.divisor1
            d=AnalysisData()
            gain=d.calibration_gain
            xdata=xdata*gain/divisor
         
        ag=self.calibrator.activegamma
        if 'Na' in ag and ax in self.figures['Na']['axes']:
            currentfig=self.figures['Na']
            currentaxes=self.figures['Na']['axes']
            #chans[0]=xdata
            comptonedge=self.calibrator.comptonedges['Na']
            source='Na'
        elif 'Co' in ag and ax in self.figures['Co']['axes']:
            currentfig=self.figures['Co']
            currentaxes=self.figures['Co']['axes']
            #chans[1]=xdata
            comptonedge=self.calibrator.comptonedges['Co']
            source='Co'
        elif 'Cs' in ag and ax in self.figures['Cs']['axes']:
            currentfig=self.figures['Cs']
            currentaxes=self.figures['Cs']['axes']
            #chans[1]=xdata
            comptonedge=self.calibrator.comptonedges['Cs']
            source='Cs'
        elif 'AmBe' in ag and ax in self.figures['AmBe']['axes']:
            currentfig=self.figures['AmBe']
            currentaxes=self.figures['AmBe']['axes']
            comptonedge=self.calibrator.comptonedges['AmBe']
            source='AmBe'
        else:
            return
        
        currentaxes[0].axvline(event.xdata)
        x=event.xdata
        currentaxes[1].axvline(event.xdata)
        if len(comptonedge)==1:
            self.calibrator.comptonchannels[source][0]=xdata
            self.check_for_calibration_plot()
        else:    
            self._annotate_selection(x, currentaxes, comptonedge,currentfig)

    def check_for_calibration_plot(self):
        global edges, chans
        active=self.calibrator.activegamma
        edges=[]
        chans=[]
        for source in active:
            v=self.calibrator.comptonchannels[source]
            e=self.calibrator.comptonedges[source]
            l=len(v)
            for i,vi in enumerate(v):
                if vi!=None:
                    chans.append(vi)
                    edges.append(e[i])
        if len(edges)>=3:
            self.plot_gamma_calibration(None,None)
        
    def _annotate_selection(self, x, currentaxes, comptonedge, currentfig):
        if len(comptonedge)==1: return
        ylims=currentaxes[0].get_ylim()
        dely=(ylims[1]-ylims[0])*0.12
        y=ylims[1]-dely
        # annotate with both energies, highest on top
        edgestr="%.3f MeV"%(comptonedge[1])
        ann1=currentaxes[0].annotate(edgestr,
                                xy=(x,y-dely), xycoords='data',
                                xytext=(x+10,y), textcoords='data',
                                bbox=dict(boxstyle="round", fc="w"),
                                arrowprops=dict(arrowstyle="->",
                                                connectionstyle="angle,angleA=-90,angleB=180"),
                                picker=True)
        edgestr="%.3f MeV"%(comptonedge[0])
        ann2=currentaxes[0].annotate(edgestr,
                                xy=(x,y-4.0*dely), xycoords='data',
                                xytext=(x+10,y-3.0*dely), textcoords='data',
                                bbox=dict(boxstyle="round", fc="w"),
                                arrowprops=dict(arrowstyle="->",
                                                connectionstyle="angle,angleA=-90,angleB=180"),picker=True)
        currentfig['figure'].canvas.mpl_disconnect(currentfig['click'])
        self.cidp=currentfig['figure'].canvas.mpl_connect('pick_event',self.pick_callback)
        #print(ann1,ann2)
        currentfig['pickchoices']=(ann1,ann2)
        
    def pick_callback(self, event):
        """
        Callback for pick of calibration energy choice.
        """
        mevent=event.mouseevent
        artist=event.artist
        canvas=event.canvas
        inaxes=event.mouseevent.inaxes
        cal=self.calibrator.activegamma
        for source in cal:
            axes=self.figures[source]['axes']
        
            if inaxes in axes:
                if artist in self.figures[source]['pickchoices']:
                    #print("In pickchoices")
                    p1,p2=self.figures[source]['pickchoices']
                    if artist == p1:
                        t=p1.get_text().split(' ')
                        self.calibrator.comptonchannels[source][1]=p1.xy[0]
                        #print('selection',t)
                    elif artist == p2:
                        t=p2.get_text().split(' ')
                        self.calibrator.comptonchannels[source][0]=p1.xy[0]
                        #print('selection',t)
                    self.check_for_calibration_plot()
                    p1.set_visible(False)
                    p2.set_visible(False)
                    self.figures[source]['pickchoices']=(None,None)
                    
                currentaxes=axes
                currentfig=self.figures[source]
            
                currentfig['figure'].canvas.mpl_disconnect(self.cidp)
                self.figures[source]['click']=currentfig['figure'].canvas.mpl_connect('button_press_event', self.pos_callback)
        
        return True
        
        
    def fig_callback(self, event):
        """
        Turn on multicursor when cursor is over gamma calibration axes.
        """
        global multi
        ax=event.inaxes
        cal=self.calibrator.activegamma
        
        #if self.selecting: return
        
        for source in cal:
            axes=self.figures[source]['axes']
            if ax in axes:
                currentaxes=axes
                currentfigure=self.figures[source]['figure']
                
        self.multi=MultiCursor(currentfigure.canvas, currentaxes, color='r', lw=1.5,
                               horizOn=False, vertOn=True, useblit=False)
