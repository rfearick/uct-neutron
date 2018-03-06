"""
=================
supportclasses.py
=================

Support classes for building a GUI for neutron data analysis.

-----
"""

import sys
from PyQt5 import Qt
import icons



class PlotTreeModel(Qt.QStandardItemModel):
    """
    M(odel) part of MVC for spectrum plots.

    This permits the building of a simple tree structure to represent the
    plot or histogram hierarchy. This tree is built using the rather cumbersome
    Qt items so as to be easily interfaced with the rest of the GUI. 

    Methods are provided to walk the tree so that info can be dumped to a file, 
    for example.

    Parameters
    ----------
    parentobject : object
        parent (in Qt sense) of instance of class.


    Attributes
    ----------
    parentobject : object
        Parent of instance.

    """
    def __init__(self, parentobject):
        super().__init__(parent=parentobject)
        self.parentobject=parentobject

    def appendGroup(self, name):
        """
        Append a new *group* to root of tree

        Parameters
        ----------
        name : str
            Name of group, should be unique (not checked!).

        Returns
        -------
        item : QStandardItem representing new group.
        """
        item=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),name)
        self.appendRow(item)
        return item

    def appendAt(self, group, name, data):
        """
        Append an item *name* with data *data* to a *group*.

        Parameters
        ----------
        group : QStandardItem
            Item corresponding to *group*.
        name : str
            Name of new QStandardItem
        data : object
            Data corresponding to new item *name*.

        Returns
        -------
        item 
            QStandardItem representing new *name*.
        """
        item=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),name)
        group.appendRow(item)
        item.setData(data)
        return item 

    def walk(self):
        """
        Walk the tree and print out names of nodes.
        """
        def _walk(item):
            i=0
            while item.child(i) is not None:
                print(item.child(i).text())
                _walk(item.child(i))
                i+=1
           
        item=self.invisibleRootItem()
        _walk(item)

class PlotTreeView(Qt.QTreeView):
    """
    V(iew) and C  part of MVC for spectrum plots.

    This subclasses *Qt.QTreeView* to add a controller method to open a plot
    when double clicked. This has to be displayed to be used, of course.

    Parameters
    ----------
    parentobject : object
        Parent (in Qt sense) of instance of class.

    Attributes
    ----------
    parentobject : object
        Parent of instance.

    """
    def __init__(self, parentobject):
        super().__init__(parent=parentobject)
        self.parentobject=parentobject
        self.doubleClicked.connect(self.openPlot)

    def openPlot(self, index):
        """
        Responds to double click to open plot.

        Parameters
        ----------
        index : QStandardItemIndex
            Index of plot item in tree.
        """
        item=self.model().itemFromIndex(index) #get item from index
        if item.data() is not None:
            item.data().openPlot()    # call item.openPlot()
        
        

if __name__=="__main__":
    
    app = Qt.QApplication(sys.argv)
    C=PlotTreeModel(None)
    g1=C.appendGroup("Group1")
    C.appendAt(g1,"g1_1",None)
    C.appendAt(g1,"g1_2",None)
    C.appendAt(g1,"g1_3",None)
    g2=C.appendGroup("Group2")
    C.appendAt(g2,"g2_1",None)

    C.walk()

    sys.exit(3)
                  
        
        


        
