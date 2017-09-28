import numpy as np
import io
import matplotlib.pyplot as plt
import configparser
from enum import Enum

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



class EventStream(object):
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
        
    """
    
    def __init__( self, infile ):
        """
        initialise class instance
        infile: path to lst file
        """
        f=open(infile,"rb")
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

    def eventgen(self):
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
        while 1:
            b=f.read(4) # read 4 byte word
            if len(b)<4:
                print('stop',b)
                return
            # event type is in b[3]
            etype=b[3]
            if etype == TIMER:
                yield TIMER,0,0,0
            elif etype == SYNCHRON:
#                if b[0]!=0xff and b[1]!=0xff and b[2]!=0xff:
                if etype & b[0] & b[1] & b[2]!=SYNCHRON:
                    print("Hmm. Markers are more complicated")
                yield SYNCHRON,0,0,0
            elif (etype & RTC) != 0:
                yield RTC,0,0,0
            else:
                padded=etype&PAD != 0
                n,a,v=self.__getevent(b[0], padded)
                yield ADCEVENT,n,a,v
 
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
        isadc=[]
        adc1=adcs&ADC1
        isadc.append(adc1)
        adc2=(adcs&ADC2)//ADC2
        isadc.append(adc2)
        adc3=(adcs&ADC3)//ADC3
        isadc.append(adc3)
        adc4=(adcs&ADC4)//ADC4
        isadc.append(adc4)
        Nadcs=adc1+adc2+adc3+adc4
        # unpack values. If adc did not fire, return zero.
        values=[]
        if padded:
            b=f.read(2)
            if b[0]!= 0xff or b[1]!=0xff:
                print("Pad error")
        for i in range(4):
            if isadc[i]==1:
                b=f.read(2)
                ints=256*int(b[1])+int(b[0])
                values.append(ints)
            else:
                values.append(0)
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

    Input:
        group:     coincidence group of adcs: bitmap value indicating which
                   adcs were read out in coincidence
        adctuple:  tuple of strings giving adcs to use, named according to DAQ
                   e.g. ('ADC1','ADC2') for 2-d or ('ADC1',) for 1-d
                   For 1-d, a str is acceptable, e.g. 'ADC1'
        sizetuple: Size of histo axis -- should be int power of two
                   Simililar protocol to adctuple
        stream:    EventStream object providing data -- needed for header info
                   which gives ADC settings
    Returns:
        data:      reference to data array (numpy)
        yl,xl:     adc names from histogram creation (for plot labels)
    """
    def __init__(self, group, adctuple, sizetuple, stream, label=None):
        self.coincidencegroup=group
        if isinstance(adctuple,str):  # assume it's a 1-d
            adctuple=(adctuple,)
            # now sizetuple should be an int
            sizetuple=(sizetuple,)
        if len(adctuple) != len(sizetuple):
            raise ValueError( "adc/size mismatch")
        if len(adctuple)>2:
            raise ValueError("More that 2 adcs")
        self.S=stream
        C=S.get_configuration()
        if len(adctuple)==1:
            self.dims=1
            self.adc1=adctuple[0]
            self.size1=sizetuple[0]
            self.adcrange1=C.getint(adctuple[0],'range')
            self.divider1 = self.adcrange1//sizetuple[0]
            self.index1=int(adctuple[0][3])-1
            self.data=np.zeros(sizetuple[0])
        elif len(adctuple)==2:
            self.dims=2
            self.adc1=adctuple[0]
            self.adc2=adctuple[1]
            self.size1=sizetuple[0]
            self.size2=sizetuple[1]
            self.adcrange1=C.getint(adctuple[0],'range')
            self.adcrange2=C.getint(adctuple[1],'range')
            self.divider1 = self.adcrange1//sizetuple[0]
            self.divider2 = self.adcrange2//sizetuple[1]
            self.index1=int(adctuple[0][3])-1
            self.index2=int(adctuple[1][3])-1
            self.data=np.zeros(sizetuple)
        else:
            raise ValueError("Number of ADCs not in range")

    def increment(self,v):
        if self.dims==1:
            self.data[v[self.index1]//self.divider1]+=1.0
        elif self.dims==2:
            i1=self.index1
            i2=self.index2
            d1=self.divider1
            d2=self.divider2
            self.data[v[i1]//d1,v[i2]//d2]+=1.0

    def get_plotdata(self):
        if self.dims==1:
            return self.data, self.adc1, 'x'
        else:
            return self.data, self.adc2, self.adc1


class Sorter(object):
    """
    Sort an eventstream into histograms
    Input:
        stream:     EventStream instance.
        histlist:   List of histograms to sort into.
        gatelist:   List of gates to apply to events (IGNORED FOR NOW).
    """
    def __init__( self, stream, histlist ):
        self.stream = stream
        self.eventgenerator = stream.eventgen()
        self.histlist = histlist
        self.gatelist = gatelist

    def sort(self):
        """
        start sorting event stream.
        eventually will run in background.
        """
        eventstream=self.eventstream
        histlist=self.histlist
        # collect stats
        ntimer=0
        nrtc=0
        nmark=0
        nevent=0
        nunknown=0
        nadc=[0,0,0,0]
        sortadc=[]
        for t,n,a,v in eventstream:
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
                bitmap=a[0]+a[1]*2+a[2]*4+a[3]*8
                sortadc.append(bitmap)
                for h in histlist:
                    if h.concidencegroup==bitmap:
                        h.increment(v)               
            else:
                nunknown+=1
                print("huh?")

        #print("Timer",T)
        #print("Events",nevent)
        #print("RTC",nrtc)
        #print("Marks",nmark)
        #print("Nadc",nadc)

        
        

if __name__ == "__main__":
   
    infile="../NE213 100 MeV data/NE213_017_22Na.lst"
    infile="../IRMM FC 100 MeV data/FC_035.lst"
    infile="../NE213 100 MeV data/NE213_010_100MeV_0deg.lst"

    S=EventStream(infile)
    G=S.eventgen()

#    h2=Histogram(('ADC2',),(512,),S)
    h2=Histogram(ADC1+ADC2+ADC3,'ADC2',512,S)
    h3=Histogram(ADC1+ADC2+ADC3,'ADC3',512,S)
    h4=Histogram(ADC4,'ADC4',512,S)
    print(len(h2.data), h2.adc1,h2.divider1, h2.adcrange1, h2.index1, h2.size1)
    h21=Histogram(ADC1+ADC2+ADC3,('ADC2','ADC1'),(256,256),S)
    print(np.shape(h21.data), h21.adc1,h21.divider1, h21.adcrange1, h21.index1, h21.size1)
    print(np.shape(h21.data), h21.adc2,h21.divider2, h21.adcrange2, h21.index2, h21.size2)
    
    T=0
    nrtc=0
    nmark=0
    nevent=0
    nadc=[0,0,0,0]
    sortadc=[]
    for t,n,a,v in G:
        if t == TIMER:
            T+=1
        elif t == RTC:
            nrtc+=1
        elif t == SYNCHRON:
            nmark+=1
        elif t == ADCEVENT:
            nevent+=1
            nadc[n-1]+=1
            if n==3:# and v[0]>56:
                h2.increment(v)
                h3.increment(v)
                h21.increment(v)
            if n==1:
                h4.increment(v)
            b=a[0]+a[1]*2+a[2]*4+a[3]*8
            sortadc.append(b)
        else:
            print("huh?")
                   
    print("Timer",T)
    print("Events",nevent)
    print("RTC",nrtc)
    print("Marks",nmark)
    print("Nadc",nadc)

    plt.figure(1)
    data,yl,xl=h21.get_plotdata()
    plt.imshow(data,origin='lower',vmax=2000)
    plt.xlabel(yl)
    plt.ylabel(xl)
    plt.figure(2)
    data,yl,xl=h2.get_plotdata()
    plt.plot(data,drawstyle='steps-mid')
    plt.ylabel(yl)
    plt.figure(3)
    plt.hist(sortadc,bins=16)
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
    plt.show()
