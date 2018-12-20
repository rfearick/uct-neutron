"""
Create singleton  to implement data holding classes
see:
http://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html

Implement classes to hold data for calibration and analysis constants.

Only a single instance of a class is created so we encapsulate global data
"""

class Singleton(type):
    """
    metaclass for single instance classes
    """
    instance=None
    def __call__(cls, *args, **kw):
        if not cls.instance:
            cls.instance=super(Singleton,cls).__call__(*args,**kw)
        return cls.instance


class Calibration(object, metaclass=Singleton):
    """
    Data for calibration:

    EADC            -- ADC used for energy calibration
    TADC            -- ADC used for TDC calibration
    slope           -- slope of gamma calibration in channel/MeVee
    intercept       -- intercept of gamma calibration in channel
    TAC             -- TDC slope in ch/ns

    Calibration data isolated for convenience 
    """
    
    __slots__=('EADC','TADC','slope','intercept','TAC')

    def __init__(self):
        self.EADC='ADC1'
        self.TADC='ADC3'

    def asDict(self):
        ##return {key: getattr(self,key) for key in self.__slots__}
        vars={}
        for k in self.__slots__:
            try:
                val=getattr(self, k)
                vars[k]=val
            except:
                pass
        return vars

    def keys(self):
        vars=self.asDict()
        return vars.keys()

    def getData(self):
        """
        Package data into dict and return it to caller.
        Values are floats
        """
        data={}
        for d in __class__.__slots__:
            v=getattr(self, d, None)
            if v is not None:
                data[d]=v
        return data

    def setData(self, data):
        """
        Unpack data from dict and store.
        The dict is assumed to be read from disk and data values are str.
        """
        for d in data.keys():
            if d in ['EADC', 'TADC']:
                setattr(self, d, data[d])
            else:
                setattr(self, d, float(data[d]))
            
    def channel(self, E):
        """
        Calculate histogram channel for a given gamma energy (in MeV)
        (this is not efficient because of all the checking and lookup)
        """
        k=self.keys()
        if 'slope' in k and 'intercept' in k:
            return (E-self.intercept)/self.slope
        else:
            return 0.0
        
    def energy(self, ch):
        """
        Calculate energy in MeVee for a given gamma histogram channel
        (this is not efficient because of all the checking and lookup)
        """
        k=self.keys()
        if 'slope' in k and 'intercept' in k:
            return self.intercept+self.slope*ch
        else:
            return 0.0

        
class AnalysisData(object, metaclass=Singleton):
    """
    Data needed for analysis:

    speed_of_light        -- in m/ns
    target_distance       -- distance target to detector, in m
    target_distance_in_ch -- target distance in channels in TDC spectrum
    T0_in_ch              -- channel corresponding to T0 in TDC spectrum
    T0                    -- time of zero tof in TDC spectrum 
    Tgamma                -- time in ns of gamma flash in raw TDC spectrum, used for TOF zero
    calibration_gain      -- gain increase used for gamma calibration
    TAC_interval          -- spacing in ns of peaks from TAC calibrator setting 
    """
    
    __slots__=['speed_of_light','target_distance','target_distance_in_ch','T0',
               'T0_in_ch','Tgamma','calibration_gain','TAC_interval', 'L_threshold' ]
    
    def __init__(self):
        self.setDefaults()

    def setDefaults(self):
        self.speed_of_light=0.3    # m/ns
        self.target_distance=9.159 # m
        self.TAC_interval=20.0     # ns
        self.calibration_gain=4.0
        self.L_threshold=2.5       # MeVee
        self.Tgamma=0.0
        self.T0=0.0

    def getData(self):
        """
        Package data into dict and return it to caller.
        Values are floats
        """
        data={}
        for d in AnalysisData.__slots__:
            v=getattr(self, d, None)
            if v is not None:
                data[d]=v
        return data

    def setData(self, data):
        """
        Unpack data from dict and store.
        The dict is assumed to be read from disk and data values are str.
        """
        for d in data.keys():
            setattr(self, d, float(data[d]))
