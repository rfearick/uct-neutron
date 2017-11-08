            
#import copy
from matplotlib.lines import Line2D
from matplotlib.widgets import LassoSelector#, _SelectorWidget

        
class MyLassoSelector(LassoSelector):
    """Selection curve made up of segments of polygon.

    For the selector to remain responsive you must keep a reference to
    it.

    The selected path can be used in conjunction with
    :func:`~matplotlib.path.Path.contains_point` to select
    data points from an image.

    In contrast to :class:`Lasso`, `LassoSelector` is written with an interface
    similar to :class:`RectangleSelector` and :class:`SpanSelector` and will
    continue to interact with the axes until disconnected.

    Parameters:

    *ax* : :class:`~matplotlib.axes.Axes`
        The parent axes for the widget.
    *onselect* : function
        Whenever the lasso is released, the `onselect` function is called and
        passed the vertices of the selected path.

    Example usage::

        ax = subplot(111)
        ax.plot(x,y)

        def onselect(verts):
            print verts
        lasso = LassoSelector(ax, onselect)

     *button* is a list of integers indicating which mouse buttons should
        be used for rectangle selection.  You can also specify a single
        integer if only a single button is desired.  Default is *None*,
        which does not limit which button can be used.

        Note, typically:
         1 = left mouse button
         2 = center mouse button (scroll wheel)
         3 = right mouse button

    """

    def __init__(self, ax, onselect=None, useblit=True, lineprops=None, button=[1,3]):
        LassoSelector.__init__(self, ax, onselect, useblit=useblit, lineprops=lineprops, button=button)
        
        if lineprops is None:
            lineprops = dict()
        if useblit:
            lineprops['animated'] = True
        self.feedback = Line2D([], [], **lineprops)
        self.feedback.set_visible(False)
        self.ax.add_line(self.line)
        self.ax.add_line(self.feedback)
        self.artists = [self.line,self.feedback]
        self.drawing=False
        self.startfeed=None
        self.verts=None

    def _press(self, event):
        #print("_press",event.button, self.startfeed)
        if event.button == 1 and self.verts is None:
            self.verts = []
            self.line.set_data([[], []])
            self.line.set_visible(True)
            self.feedback.set_data([[], []])
            self.feedback.set_visible(True)
            self.startfeed=None

    def _release(self, event):
        print("_release", event.button)
        if self.verts is not None:
            if event.button==1:
                self.startfeed=self._get_data(event)
                self._onrelease(event)
            elif event.button==3:
                self._onrelease(event)
                #self.verts.append(self._get_data(event))
                #self.verts.append(self.verts[0])
                #self.update()
                #self.onselect(self.verts)
                #self.line.set_data([[], []])
                #self.line.set_visible(False)
                #self.verts = None

    def onmove(self, event):
        """Cursor move event handler and validator"""
        #if not self.ignore(event) and self.startfeed is not None:
        #print("m", self.get_active())
        if self.startfeed is not None:
            print("onmove",self.ignore(event))
            event = self._clean_event(event)
            self._onmove(event)
            return True
        return False

    def _onmove(self, event):
        if self.startfeed is not None:
            feedbackline=[self.startfeed,self._get_data(event)]
            print("feedback",feedbackline)
            self.feedback.set_data(list(zip(*feedbackline)))
            self.update()

    def _onrelease(self, event):
        self.verts.append(self._get_data(event))
        if event.button==3:
            self.verts.append(self.verts[0])
        self.line.set_data(list(zip(*self.verts)))
        #print("_onrelease", event.button, self.verts)
        print("_onrelease", event.button, self.startfeed)
        self.update()
        if event.button==3:
            self.onselect(self.verts)
            self.verts=None
            self.startfeed=None

    def get_verts(self):
        """
        return list of vertices
        """
        return self.verts



if __name__=="__main__":
    
    import numpy as np
    #import io

    # use this for mac rather than macosx
    import matplotlib
    matplotlib.use("Qt5Agg")

    import matplotlib.pyplot as plt
    from matplotlib.widgets import Slider
    from matplotlib import path
    
    axcolor = 'lightgoldenrodyellow'


    imdata=np.random.randn(256,256)+10.0
    yl='y'
    xl='x'
    #plt.ion()
    fig,ax=plt.subplots()
    plt.subplots_adjust(bottom=0.20)

    def update(val):
        #v=adjust2d.val
        #print("update",v,val)
        #im=ax.imshow(imdata,origin='lower',vmax=val)
        im.set_clim(0.0,val)
        fig.canvas.draw_idle()
    allverts=[]
    def onselect(verts):
        global imdata
        #print("image",np.shape(imdata))
        ny,nx=np.shape(imdata)
        allverts.append(verts)
        p=path.Path(verts)
        #print("onselect",allverts)
        for ix in range(nx):
            for iy in range(ny):
                if not p.contains_point((iy,ix)):
                    imdata[ix,iy]=0.0
        print("done")
        #print(imdata[0:10,0:2])
        fig2=plt.figure(2)
        im=plt.imshow(imdata,origin='lower',vmax=v0)
        #fig2.canvas.draw_idle()
        plt.show()
        

    v0=np.amax(imdata)
    print(v0)
    #update(vmax)
    #plt.ion()
    im=ax.imshow(imdata,origin='lower',vmax=v0)
    lasso=MyLassoSelector(ax,onselect,useblit=False)
    plt.xlabel(yl)
    plt.ylabel(xl)
    axadj=plt.axes([0.15,0.05,0.7,0.03])
    adjust2d=Slider(axadj, 'Max', 0.01*v0,v0,valinit=v0)
    adjust2d.on_changed(update)

    plt.show()
