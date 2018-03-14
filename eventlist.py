import numpy as np
import io
import configparser
from enum import IntEnum
import time

class EventFlags(IntEnum):
    """
    Define constants for use by module
    """
    # list stream identifers
    TIMER=64
    PAD=128
    RTC=16
    # marker between timer events and adc events
    SYNCHRON=0xff

    # our identifier for adc events
    ADCEVENT=1

    # adc bitmap
    ADC1=1
    ADC2=2
    ADC3=4
    ADC4=8

# adc names for use in histogramming
adcnames=('ADC1','ADC2','ADC3','ADC4')

# for efficiency keep flags as globals
"""
TIMER   =EventFlags.TIMER
PAD     =EventFlags.PAD
RTC     =EventFlags.RTC
SYNCHRON=EventFlags.SYNCHRON
ADCEVENT=EventFlags.ADCEVENT
ADC1=EventFlags.ADC1
ADC2=EventFlags.ADC2
ADC3=EventFlags.ADC3
ADC4=EventFlags.ADC4
"""
# list stream identifers
TIMER=64
PAD=128
RTC=16
# marker between timer events and adc events
SYNCHRON=0xff

# our identifier for adc events
ADCEVENT=1

# adc bitmap
ADC1=1
ADC2=2
ADC3=4
ADC4=8

# number of adcs
TOTALADCS=4

# powers of two, for convenience
# unlikely adc is set to many of these, but ...
powers_of_two=[2,4,8,16,32,64,128,256,512,1024,2048,4096,8192]


class EventSource(object):
    """
    a class to encapsulate neutron daq .lst files

    The list data format is described in Fast-Comtex manual for MPA3, sect. 7.6.3.

    The .lst file is a binary file with a first section consisting of a variable 
    length header in Windows INI format, with \r\n (CRLF) as line seperators.
    The header is terminated with the section marker [LISTDAT]\r\n.
    The format is non-standard in that it does not start with a section marker.
    One is added -- [settings]. Name may change once we know what the data are.
    The data after this marker is in little-endian words which we will take as 4 
    bytes, b0,b1,b2,b3.
    Byte b3 is a bitmap which identifies the word, by bit set:
        RTC      16   real time clock (from Maciej, none spotted)
        TIMER    64   timer input, every 1 ms (unless timereduce set in header).
                      Bits in b0 indicate if ADC is active. Use for dead time calc.
        PAD     128   ADC event is zero, but this bit may be set if adc data word 
                      is padded 
        SYNCHRON MARKER 0xffffffff   all bits set -- seperate timer from adc data.

    Adcs triggered are indicated in b0: adc1 as bit0 ( value 1), adc2 as bit1 (2)
         adc3 as bit2 (4), adc4 as bit3 (8).
    Data follows in subsequent 4-byte words, with 2 bytes per data word.
    Data words are packed into 4-byte words from low bits, in sequence of adcs.
    Only data from adcs that triggered are packed.
    If there are an odd number of adcs, the first data word is padded with 0xff
    i.e., the two words for 3 adcs (say, adc1,adc2,adc4) are:
            [  0xff     | 0xff     |  adc1(lo) | adc1(hi)  ]
            [  adc2(lo) | adc2(hi) |  adc4(lo) | adc4(hi)  ]
    If the word is padded, bit value 128 of b3 is set.
    Occasionally there seem to be 4 zero bytes following an adc event.
    This is not documented and may be some sort of bug.
    Presently they are ignored.

    Parameters
    ----------
    infile : Path 
        Full path to list file to be sorted.
    
    """
    
    def __init__( self, infile ):
        """
        initialise class instance
        infile: path to lst file
        """
        f=open(infile,"rb",buffering=81920)
        self.filename=infile
        self.f=f
        # read header into list
        l=[]        
        for b in f:
            l.append(b)
            s=b.decode()
            if "[LISTDATA]" in s: # marker for start of data (end of header)
                break
        self.header=l
        # we can decode header using configparser from standard python library
        C=configparser.ConfigParser(strict=False)
        # the data comes out the binary mode file as byte array per line  -- add
        # a header, convert bytes to list, then back to single byte array,
        # which can then be decoded to a string for configparser.
        # Must be an easier way...
        # Should merge into code above -- 'read header into list'
        s=list(b'[settings]')
        for b in self.header: s.extend(list(b))
        ba=bytearray(s)
        self.configdatastring=ba.decode()
        C.read_string(ba.decode())
        self.configdata=C
        adcranges=[0,0,0,0]
        adcmasks=[0,0,0,0]
        for i in range(len(adcnames)):
            adcrange=C.getint(adcnames[i],'range')
            if adcrange not in powers_of_two:
                raise ValueError('ADC range is not a power of two')
            adcranges[i]=adcrange
            adcmasks[i]=adcrange-1
        self.adcranges=adcranges
        self.adcmasks=adcmasks

    def eventstream(self):
        """
        generator for event stream

        This returns an iterator for the event stream.
        The user must decode the event types and process accordingly.

        The iterator returns a tuple of 4 values.
        The first is an event type.
        The others are only significant for adc data.
        returned for adc data:
           (ADCEVENT, no. of adcs triggered, 
            list of 4 booleans of adc status, list of 4 adc values)
        Only adcs with True status should be read out.
        """
        f=self.f
        nunknown0=0
        while 1:
            b=f.read(4) # read 4 byte word
            if b==b'\x00\x00\x00\x00':
                #print("offset",f.tell())
                nunknown0+=1
                continue
            if len(b)<4:
                print("nunknown0",nunknown0)
                print('stop',b)
                return
            # event type is in b[3]
            etype=b[3]
            b0=b[0]
            if etype == TIMER:
                yield TIMER,b0,0,0
            elif etype == SYNCHRON:
#                if b[0]!=0xff and b[1]!=0xff and b[2]!=0xff:
#                if etype & b[0] & b[1] & b[2]!=SYNCHRON:
                if b != b'\xff\xff\xff\xff':
                    print("Hmm. Markers are more complicated")
                yield SYNCHRON,0,0,0
            elif (etype & RTC) != 0:
                yield RTC,0,0,0
            else:
                padded=etype&PAD != 0
                #if b[0]==0:
                #    print(b,v)
                #    #b=f.read(16)
                #    print(b,oldb)
                #    continue
                n,a,v=self.__getevent(b0, padded)
                yield ADCEVENT,n,b0,v

    def __getevent(self, adcs, padded):
        """
        read an adc event from stream and decode 
        data words are padded if odd number of adcs fired 
        """
        f=self.f
        # (basically from maciej)
        # Check bits to see which adcs fired.
        # Normalize so only lowest bit set
        # Keep results in isadc[].
        adc1=adcs&ADC1
        adc2=(adcs&ADC2)//ADC2
        adc3=(adcs&ADC3)//ADC3
        adc4=(adcs&ADC4)//ADC4
        isadc=[adc1,adc2,adc3,adc4]
        Nadcs=adc1+adc2+adc3+adc4
        # unpack values. If adc did not fire, return zero.
        if padded:
            b=f.read(2)
            if b!= b'\xff\xff':
                print("Pad error")
        values=[0,0,0,0]
        for i in range(TOTALADCS):
            if isadc[i]==1:
                b=f.read(2)
                # assemble ADC word
                ints=256*int(b[1])+int(b[0])
                # mask adc word to adcrange
                ints=ints&self.adcmasks[i]
                values[i]=ints
        return Nadcs,isadc,values

    def get_header(self):
        return self.header

    def get_configuration(self):
        """
        returns a ConfigParser object representing the header data
        """
        return self.configdata
    

class Histogram(object):
    """
    Create a 1-d or 2-d histogram

    Parameters
    ----------
        stream:    EventStream object providing data -- needed for header info
                   which gives ADC settings
        group:     coincidence group of adcs: bitmap value indicating which
                   adcs were read out in coincidence
        adctuple:  tuple of strings giving adcs to use, named according to DAQ
                   e.g. ('ADC1','ADC2') for 2-d or ('ADC1',) for 1-d
                   For 1-d, a str is acceptable, e.g. 'ADC1'
                   For 2-d, tuples are in (x,y) format assuming standard
                   matplotlib.imshow() orientation, 
                   i.e. numpy array is data[y,x] 
        sizetuple: Size of histo axis -- should be int power of two
                   Simililar protocol to adctuple
        label:     Tag to identify axes for use in plotting

    Returns
    -------
        data:      reference to data array (numpy)
        yl,xl:     adc names from histogram creation (for plot labels)
    """
    def __init__(self, stream, group, adctuple, sizetuple, label=None):
        self.coincidencegroup=group
        self.label=label
        if label is None:
            labeltuple=adctuple
        else:
            labeltuple=label
        if isinstance(adctuple,str):  # assume it's a 1-d
            if self.label==None: self.label=adctuple
            adctuple=(adctuple,)
            # now sizetuple, labeltuple should be an int
            sizetuple=(sizetuple,)
            labeltuple=(labeltuple,)
        if len(adctuple) != len(sizetuple):
            raise ValueError("adc/size mismatch")
        if len(adctuple) != len(labeltuple):
            raise ValueError("adc/label mismatch")
        if len(adctuple)>2:
            raise ValueError("More that 2 adcs")
        self.S=stream
        C=stream.get_configuration()
        if len(adctuple)==1:
            self.dims=1
            self.adc1=adctuple[0]
            self.size1=sizetuple[0]
            self.label1=labeltuple[0]
            self.adcrange1=C.getint(adctuple[0],'range')
            self.divisor1 = self.adcrange1//sizetuple[0]
            self.index1=int(adctuple[0][3])-1
            self.data=np.zeros(sizetuple[0])
        elif len(adctuple)==2:
            if self.label is None: self.label=labeltuple[0]+"v"+labeltuple[1]
            self.dims=2
            self.adc1=adctuple[0]
            self.adc2=adctuple[1]
            self.size1=sizetuple[0]
            self.size2=sizetuple[1]
            self.label1=labeltuple[0]
            self.label2=labeltuple[1]
            self.adcrange1=C.getint(adctuple[0],'range')
            self.adcrange2=C.getint(adctuple[1],'range')
            self.divisor1 = self.adcrange1//sizetuple[0]
            self.divisor2 = self.adcrange2//sizetuple[1]
            self.index1=int(adctuple[0][3])-1
            self.index2=int(adctuple[1][3])-1
            self.data=np.zeros(sizetuple)
        else:
            raise ValueError("Number of ADCs must be 1 or 2")

    def increment(self,v):
        if self.dims==1:
            self.data[v[self.index1]//self.divisor1]+=1.0
        elif self.dims==2:
            i1=self.index1
            i2=self.index2
            d1=self.divisor1
            d2=self.divisor2
            self.data[v[i2]//d2,v[i1]//d1]+=1.0

    def increment1(self,v):
        if self.dims==1:
            self.data[v//self.divisor1]+=1.0
        elif self.dims==2:
            # Error
            pass
        
    def increment2(self,v1,v2):
        if self.dims==1:
            # Error
            pass
        elif self.dims==2:
            d1=self.divisor1
            d2=self.divisor2
            self.data[v2//d2,v1//d1]+=1.0

    def get_plotdata(self):
        if self.dims==1:
            return self.data, self.adc1, 'x'
        else:
            return self.data, self.adc1, self.adc2

    def get_plotlabels(self):
        if self.dims==1:
            return self.data, self.label1, 'x'
        else:
            return self.data, self.label1, self.label2

class Sorter(object):
    """
    Sort an eventstream into histograms
    Input:
        stream:     EventStream instance.
        histlist:   List of histograms to sort into.
        gatelist:   List of gates to apply to events (IGNORED FOR NOW).
    """
    def __init__( self, stream, histlist, gatelist=None ):
        self.stream = stream
        self.histlist = histlist
        self.gatelist = gatelist
        self._groups=[]
        self._hists=[]
        self.moresort=None
        for h in histlist:
            if h.coincidencegroup in self._groups:
                i=self._groups.index(h.coincidencegroup)
                self._hists[i].append(h)
            else:
                self._groups.append(int(h.coincidencegroup))
                self._hists.append([h])

    def sort(self):
        """
        start sorting event stream.
        eventually will run in background.
        """
        eventstream=self.stream.eventstream()
        #histlist=self.histlist
        # collect stats
        ntimer=0
        nrtc=0
        nmark=0
        nevent=0
        nunknown1=0
        nunknown2=0
        nadc=[0,0,0,0]
        sortadc=[]
        t0=time.perf_counter()
        for t,n,a,v in eventstream:
            #print(t,n,a,v)
            if t == TIMER:
                ntimer+=1
            elif t == RTC:
                nrtc+=1
            elif t == SYNCHRON:
                nmark+=1
            elif t == ADCEVENT:
                nevent+=1
                nadc[n-1]+=1
                # bitmap of event
                bitmap=a#[0]+a[1]*2+a[2]*4+a[3]*8
                if bitmap > 0:
                    sortadc.append(bitmap)
                    if bitmap in self._groups:
                        i=self._groups.index(bitmap)
                        histlist=self._hists[i]
                        for h in histlist:
                            h.increment(v)
                    if self.moresort is not None: self.moresort(a,v)
                else:
                    nunknown1+=1
            else:
                nunknown2+=1
                print("huh?")

        t1=time.perf_counter()
        print("Sort: elapsed time ",t1-t0, " s")
        print("Timer",ntimer)
        print("Events",nevent)
        print("RTC",nrtc)
        print("Marks",nmark)
        print("Nadc",nadc,nadc[0]+nadc[1]+nadc[2]+nadc[3])
        print("unknown1",nunknown1)
        print("unknown2",nunknown2)
        return sortadc

    def setExtraSorter( self, sorter):
        self.moresort=sorter
        
        

if __name__ == "__main__":

    # for mac
    import platform
    if platform.system()=="Darwin":
        import matplotlib
        matplotlib.use("Qt5Agg")


    import numpy as np
    import matplotlib.pyplot as plt
    import time
   
    infile="../IRMM FC 100 MeV data/FC_035.lst"
    infile="../NE213 100 MeV data/NE213_010_100MeV_0deg.lst"
    #infile="../NE213 100 MeV data/NE213_019_137Cs.lst"
    #infile="../NE213 100 MeV data/NE213_017_22Na.lst"

    E=EventSource(infile)
    G=E.eventstream()

    h1=Histogram(E, ADC1+ADC2+ADC3, 'ADC1', 512)
    h2=Histogram(E, ADC1+ADC2+ADC3, 'ADC2', 512)
    h3=Histogram(E, ADC1+ADC2+ADC3, 'ADC3', 512)
    h4=Histogram(E, ADC4, 'ADC4', 512)
    print(len(h2.data), h2.adc1,h2.divisor1, h2.adcrange1, h2.index1, h2.size1)
    h21=Histogram(E, ADC1+ADC2+ADC3, ('ADC1','ADC2'), (256,256),label=('L','S'))
    print(np.shape(h21.data), h21.adc1,h21.divisor1, h21.adcrange1, h21.index1, h21.size1)
    print(np.shape(h21.data), h21.adc2,h21.divisor2, h21.adcrange2, h21.index2, h21.size2)
    histlist=[h1,h2,h3,h4,h21]
    S=Sorter( E, histlist)
    sortadc=[]
    deadtimer=[]
    t0=time.perf_counter()
    # this section 100 s (macmini)
    # a few optimisations, now 96 s (macmini)
    sortadc=S.sort()
    """
    # this section 103s (macmini)
    ntimer=0
    nrtc=0
    nmark=0
    nevent=0
    nadc=[0,0,0,0]
    nunknown=0
    for t,n,a,v in G:
        if t == TIMER:
            ntimer+=1
        elif t == RTC:
            nrtc+=1
            if n>0:
                deadtimer.append(n)
        elif t == SYNCHRON:
            nmark+=1
        elif t == ADCEVENT:
            nevent+=1
            nadc[n-1]+=1
            if n==3 and v[0]<1024:
                h1.increment(v)
                h2.increment(v)
                h3.increment(v)
                h21.increment(v)
            if n==1:
                h4.increment(v)
            else:
                nunknown+=1
            b=a#[0]+a[1]*2+a[2]*4+a[3]*8
            sortadc.append(b)
        else:
            print("huh?")
                  
    print("Timer",ntimer)
    print("Events",nevent)
    print("RTC",nrtc)
    print("Marks",nmark)
    print("Nadc",nadc,nadc[0]+nadc[1]+nadc[2]+nadc[3])
    print("unknown",nunknown)
    """
    t1=time.perf_counter()
    print("Elapsed time:", t1-t0, " s")

    plt.figure(1)
    data,yl,xl=h21.get_plotlabels()
    plt.imshow(data,origin='lower',vmax=2000)
    plt.xlabel(yl)
    plt.ylabel(xl)
    plt.figure(2)
    data,yl,xl=h2.get_plotdata()
    plt.plot(data,drawstyle='steps-mid')
    plt.ylabel(yl)
    plt.figure(3)
    plt.hist(sortadc,bins=16,range=(0,15))
    plt.xlim(0,16)
    plt.ylabel('Adc distribution')
    plt.figure(4)
    data,yl,xl=h4.get_plotdata()
    plt.plot(data,drawstyle='steps-mid')
    plt.ylabel(yl)
    plt.figure(5)
    data,yl,xl=h3.get_plotdata()
    plt.plot(data,drawstyle='steps-mid')
    plt.ylabel(yl)
    plt.figure(6)
    data,yl,xl=h1.get_plotdata()
    plt.plot(data,drawstyle='steps-mid')
    plt.ylabel(yl)
    plt.show()
