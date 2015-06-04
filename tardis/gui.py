"""gui.py contains all the classes used to create the GUI for Tardis.

3. routine listings
4. see also
5. notes
6. references
7. examples

This module must be imported inside IPython console started with eventloop
integration. The console provides the event loop and the place to 
create/calculate the tardis model. So the module is basically a tool to 
visualize results. 

Running instructions
--------------------
    1. Decide which Qt binding you want to use (PySide or PyQt) and 
    accordingly set QT_API in shell
            export QT_API=pyside 
            export QT_API=pyqt 
    2. Start the IPython console with eventloop integration 
            ipython --pylab=qt4
    3. Display your model
            from tardis import gui 
            win = gui.Tardis()
            win.show_model(mdl)

Raises
------
    TemporarilyUnavaliable
        Raised when the currently disabled active mode is requested.

"""
import os
from pkg_resources import parse_version
import exceptions

import numpy as np
import matplotlib
import matplotlib.pylab as plt
import matplotlib.gridspec as gridspec
from matplotlib import colors
from matplotlib.patches import Circle
from matplotlib.figure import *
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4 import NavigationToolbar2QT as NavigationToolbar
if os.environ.get('QT_API', None)=='pyqt':
    from PyQt4 import QtGui, QtCore
elif os.environ.get('QT_API', None)=='pyside':
    from PySide import QtGui, QtCore
else:
    raise ImportError('QT_API was not set! Please exit the IPython console'+
        ' and at the bash prompt use : \n\n export QT_API=pyside \n or \n'+
        ' export QT_API=pyqt \n\n For more information refer to user guide.')
import yaml
from astropy import units as u

from tardis import analysis, util
from tardis import run_tardis
import tardis

if (parse_version(matplotlib.__version__)>=parse_version('1.4')):
    matplotlib.style.use('fivethirtyeight')
else:
    print "Please upgrade matplotlib to a version >=1.4 for best results!"
matplotlib.rcParams['font.family']='serif'
matplotlib.rcParams['font.size']=10.0
matplotlib.rcParams['lines.linewidth']=1.0
matplotlib.rcParams['axes.formatter.use_mathtext']=True
matplotlib.rcParams['axes.edgecolor']=matplotlib.rcParams['grid.color']
matplotlib.rcParams['axes.linewidth']=matplotlib.rcParams['grid.linewidth']

class TemporarilyUnavaliable(Exception):
    """Exception raised when creation of active mode of tardis is attempted."""
    
    def __init__(self, value):
        self.value = value
    
    def __str__(self):
        return repr(self.value)

class Tardis(QtGui.QMainWindow):
    """Create the top level window for the GUI and wait for call to 
    display data.

    """

    def __init__(self, parent=None, config=None, atom_data=None):
        """Create the top level window and all widgets it contains.

        When called with no arguments it initializes the GUI in passive
        mode. When a yaml config file and atom data are provided the 
        GUI starts in the active mode.

        Parameters
        ---------
            parent: None
                Set to None by default and shouldn't be changed unless 
                you are developing something new.
            config: string 
                yaml file with configuration information for TARDIS.
            atom_data: string
                hdf file that has the atom data.

        Raises
        ------
            TemporarilyUnavaliable
                Raised when an attempt is made to start the active mode. 
                This will be removed when active mode is developed.

        """

        #assumes that qt has already been initialized by starting IPython 
        #with the flag "--pylab=qt"
        app = QtCore.QCoreApplication.instance()
        if app is None:
            app = QtGui.QApplication([])
        try:
            from IPython.lib.guisupport import start_event_loop_qt4
            start_event_loop_qt4(app)
        except ImportError:
            app.exec_()

        super(Tardis, self).__init__(parent)

        #path to icons folder
        self.path = os.path.join(tardis.__path__[0],'images')  

        #Check if configuration file was provided
        self.mode = 'passive'
        if config is not None:
            self.mode = 'active'

        #Statusbar
        statusbr = self.statusBar()
        self.successLabel = QtGui.QLabel('<font color="red"><b>Calculation'+ 
            'did not converge</b></font>')
        self.successLabel.setFrameStyle(QtGui.QFrame.StyledPanel |
            QtGui.QFrame.Sunken)
        statusbr.addPermanentWidget(self.successLabel)
        self.modeLabel = QtGui.QLabel('Passive mode')
        statusbr.addPermanentWidget(self.modeLabel)
        statusbr.showMessage(self.mode, 5000)
        statusbr.showMessage("Ready", 5000) 

        #Actions
        quitAction = QtGui.QAction("&Quit", self)
        quitAction.setIcon(QtGui.QIcon(os.path.join(self.path, 
            'closeicon.png')))
        quitAction.triggered.connect(self.close)
        
        self.viewMdv = QtGui.QAction("View &Model", self)
        self.viewMdv.setIcon(QtGui.QIcon(os.path.join(self.path,
            'mdvswitch.png')))
        self.viewMdv.setCheckable(True)
        self.viewMdv.setChecked(True)
        self.viewMdv.setEnabled(False)
        self.viewMdv.triggered.connect(self.switchToMdv)
        
        self.viewForm = QtGui.QAction("&Edit Model", self)
        self.viewForm.setIcon(QtGui.QIcon(os.path.join(self.path,
            'formswitch.png')))
        self.viewForm.setCheckable(True)
        self.viewForm.setEnabled(False)
        self.viewForm.triggered.connect(self.switchToForm)

        #Menubar
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(quitAction)
        self.viewMenu = self.menuBar().addMenu("&View")
        self.viewMenu.addAction(self.viewMdv)
        self.viewMenu.addAction(self.viewForm)
        self.helpMenu = self.menuBar().addMenu("&Help")

        #Toolbar
        fileToolbar = self.addToolBar("File")
        fileToolbar.setObjectName("FileToolBar")  
        fileToolbar.addAction(quitAction)

        viewToolbar = self.addToolBar("View")
        viewToolbar.setObjectName("ViewToolBar")
        viewToolbar.addAction(self.viewMdv)
        viewToolbar.addAction(self.viewForm)

        #Central Widget
        self.stackedWidget = QtGui.QStackedWidget()
        self.mdv = ModelViewer() 
        self.stackedWidget.addWidget(self.mdv)
        
        #In case of active mode
        if self.mode == 'active':
            #Disabled currently
            # self.formWidget = ConfigEditor(config)
            # #scrollarea
            # scrollarea = QtGui.QScrollArea()
            # scrollarea.setWidget(self.formWidget)
            # self.stackedWidget.addWidget(scrollarea)
            # self.viewForm.setEnabled(True)
            # self.viewMdv.setEnabled(True)
            # model = run_tardis(config, atom_data)
            # self.show_model(model)
            raise TemporarilyUnavaliable("The active mode is under development"+
                ". Please use the passive mode for now.")

        self.setCentralWidget(self.stackedWidget)

    def show_model(self, model=None):
        """Set the provided model into the GUI and show the main window.

        Parameters
        ----------
        model: TARDIS model object 
            A keyword argument that takes the tardis model object.

        """
        if model:
            self.mdv.change_model(model)
        if model.converged:
            self.successLabel.setText('<font color="green">converged</font>')
        if self.mode == 'active':
            self.modeLabel.setText('Active Mode')

        self.mdv.fillOutputLabel()
        self.mdv.tableview.setModel(self.mdv.tablemodel)
        self.mdv.plot_model()
        self.mdv.plot_spectrum()
        self.showMaximized()

    def switchToMdv(self):
        """Switch the cental stacked widget to show the modelviewer."""
        self.stackedWidget.setCurrentIndex(0)
        self.viewForm.setChecked(False)

    def switchToForm(self):
        """Switch the cental stacked widget to show the ConfigEditor."""
        self.stackedWidget.setCurrentIndex(1)
        self.viewMdv.setChecked(False)

class ConfigEditor(QtGui.QWidget):
    """The configuration editor widget. 

    This widget is added to the stacked widget that is the central widget of 
    the main top level window created by Tardis. 
    """  
    
    def __init__(self, yamlconfigfile, parent=None):
        """Create and return the configuration widget.

        Parameters
        ----------
            yamlconfigfile: string 
                File name of the yaml configuration file.
            parent: None
                Set to None. The parent is changed when the widget is 
                appended to the layout of its parent.

        """
        super(ConfigEditor, self).__init__(parent)
        
        #Configurations from the input and template    
        configDict = yaml.load(open(yamlconfigfile))
        templatedictionary ={'tardis_config_version':[True, 'v1.0'],
            'supernova':{ 'luminosity_requested':[True, '1 solLum'],
                          'time_explosion':[True, None],
                          'distance':[False, None],
                          'luminosity_wavelength_start':[False, '0 angstrom'],
                          'luminosity_wavelength_end':[False, 'inf angstrom'],
                        },
            'atom_data':[True,'File Browser'],
            'plasma':{ 'initial_t_inner':[False, '-1K'],
                       'initial_t_rad':[False,'10000K'],
                       'disable_electron_scattering':[False, False],
                       'ionization':[True, None],
                       'excitation':[True, None],
                       'radiative_rates_type':[True, None],
                       'line_interaction_type':[True, None],
                       'w_epsilon':[False, 1e-10],
                       'delta_treatment':[False, None],
                       'nlte':{ 'species':[False, []],
                                'coronal_approximation':[False, False],
                                'classical_nebular':[False, False]
                              }
                      },
            'model':{ 'structure':{'type':[True, ['file|_:_|filename|_:_|'+
            'filetype|_:_|v_inner_boundary|_:_|v_outer_boundary', 
            'specific|_:_|velocity|_:_|density']],
                      'filename':[True, None],
                      'filetype':[True, None],
                      'v_inner_boundary':[False, '0 km/s'],
                      'v_outer_boundary':[False, 'inf km/s'],
                      'velocity':[True, None],
                      'density':{ 'type':[True, ['branch85_w7|_:_|w7_time_0'+
                                    '|_:_|w7_time_0|_:_|w7_time_0',
                                    'exponential|_:_|time_0|_:_|rho_0|_:_|'+
                                    'v_0','power_law|_:_|time_0|_:_|rho_0'+
                                    '|_:_|v_0|_:_|exponent','uniform|_:_|value']],
                                  'w7_time_0':[False, '0.000231481 day'],
                                  'w7_rho_0':[False, '3e29 g/cm^3'],
                                  'w7_v_0': [False, '1 km/s'],
                                  'time_0':[True, None],
                                  'rho_0':[True, None],
                                  'v_0': [True, None], 
                                  'exponent': [True, None],
                                  'value':[True, None] 
                                }
                                  },
                      'abundances':{ 'type':[True, ['file|_:_|filetype|_:_|'+
                                     'filename', 'uniform']],
                                     'filename':[True, None],
                                     'filetype':[False, None]
                                    }
                    },
            'montecarlo':{'seed':[False, 23111963],
                          'no_of_packets':[True, None],
                          'iterations':[True, None],
                          'black_body_sampling':{
                                                    'start': '1 angstrom',
                                                    'stop': '1000000 angstrom',
                                                    'num': '1.e+6',
                                                },
                          'last_no_of_packets':[False, -1],
                          'no_of_virtual_packets':[False, 0],
                          'enable_reflective_inner_boundary':[False, False],
                          'inner_boundary_albedo':[False, 0.0],
                          'convergence_strategy':{ 'type':[True, 
                          ['damped|_:_|damping_constant|_:_|t_inner|_:_|'+
                          't_rad|_:_|w|_:_|lock_t_inner_cycles|_:_|'+
                          't_inner_update_exponent','specific|_:_|threshold'+
                          '|_:_|fraction|_:_|hold_iterations|_:_|t_inner'+
                          '|_:_|t_rad|_:_|w|_:_|lock_t_inner_cycles|_:_|'+
                          'damping_constant|_:_|t_inner_update_exponent']],
                                   't_inner_update_exponent':[False, -0.5],
                                   'lock_t_inner_cycles':[False, 1],
                                   'hold_iterations':[True, 3],
                                   'fraction':[True, 0.8],
                                   'damping_constant':[False, 0.5],
                                   'threshold':[True, None],
                                   't_inner':{ 'damping_constant':[False, 0.5],
                                               'threshold': [False, None]
                                             },
                                   't_rad':{'damping_constant':[False, 0.5],
                                            'threshold':[True, None]
                                            },
                                    'w':{'damping_constant': [False, 0.5],
                                         'threshold': [True, None]
                                         }
                                                }
                          },
            'spectrum':[True, None]
            }
        self.matchDicts(configDict, templatedictionary)

        self.layout = QtGui.QVBoxLayout()

        #Make tree
        self.trmodel = TreeModel(templatedictionary)
        self.colView = QtGui.QColumnView()
        self.colView.setModel(self.trmodel)
        #Five columns of width 256 each can be visible at once
        self.colView.setFixedWidth(256*5) 
        self.colView.setItemDelegate(TreeDelegate(self))
        self.layout.addWidget(self.colView)

        #Recalculate button
        button = QtGui.QPushButton('Recalculate')
        button.setFixedWidth(90)
        self.layout.addWidget(button)
        button.clicked.connect(self.recalculate) 

        #Finally put them all in
        self.setLayout(self.layout)

    def matchDicts(self, dict1, dict2): #dict1<=dict2
        """Compare and combine two dictionaries.

        If there are new keys in `dict1` then they are appended to `dict2`.
        The `dict2` stores the values for the keys in `dict1` but it 
        first modifies them by taking the value and appending to a 
        list whose first item is either True or False, indicating if 
        that key is mandatory or not. The goal of this method is to
        perform validation by inserting user provided values into the 
        template dictionary. After inserting user given values into the 
        template dictionary, all the keys have either default or user 
        provided values. Then it can be used to build a tree to be 
        shown in the ConfigEditor.

        Parameters
        ----------
            dict1: dictionary
                The dictionary of user provided configuration.
            dict2: dictionary
                The template dictionary with all default values set. This 
                one may have some keys missing that are present in the
                `dict1`. Such keys will be appended.
        Raises
        ------
            IOError
                If the configuration file has an invalid value for a 
                key that can only take values from a predefined list,
                then this error is raised.

        """
        for key in dict1:
            if key in dict2:
                if isinstance(dict2[key], dict):
                    self.matchDicts(dict1[key], dict2[key])

                elif isinstance(dict2[key], list):
                    if isinstance(dict2[key][1], list):
                        
                        #options = dict2[key][1] #This is passed by reference. 
                        #So copy the list manually.
                        options = [dict2[key][1][i] for i in range(
                            len(dict2[key][1]))]

                        for i in range(len(options)):
                            options[i] = options[i].split('|_:_|')[0]

                        optionselected = dict1[key]

                        if optionselected in options:
                            indexofselected = options.index(optionselected)
                            temp = dict2[key][1][0]
                            
                            dict2[key][1][0] = dict2[key][1][indexofselected]
                            dict2[key][1][indexofselected] = temp
                            
                            
                        else:
                            print 'The selected and available options'
                            print optionselected
                            print options
                            raise exceptions.IOError("An invalid option was"+
                                " provided in the input file")

                else:
                    dict2[key] = dict1[key]
            else:
                toappend = [False, dict1[key]]
                dict2[key] = toappend

    def recalculate(self):
        """Recalculate and display the model from the modified data in
        the ConfigEditor.
        """
        pass

class Node(object):
    """Object that serves as the nodes in the TreeModel.

    Attributes
    ----------
        parent: None/Node 
            The parent of the node.
        children: list of Node
            The children of the node.
        data: list of string 
            The data stored on the node. Can be a key or a value.
        siblings: dictionary 
            A dictionary of nodes that are siblings of this node. The 
            keys are the values of the nodes themselves. This is 
            used to keep track of which value the user has selected
            if the parent of this node happens to be a key that can
            take values from a list.

    """

    def __init__(self, data, parent=None):
        """Create one node with the data and parent provided.

        Parameters
        ----------
            data: list of string
                The data that is intended to be stored on the node.
            parent: Node 
                Another node which is the parent of this node. The 
                root node has parent set to None.

        Note
        ----
            A leaf node is a node that is the only child of its parent. 
            For this tree this will always be the case. This is because
            the tree stores the key at every node except the leaf node
            where it stores the value for the key. So if in the dictionary
            the value of a key is another dictionary, then it will 
            be a node with no leafs. If the key has a value that is a 
            value or a list then it will have one child that is a leaf.
            The leaf can have no children. For example-

            'a':val1
            'b':{'c':val2
                 'd':val3
                 'e':{'f':val4
                      'g':val5
                         :val6
                         :val7}} *In this case the key g can take values
                                  val7, val5 and val6 and is currently
                                  set to val5.

            In the tree shown above all quoted values are keys in the 
            dictionary and are non-leaf nodes in the tree. All values 
            of the form valx are leaf nodes and are not dictionaries 
            themselves. If the keys have non-dictionary values then they
            have a leaf attached. And no leaf can have a child.
        
        """
        self.parent = parent
        self.children = []
        self.data = data
        self.siblings = {}  #For 'type' fields. Will store the nodes to 
                            #enable disable on selection

    def appendChild(self, child):
        """Add a child to this node."""
        self.children.append(child)
        child.parent = self

    def getChild(self, i):
        """Get the ith child of this node. 

        No error is raised if the cild requested doesn't exist. A 
        None is returned in such cases.

        """
        if i < self.numChildren():
            return self.children[i]
        else:
            return None

    def numChildren(self):
        """Number of children this node has."""
        return len(self.children)

    def numColumns(self):
        """Returns the number of strings stored in the data attribute."""
        return len(self.data)

    def getData(self, i):
        """Returns the ith string from the data list.

        No error is raised if the data list index is exceeded. A None is
        returned in such cases.

        """
        try:
            return self.data[i]
        except IndexError:
            return None

    def getParent(self):
        """Return the parent of this node."""
        return self.parent

    def getIndexOfSelf(self):
        """Returns the number at which it comes in the list of its 
        parent's children. For root the index 0 is returned.

        """
        if self.parent:
            return self.parent.children.index(self)
        else:
            return 0

    def setData(self, column, value):
        """Set the data for the ith index to the provided value. Returns
        true if the data was set successfully.

        """
        if column < 0 or column >= self.numColumns():
            return False

        self.data[column] = value

        return True

class TreeModel(QtCore.QAbstractItemModel):
    """The class that defines the tree for ConfigEditor.

    Parameters
    ----------
        root: Node
            Root node of the tree.
        disabledNodes: list of Node 
            List of leaf nodes that are not editable currently.
        typenodes: list of Node 
            List of nodes that correspond to keys that set container 
            types. Look at tardis configuration template. These are the
            nodes that have values that can be set from a list.

    """
    def __init__(self, dictionary, parent=None):
        """Create a tree of tardis configuration dictionary.

        Parameters
        ----------
            dictionary: dictionary            
                The dictionary that needs to be converted to the tree.
            parent: None 
                Used to instantiate the QAbstractItemModel

        """
        QtCore.QAbstractItemModel.__init__(self, parent)

        self.root = Node(["column A"])
        self.disabledNodes = []
        self.typenodes = []
        self.dictToTree(dictionary, self.root)

    def dictToTree(self, dictionary, root):
        """Create the tree and append siblings to nodes that need them.

        Parameters
        ----------
            dictionary: dictionary
                The dictionary that is to be converted to the tree.
            root: Node 
                The root node of the tree.

        """
        #Construct tree with all nodes
        self.treeFromNode(dictionary, root)

        #Append siblings to type nodes
        for node in self.typenodes: #For every type node
            parent = node.getParent()
            sibsdict = {}
            for i in range(parent.numChildren()):
                sibsdict[parent.getChild(i).getData(0)] = parent.getChild(i)

            typesleaf = node.getChild(0)
            for i in range(typesleaf.numColumns()):
                sibstrings = typesleaf.getData(i).split('|_:_|')
            
                typesleaf.setData(i, sibstrings[0])
                sibslist = []
                for j in range(1, len(sibstrings)):
                    if sibstrings[j] in sibsdict:
                        sibslist.append(sibsdict[sibstrings[j]])

                typesleaf.siblings[sibstrings[0]] = sibslist
            
            #Then append siblings of current selection for all type nodes to
            #disabled nodes
            for i in range(1,typesleaf.numColumns()):
                key = typesleaf.getData(i)
                for nd in typesleaf.siblings[key]:
                    self.disabledNodes.append(nd)


    def treeFromNode(self, dictionary, root):
        """Convert dictionary to tree. Called by dictToTree."""
        for key in dictionary:
            child = Node([key])
            root.appendChild(child)
            if isinstance(dictionary[key], dict):
                self.treeFromNode(dictionary[key], child)
            elif isinstance(dictionary[key], list):
                if isinstance(dictionary[key][1], list):
                    leaf = Node(dictionary[key][1])    
                else:
                    leaf = Node([dictionary[key][1]])

                child.appendChild(leaf)
                if key == 'type':
                    self.typenodes.append(child)

    def dictFromNode(self, node): 
        """Take a node and convert the whole subtree rooted at it into a 
        dictionary.

        """
        children = [node.getChild(i) for i in range(node.numChildren())]
        if len(children) > 1:
            dictionary = {}
            for nd in children:
                if nd in self.disabledNodes:
                    pass
                else:
                    dictionary[nd.getData(0)] = self.dictFromNode(nd)
            return dictionary
        elif len(children)==1:
            return children[0].getData(0)

    def columnCount(self, index):
        """Return the number of columns in the node pointed to by
        the given model index.

        """
        if index.isValid():
            return index.internalPointer().numColumns()
        else:
            return self.root.numColumns()

    def data(self, index, role):
        """Returns the asked data for the node specified by the modeLabel
        index."""
        if not index.isValid():
            return None

        if role != QtCore.Qt.DisplayRole:
            return None

        item = index.internalPointer()

        return item.getData(index.column())

    def flags(self, index):
        """Return flags for the items whose model index is provided."""
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        node = index.internalPointer()
        if ((node.getParent() in self.disabledNodes) or 
            (node in self.disabledNodes)):
            return QtCore.Qt.NoItemFlags

        if node.numChildren()==0:
            return (QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | 
                QtCore.Qt.ItemIsSelectable)

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable        

    def getItem(self, index):
        """Returns the node to which the model index is pointing. If the
        model index is invalid then the root node is returned.

        """
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item

        return self.root

    def headerData(self, section, orientation, role):
        """Returns header data. This is not used in QColumnView. But will
        be needed for QTreeView.

        """
        if (orientation == QtCore.Qt.Horizontal and 
          role == QtCore.Qt.DisplayRole):
            return self.root.getData(section)

        return None

    def index(self, row, column, parent=QtCore.QModelIndex()):
        """Create a model index for the given row and column. For a 
        tree model, the row is the set of nodes with the same parents and
        the column indexes the data in the node.

        """
        if parent.isValid() and parent.column() != 0:
            return QtCore.QModelIndex()

        parentItem = self.getItem(parent)
        childItem = parentItem.getChild(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QtCore.QModelIndex()

    def insertColumns(self, position, columns, parent=QtCore.QModelIndex()):
        """Insert columns in the tree model."""
        self.beginInsertColumns(parent, position, position + columns - 1)
        success = self.root.insertColumns(position, columns)
        self.endInsertColumns()

        return success

    def insertRows(self, position, rows, parent=QtCore.QModelIndex()):
        """Insert rows in the tree model."""
        parentItem = self.getItem(parent)
        self.beginInsertRows(parent, position, position + rows - 1)
        success = parentItem.insertChildren(position, rows,
                    self.rootItem.columnCount())
        self.endInsertRows()

        return success

    def parent(self, index):
        """Return the parent of the node to which the index points."""
        if not index.isValid():
            return QtCore.QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.getParent()

        if parentItem == self.root:
            return QtCore.QModelIndex()

        return self.createIndex(parentItem.getIndexOfSelf(), 0, parentItem)

    def rowCount(self, parent=QtCore.QModelIndex()):
        """The number of rows for a given node. 
        
        (The number of rows is just the number of children for a node.)

        """
        parentItem = self.getItem(parent)

        return parentItem.numChildren()

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """Set the value as the data at the location pointed by the 
        index.

        """
        if role != QtCore.Qt.EditRole:
            return False

        item = self.getItem(index)
        result = item.setData(index.column(), value)

        if result:
            self.dataChanged.emit(index, index)
            #print self.dictFromNode(self.root)
        return result

    def setHeaderData(self, section, orientation, value, 
        role=QtCore.Qt.EditRole):
        """Change header data. Unused in columnview."""
        if role != QtCore.Qt.EditRole or orientation != QtCore.Qt.Horizontal:
            return False

        result = self.root.setData(section, value)
        if result:
            self.headerDataChanged.emit(orientation, section, section)

        return result

class TreeDelegate(QtGui.QStyledItemDelegate):
    """Create a custom delegate to modify the columnview that displays the 
    TreeModel.

    """
    def __init__(self, parent=None):
        """Call the constructor of the superclass."""
        QtGui.QStyledItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        """Create a lineEdit or combobox depending on the type of node."""
        node = index.internalPointer()
        if node.numColumns()>1:
            combobox = QtGui.QComboBox(parent)
            combobox.addItems([node.getData(i) for i in range(node.numColumns())])
            combobox.setEditable(False)
            return combobox
        else:
            editor =  QtGui.QLineEdit(parent)
            editor.setText(str(node.getData(0)))
            editor.returnPressed.connect(self.closeAndCommit)
            return editor

    def closeAndCommit(self):
        """Saver for the line edits."""
        editor = self.sender()
        if isinstance(editor, QtGui.QLineEdit):
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QtGui.QAbstractItemDelegate.NoHint)

    def setModelData(self, editor, model, index):
        """Called when new data id set in the model. This is where the
        siblings of type nodes are enabled or disabled according to the 
        new choice made.

        """
        node = index.internalPointer()

        if node.numColumns() > 1 and node.getParent().getData(0) != 'type':
            selectedIndex = editor.currentIndex()
            firstItem = node.getData(0)
            node.setData(0, str(editor.currentText()))
            node.setData(selectedIndex, str(firstItem))

        elif node.numColumns() > 1 and node.getParent().getData(0) == 'type':
            selectedIndex = editor.currentIndex()
            firstItem = node.getData(0)
            node.setData(0, str(editor.currentText()))
            node.setData(selectedIndex, str(firstItem))

            itemsToDisable = node.siblings[firstItem]
            itemsToEnable = node.siblings[str(editor.currentText())]

            for nd in itemsToDisable:
                model.disabledNodes.append(nd)

            for nd in itemsToEnable:
                if nd in model.disabledNodes:
                    model.disabledNodes.remove(nd) 

        elif isinstance(editor, QtGui.QLineEdit): 
            node.setData(0, str(editor.text()))
        else:
            QtGui.QStyledItemDelegate.setModelData(self, editor, model, index)
            
        #print model.dictFromNode(model.root) 
        #f = open('dictester.dat','w')
        #f.write(yaml.dump(model.dictFromNode(model.root)))
        #f.close()

class ModelViewer(QtGui.QWidget):
    """The widget that holds all the plots and tables that visualize 
    the data in the tardis model. This is also appended to the stacked 
    widget in the top level window.

    """
    
    def __init__(self, parent=None):
        """Create all widgets that are children of ModelViewer."""
        super(ModelViewer, self).__init__(parent)
        
        #Data structures
        self.model = None
        self.shell_info = {}
        self.line_info = []

        #Shells widget
        self.shellWidget = self.makeShellWidget()
        
        #Spectrum widget
        self.spectrumWidget = self.makeSpectrumWidget()

        #Plot tab widget
        self.plotTabWidget = QtGui.QTabWidget()
        self.plotTabWidget.addTab(self.shellWidget,"&Shells")
        self.plotTabWidget.addTab(self.spectrumWidget, "S&pectrum")

        #Table widget
        self.tablemodel = SimpleTableModel([['Shell: '], ["Rad. temp", "Ws"]],
         (1, 0))
        self.tableview = QtGui.QTableView()
        self.tableview.setMinimumWidth(200)
        self.tableview.connect(self.tableview.verticalHeader(), 
            QtCore.SIGNAL('sectionClicked(int)'), self.graph.highlight_shell)
        self.tableview.connect(self.tableview.verticalHeader(), 
            QtCore.SIGNAL('sectionDoubleClicked(int)'),
            self.on_header_double_clicked)

        #Label for text output
        self.outputLabel = QtGui.QLabel()
        self.outputLabel.setFrameStyle(QtGui.QFrame.StyledPanel | 
            QtGui.QFrame.Sunken)
        self.outputLabel.setStyleSheet("QLabel{background-color:white;}")

        #Group boxes
        graphsBox = QtGui.QGroupBox("Visualized results")
        textsBox = QtGui.QGroupBox("Model parameters")
        tableBox = QtGui.QGroupBox("Tabulated results")

        #For textbox
        textlayout = QtGui.QHBoxLayout()
        textlayout.addWidget(self.outputLabel)

        tableslayout = QtGui.QVBoxLayout()
        tableslayout.addWidget(self.tableview)
        tableBox.setLayout(tableslayout)

        visualayout = QtGui.QVBoxLayout()
        visualayout.addWidget(self.plotTabWidget)
        graphsBox.setLayout(visualayout)

        self.layout = QtGui.QHBoxLayout()
        self.layout.addWidget(graphsBox)
        textntablelayout = QtGui.QVBoxLayout()
        textsBox.setLayout(textlayout)
        textntablelayout.addWidget(textsBox)
        textntablelayout.addWidget(tableBox)

        self.layout.addLayout(textntablelayout)                
        self.setLayout(self.layout)

    def fillOutputLabel(self):
        """Read some data from tardis model and display on the label for 
        quick user access.

        """
        labeltext = 'Iterations requested: {} <br/> Iterations executed:  {}<br/>\
                     Model converged     : {} <br/> Simulation Time    :  {} s <br/>\
                     Inner Temperature   : {} K <br/> Number of packets  :  {}<br/>\
                     Inner Luminosity    : {}'\
                     .format(self.model.iterations_max_requested, 
                        self.model.iterations_executed,
                        '<font color="green"><b>True</b></font>' if 
                        self.model.converged else 
                        '<font color="red"><b>False</b></font>', 
                        self.model.time_of_simulation.value,
                        self.model.t_inner.value, 
                        self.model.current_no_of_packets,
                        self.model.luminosity_inner)
        self.outputLabel.setText(labeltext)

    def makeShellWidget(self):
        """Create the plot of the the shells and place it inside a 
        container widget. Return the container widget.

        """
        #Widgets for plot of shells
        self.graph = MatplotlibWidget(self, 'model')
        self.graph_label = QtGui.QLabel('Select Property:')
        self.graph_button = QtGui.QToolButton()
        self.graph_button.setText('Rad. temp')
        self.graph_button.setPopupMode(QtGui.QToolButton.MenuButtonPopup)
        self.graph_button.setMenu(QtGui.QMenu(self.graph_button))
        self.graph_button.menu().addAction('Rad. temp').triggered.connect(
            self.change_graph_to_t_rads)
        self.graph_button.menu().addAction('Ws').triggered.connect(
            self.change_graph_to_ws)

        #Layouts: bottom up
        self.graph_subsublayout = QtGui.QHBoxLayout()
        self.graph_subsublayout.addWidget(self.graph_label)
        self.graph_subsublayout.addWidget(self.graph_button)

        self.graph_sublayout = QtGui.QVBoxLayout()
        self.graph_sublayout.addLayout(self.graph_subsublayout)
        self.graph_sublayout.addWidget(self.graph)

        containerWidget = QtGui.QWidget()
        containerWidget.setLayout(self.graph_sublayout)
        return containerWidget

    def makeSpectrumWidget(self):
        """Create the spectrum plot and associated buttons and append to
        a container widget. Return the container widget.

        """
        self.spectrum = MatplotlibWidget(self)
        self.spectrum_label = QtGui.QLabel('Select Spectrum:')
        self.spectrum_button = QtGui.QToolButton()
        self.spectrum_button.setText('spec_flux_angstrom')
        self.spectrum_button.setPopupMode(QtGui.QToolButton.MenuButtonPopup)
        self.spectrum_button.setMenu(QtGui.QMenu(self.spectrum_button))
        self.spectrum_button.menu().addAction('spec_flux_angstrom'
            ).triggered.connect(self.change_spectrum_to_spec_flux_angstrom)
        self.spectrum_button.menu().addAction('spec_virtual_flux_angstrom'
            ).triggered.connect(self.change_spectrum_to_spec_virtual_flux_angstrom)
        self.spectrum_span_button = QtGui.QPushButton('Show Wavelength Range')
        self.spectrum_span_button.clicked.connect(self.spectrum.show_span)
        self.spectrum_line_info_button = QtGui.QPushButton('Show Line Info')
        self.spectrum_line_info_button.hide()
        self.spectrum_line_info_button.clicked.connect(self.spectrum.show_line_info)

        self.spectrum_subsublayout = QtGui.QHBoxLayout()
        self.spectrum_subsublayout.addWidget(self.spectrum_span_button)
        self.spectrum_subsublayout.addWidget(self.spectrum_label)
        self.spectrum_subsublayout.addWidget(self.spectrum_button)

        self.spectrum_sublayout = QtGui.QVBoxLayout()
        self.spectrum_sublayout.addLayout(self.spectrum_subsublayout)
        self.spectrum_sublayout.addWidget(self.spectrum_line_info_button)
        self.spectrum_sublayout.addWidget(self.spectrum)
        self.spectrum_sublayout.addWidget(self.spectrum.toolbar)

        containerWidget = QtGui.QWidget()
        containerWidget.setLayout(self.spectrum_sublayout)
        return containerWidget


    def update_data(self, model=None):
        """Associate the given model with the GUI and display results."""
        if model:
            self.change_model(model)
        self.tablemodel.updateTable()
        for index in self.shell_info.keys():
            self.shell_info[index].update_tables()
        self.plot_model()
        if self.graph_button.text == 'Ws':
            self.change_graph_to_ws()
        self.plot_spectrum()
        if self.spectrum_button.text == 'spec_virtual_flux_angstrom':
            self.change_spectrum_to_spec_virtual_flux_angstrom()
        self.show()

    def change_model(self, model):
        """Reset the model set in the GUI."""
        self.model = model
        self.tablemodel.arraydata = []
        self.tablemodel.addData(model.t_rads.value.tolist())
        self.tablemodel.addData(model.ws.tolist())

    def change_spectrum_to_spec_virtual_flux_angstrom(self):
        """Change the spectrum data to the virtual spectrum."""
        if self.model.spectrum_virtual.luminosity_density_lambda is None:
            luminosity_density_lambda = np.zeros_like(
                self.model.spectrum_virtual.wavelength)
        else:
            luminosity_density_lambda = \
            self.model.spectrum_virtual.luminosity_density_lambda.value

        self.change_spectrum(luminosity_density_lambda, 'spec_flux_angstrom')

    def change_spectrum_to_spec_flux_angstrom(self):
        """Change spectrum data back from virtual spectrum. (See the 
            method above)."""
        if self.model.spectrum.luminosity_density_lambda is None:
            luminosity_density_lambda = np.zeros_like(
                self.model.spectrum.wavelength)
        else:
            luminosity_density_lambda = \
            self.model.spectrum.luminosity_density_lambda.value

        self.change_spectrum(luminosity_density_lambda, 'spec_flux_angstrom')

    def change_spectrum(self, data, name):
        """Replot the spectrum plot using the data provided. Called
        when changing spectrum types. See the two methods above.

        """
        self.spectrum_button.setText(name)
        self.spectrum.dataplot[0].set_ydata(data)
        self.spectrum.ax.relim()
        self.spectrum.ax.autoscale()
        self.spectrum.draw()

    def plot_spectrum(self):
        """Plot the spectrum and add labels to the graph."""
        self.spectrum.ax.clear()
        self.spectrum.ax.set_title('Spectrum')
        self.spectrum.ax.set_xlabel('Wavelength (A)')
        self.spectrum.ax.set_ylabel('Intensity')
        wavelength = self.model.spectrum.wavelength.value
        if self.model.spectrum.luminosity_density_lambda is None:
            luminosity_density_lambda = np.zeros_like(wavelength)
        else:
            luminosity_density_lambda =\
             self.model.spectrum.luminosity_density_lambda.value

        self.spectrum.dataplot = self.spectrum.ax.plot(wavelength, 
            luminosity_density_lambda, label='b')
        self.spectrum.draw()

    def change_graph_to_ws(self):
        """Change the shell plot to show dilution factor."""
        self.change_graph(self.model.ws, 'Ws', '')

    def change_graph_to_t_rads(self):
        """Change the graph back to radiation Temperature."""
        self.change_graph(self.model.t_rads.value, 't_rads', '(K)')

    def change_graph(self, data, name, unit):
        """Called to change the shell plot by the two methods above."""
        self.graph_button.setText(name)
        self.graph.dataplot[0].set_ydata(data)
        self.graph.ax1.relim()
        self.graph.ax1.autoscale()
        self.graph.ax1.set_title(name + ' vs Shell')
        self.graph.ax1.set_ylabel(name + ' ' + unit)
        normalizer = colors.Normalize(vmin=data.min(), vmax=data.max())
        color_map = plt.cm.ScalarMappable(norm=normalizer, cmap=plt.cm.jet)
        color_map.set_array(data)
        self.graph.cb.set_clim(vmin=data.min(), vmax=data.max())
        self.graph.cb.update_normal(color_map)
        if unit == '(K)':
            unit = 'T (K)'
        self.graph.cb.set_label(unit)
        for i, item in enumerate(data):
            self.shells[i].set_facecolor(color_map.to_rgba(item))
        self.graph.draw()

    def plot_model(self):
        """Plot the two graphs, the shell model and the line plot 
        both showing the radiation temperature and set labels.

        """
        self.graph.ax1.clear()
        self.graph.ax1.set_title('Rad. Temp vs Shell')
        self.graph.ax1.set_xlabel('Shell Number')
        self.graph.ax1.set_ylabel('Rad. Temp (K)')
        self.graph.ax1.yaxis.get_major_formatter().set_powerlimits((0, 1))
        self.graph.dataplot = self.graph.ax1.plot(
            range(len(self.model.t_rads.value)), self.model.t_rads.value)
        self.graph.ax2.clear()
        self.graph.ax2.set_title('Shell View')
        self.graph.ax2.set_xticklabels([])
        self.graph.ax2.set_yticklabels([])
        self.graph.ax2.grid = True

        self.shells = []
        t_rad_normalizer = colors.Normalize(vmin=self.model.t_rads.value.min(), 
            vmax=self.model.t_rads.value.max())
        t_rad_color_map = plt.cm.ScalarMappable(norm=t_rad_normalizer, 
            cmap=plt.cm.jet)
        t_rad_color_map.set_array(self.model.t_rads.value)
        if self.graph.cb:
            self.graph.cb.set_clim(vmin=self.model.t_rads.value.min(), 
                vmax=self.model.t_rads.value.max())
            self.graph.cb.update_normal(t_rad_color_map)
        else:
            self.graph.cb = self.graph.figure.colorbar(t_rad_color_map)
            self.graph.cb.set_label('T (K)')
        self.graph.normalizing_factor = 0.2 * (
            self.model.tardis_config.structure.r_outer.value[-1] - 
            self.model.tardis_config.structure.r_inner.value[0]) / (
            self.model.tardis_config.structure.r_inner.value[0])

        #self.graph.normalizing_factor = 8e-16
        for i, t_rad in enumerate(self.model.t_rads.value):
            r_inner = (self.model.tardis_config.structure.r_inner.value[i] * 
                self.graph.normalizing_factor)
            r_outer = (self.model.tardis_config.structure.r_outer.value[i] * 
                self.graph.normalizing_factor)
            self.shells.append(Shell(i, (0,0), r_inner, r_outer, 
                facecolor=t_rad_color_map.to_rgba(t_rad),
                picker=self.graph.shell_picker))
            self.graph.ax2.add_patch(self.shells[i])
        self.graph.ax2.set_xlim(0, 
            self.model.tardis_config.structure.r_outer.value[-1] * 
            self.graph.normalizing_factor)
        self.graph.ax2.set_ylim(0, 
            self.model.tardis_config.structure.r_outer.value[-1] * 
            self.graph.normalizing_factor)
        self.graph.figure.tight_layout()
        self.graph.draw()

    def on_header_double_clicked(self, index):
        """Callback to get counts for different Z from table."""
        self.shell_info[index] = ShellInfo(index, self)

class ShellInfo(QtGui.QDialog):
    """Dialog to display Shell abundances."""

    def __init__(self, index, parent=None):
        """Create the widget to display shell info and set data."""
        super(ShellInfo, self).__init__(parent)
        self.parent = parent
        self.shell_index = index
        self.setGeometry(400, 150, 200, 400)
        self.setWindowTitle('Shell %d Abundances' % (self.shell_index + 1))
        self.atomstable = QtGui.QTableView()
        self.ionstable = QtGui.QTableView()
        self.levelstable = QtGui.QTableView()
        self.atomstable.connect(self.atomstable.verticalHeader(), 
            QtCore.SIGNAL('sectionClicked(int)'),
            self.on_atom_header_double_clicked)


        self.table1_data = self.parent.model.tardis_config.abundances[
            self.shell_index]
        self.atomsdata = SimpleTableModel([['Z = '], ['Count (Shell %d)' % (
            self.shell_index + 1)]], iterate_header=(2, 0), 
            index_info=self.table1_data.index.values.tolist())
        self.ionsdata = None
        self.levelsdata = None
        self.atomsdata.addData(self.table1_data.values.tolist())
        self.atomstable.setModel(self.atomsdata)

        self.layout = QtGui.QHBoxLayout()
        self.layout.addWidget(self.atomstable)
        self.layout.addWidget(self.ionstable)
        self.layout.addWidget(self.levelstable)
        self.setLayout(self.layout)
        self.ionstable.hide()
        self.levelstable.hide()
        self.show()

    def on_atom_header_double_clicked(self, index):
        """Called when a header in the first column is clicked to show 
        ion populations."""
        self.current_atom_index = self.table1_data.index.values.tolist()[index]
        self.table2_data = self.parent.model.plasma_array.ion_populations[
            self.shell_index].ix[self.current_atom_index]
        self.ionsdata = SimpleTableModel([['Ion: '], 
            ['Count (Z = %d)' % self.current_atom_index]], 
            iterate_header=(2, 0), 
            index_info=self.table2_data.index.values.tolist())
        normalized_data = []
        for item in self.table2_data.values:
            normalized_data.append(float(item /
               self.parent.model.tardis_config.number_densities[self.shell_index]
               .ix[self.current_atom_index]))


        self.ionsdata.addData(normalized_data)
        self.ionstable.setModel(self.ionsdata)
        self.ionstable.connect(self.ionstable.verticalHeader(), QtCore.SIGNAL(
            'sectionClicked(int)'),self.on_ion_header_double_clicked)
        self.levelstable.hide()
        self.ionstable.setColumnWidth(0, 120)
        self.ionstable.show()
        self.setGeometry(400, 150, 380, 400)
        self.show()

    def on_ion_header_double_clicked(self, index):
        """Called on double click of ion headers to show level populations."""
        self.current_ion_index = self.table2_data.index.values.tolist()[index]
        self.table3_data = self.parent.model.plasma_array.level_populations[
            self.shell_index].ix[self.current_atom_index, self.current_ion_index]
        self.levelsdata = SimpleTableModel([['Level: '], 
            ['Count (Ion %d)' % self.current_ion_index]], 
            iterate_header=(2, 0), 
            index_info=self.table3_data.index.values.tolist())
        normalized_data = []
        for item in self.table3_data.values.tolist():
            normalized_data.append(float(item / 
            self.table2_data.ix[self.current_ion_index]))
        self.levelsdata.addData(normalized_data)
        self.levelstable.setModel(self.levelsdata)
        self.levelstable.setColumnWidth(0, 120)
        self.levelstable.show()
        self.setGeometry(400, 150, 580, 400)
        self.show()

    def update_tables(self):
        """Update table data for shell info viewer."""
        self.table1_data = self.parent.model.plasma_array[
            self.shell_index].number_densities
        self.atomsdata.index_info=self.table1_data.index.values.tolist()
        self.atomsdata.arraydata = []
        self.atomsdata.addData(self.table1_data.values.tolist())
        self.atomsdata.updateTable()
        self.ionstable.hide()
        self.levelstable.hide()
        self.setGeometry(400, 150, 200, 400)
        self.show()

class LineInteractionTables(QtGui.QWidget):
    """Widget to hold the line interaction tables used by 
    LineInfo which in turn is used by spectrum widget.

    """

    def __init__(self, line_interaction_analysis, atom_data, description):
        """Create the widget and set data."""
        super(LineInteractionTables, self).__init__()
        self.text_description = QtGui.QLabel(str(description))
        self.species_table = QtGui.QTableView()
        self.transitions_table = QtGui.QTableView()
        self.layout = QtGui.QHBoxLayout()
        self.line_interaction_analysis = line_interaction_analysis
        self.atom_data = atom_data
        line_interaction_species_group = \
        line_interaction_analysis.last_line_in.groupby(['atomic_number', 
            'ion_number'])
        self.species_selected = sorted(
            line_interaction_species_group.groups.keys())
        species_symbols = [util.species_tuple_to_string(item, 
            atom_data) for item in self.species_selected]
        species_table_model = SimpleTableModel([species_symbols, ['Species']])
        species_abundances = (
            line_interaction_species_group.wavelength.count().astype(float) /
            line_interaction_analysis.last_line_in.wavelength.count()).astype(float).tolist()
        species_abundances = map(float, species_abundances)
        species_table_model.addData(species_abundances)
        self.species_table.setModel(species_table_model)

        line_interaction_species_group.wavelength.count()
        self.layout.addWidget(self.text_description)
        self.layout.addWidget(self.species_table)
        self.species_table.connect(self.species_table.verticalHeader(), 
            QtCore.SIGNAL('sectionClicked(int)'), self.on_species_clicked)
        self.layout.addWidget(self.transitions_table)

        self.setLayout(self.layout)
        self.show()

    def on_species_clicked(self, index):
        """"""
        current_species = self.species_selected[index]
        last_line_in = self.line_interaction_analysis.last_line_in
        last_line_out = self.line_interaction_analysis.last_line_out

        last_line_in_filter = (last_line_in.atomic_number == current_species[0]).values & \
                              (last_line_in.ion_number == current_species[1]).values

        current_last_line_in = last_line_in[last_line_in_filter].reset_index()
        current_last_line_out = last_line_out[last_line_in_filter].reset_index()

        current_last_line_in['line_id_out'] = current_last_line_out['line_id']


        last_line_in_string = []
        last_line_count = []
        grouped_line_interactions = current_last_line_in.groupby(['line_id', 
            'line_id_out'])
        exc_deexc_string = 'exc. %d-%d (%.2f A) de-exc. %d-%d (%.2f A)'

        for line_id, row in grouped_line_interactions.wavelength.count().iteritems():
            current_line_in = self.atom_data.lines.ix[line_id[0]]
            current_line_out = self.atom_data.lines.ix[line_id[1]]
            last_line_in_string.append(exc_deexc_string % (
                current_line_in['level_number_lower'],
               current_line_in['level_number_upper'],
               current_line_in['wavelength'],
               current_line_out['level_number_upper'],
               current_line_out['level_number_lower'],
               current_line_out['wavelength']))
            last_line_count.append(int(row))


        last_line_in_model = SimpleTableModel([last_line_in_string, [
            'Num. pkts %d' % current_last_line_in.wavelength.count()]])
        last_line_in_model.addData(last_line_count)
        self.transitions_table.setModel(last_line_in_model)

class LineInfo(QtGui.QDialog):
    """Dialog to show the line info used by spectrum widget."""
    def __init__(self, parent, wavelength_start, wavelength_end):
        """Create the dialog and set data in it from the model. 
        Show widget."""
        super(LineInfo, self).__init__(parent)
        self.parent = parent
        self.setGeometry(180 + len(self.parent.line_info) * 20, 150, 250, 400)
        self.setWindowTitle('Line Interaction: %.2f - %.2f (A) ' % (
            wavelength_start, wavelength_end,))
        self.layout = QtGui.QVBoxLayout()
        packet_nu_line_interaction = analysis.LastLineInteraction.from_model(
            self.parent.model)
        packet_nu_line_interaction.packet_filter_mode = 'packet_nu'
        packet_nu_line_interaction.wavelength_start = wavelength_start * u.angstrom
        packet_nu_line_interaction.wavelength_end = wavelength_end * u.angstrom
        
        line_in_nu_line_interaction = analysis.LastLineInteraction.from_model(
            self.parent.model)
        line_in_nu_line_interaction.packet_filter_mode = 'line_in_nu'
        line_in_nu_line_interaction.wavelength_start = wavelength_start * u.angstrom
        line_in_nu_line_interaction.wavelength_end = wavelength_end * u.angstrom


        self.layout.addWidget(LineInteractionTables(packet_nu_line_interaction, 
            self.parent.model.atom_data, 'filtered by frequency of packet'))
        self.layout.addWidget(LineInteractionTables(line_in_nu_line_interaction, 
            self.parent.model.atom_data, 
            'filtered by frequency of line interaction'))

        self.setLayout(self.layout)
        self.show()

    def get_data(self, wavelength_start, wavelength_end):
        """Fetch line info data for the specified wavelength range 
        from the model and create ionstable.

        """
        self.wavelength_start = wavelength_start * u.angstrom
        self.wavelength_end = wavelength_end * u.angstrom
        last_line_in_ids, last_line_out_ids = analysis.get_last_line_interaction(
            self.wavelength_start, self.wavelength_end, self.parent.model)
        self.last_line_in, self.last_line_out = (
            self.parent.model.atom_data.lines.ix[last_line_in_ids], 
            self.parent.model.atom_data.lines.ix[last_line_out_ids])
        self.grouped_lines_in, self.grouped_lines_out = (self.last_line_in.groupby(
            ['atomic_number', 'ion_number']), 
        self.last_line_out.groupby(['atomic_number', 'ion_number']))
        self.ions_in, self.ions_out = (self.grouped_lines_in.groups.keys(), 
        self.grouped_lines_out.groups.keys())
        self.ions_in.sort()
        self.ions_out.sort()
        self.header_list = []
        self.ion_table = (self.grouped_lines_in.wavelength.count().astype(float) / 
            self.grouped_lines_in.wavelength.count().sum()).values.tolist()
        for z, ion in self.ions_in:
            self.header_list.append('Z = %d: Ion %d' % (z, ion))

    def get_transition_table(self, lines, atom, ion):
        """Called by the two methods below to get transition table for
        given lines, atom and ions.

        """
        grouped = lines.groupby(['atomic_number', 'ion_number'])
        transitions_with_duplicates = lines.ix[grouped.groups[(atom, ion)]
            ].groupby(['level_number_lower', 'level_number_upper']).groups
        transitions = lines.ix[grouped.groups[(atom, ion)]
            ].drop_duplicates().groupby(['level_number_lower', 
            'level_number_upper']).groups
        transitions_count = []
        transitions_parsed = []
        for item in transitions.values():
            c = 0
            for ditem in transitions_with_duplicates.values():
                c += ditem.count(item[0])
            transitions_count.append(c)
        s = 0
        for item in transitions_count:
            s += item
        for index in range(len(transitions_count)):
            transitions_count[index] /= float(s)
        for key, value in transitions.items():
            transitions_parsed.append("%d-%d (%.2f A)" % (key[0], key[1], 
                self.parent.model.atom_data.lines.ix[value[0]]['wavelength']))
        return transitions_parsed, transitions_count

    def on_atom_clicked(self, index):
        """Create and show transition table for the clicked item in the
        dialog created by the spectrum widget.

        """
        self.transitionsin_parsed, self.transitionsin_count = (
            self.get_transition_table(self.last_line_in, 
            self.ions_in[index][0], self.ions_in[index][1]))
        self.transitionsout_parsed, self.transitionsout_count = (
            self.get_transition_table(self.last_line_out, 
            self.ions_out[index][0], self.ions_out[index][1]))
        self.transitionsindata = SimpleTableModel([self.transitionsin_parsed, 
            ['Lines In']])
        self.transitionsoutdata = SimpleTableModel([self.transitionsout_parsed, 
            ['Lines Out']])
        self.transitionsindata.addData(self.transitionsin_count)
        self.transitionsoutdata.addData(self.transitionsout_count)
        self.transitionsintable.setModel(self.transitionsindata)
        self.transitionsouttable.setModel(self.transitionsoutdata)
        self.transitionsintable.show()
        self.transitionsouttable.show()
        self.setGeometry(180 + len(self.parent.line_info) * 20, 150, 750, 400)
        self.show()

    def on_atom_clicked2(self, index):
        """Create and show transition table for the clicked item in the
        dialog created by the spectrum widget.

        """
        self.transitionsin_parsed, self.transitionsin_count = (
            self.get_transition_table(self.last_line_in, self.ions_in[index][0], 
            self.ions_in[index][1]))
        self.transitionsout_parsed, self.transitionsout_count = (
            self.get_transition_table(self.last_line_out, 
            self.ions_out[index][0], self.ions_out[index][1]))
        self.transitionsindata = SimpleTableModel([self.transitionsin_parsed, 
            ['Lines In']])
        self.transitionsoutdata = SimpleTableModel([self.transitionsout_parsed,
            ['Lines Out']])
        self.transitionsindata.addData(self.transitionsin_count)
        self.transitionsoutdata.addData(self.transitionsout_count)
        self.transitionsintable2.setModel(self.transitionsindata)
        self.transitionsouttable2.setModel(self.transitionsoutdata)
        self.transitionsintable2.show()
        self.transitionsouttable2.show()
        self.setGeometry(180 + len(self.parent.line_info) * 20, 150, 750, 400)
        self.show()

class SimpleTableModel(QtCore.QAbstractTableModel):
    """Create a table data structure for the table widgets."""
    
    def __init__(self, headerdata=None, iterate_header=(0, 0), 
            index_info=None, parent=None, *args):
        """Call constructor of the QAbstractTableModel and set parameters
        given by user.
        """
        super(SimpleTableModel, self).__init__(parent, *args)
        self.headerdata = headerdata
        self.arraydata = []
        self.iterate_header = iterate_header
        self.index_info = index_info

    def addData(self, datain):
        """Add data to the model."""
        self.arraydata.append(datain)

    def rowCount(self, parent=QtCore.QModelIndex()):
        """Return number of rows."""
        return len(self.arraydata[0])

    def columnCount(self, parent=QtCore.QModelIndex()):
        """Return number of columns."""
        return len(self.arraydata)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """Set the header data."""
        if orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            if self.iterate_header[0] == 1:
                return self.headerdata[0][0] + str(section + 1)
            elif self.iterate_header[0] == 2:
                if self.index_info:
                    return self.headerdata[0][0] + str(self.index_info[section])
                else:
                    return self.headerdata[0][0] + str(section + 1)
            else:
                return self.headerdata[0][section]
        elif orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if self.iterate_header[1] == 1:
                return self.headerdata[1][0] + str(section + 1)
            elif self.iterate_header[1] == 2:
                if self.index_info:
                    return self.headerdata[1][0] + str(self.index_info[section])
            else:
                return self.headerdata[1][section]
        return None

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """Return data of specified index and role."""
        if not index.isValid():
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        return (self.arraydata[index.column()][index.row()])

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """Change the data in the model for specified index and role
        to specified value."""
        if not index.isValid():
            return False
        elif role != QtCore.Qt.EditRole:
            return False
        self.arraydata[index.column()][index.row()] = value
        self.emit(QtCore.SIGNAL(
            'dataChanged(const QModelIndex &, const QModelIndex &)'), 
            index, index)
        return True

    def updateTable(self):
        """Update table to set all the new data."""
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                index = self.createIndex(r, c)
                self.setData(index, self.arraydata[c][r])

class MatplotlibWidget(FigureCanvas):
    """Canvas to draw graphs on."""

    def __init__(self, parent, fig=None):
        """Create the canvas. Add toolbar depending on the parent."""
        self.parent = parent
        self.figure = Figure()#(frameon=False,facecolor=(1,1,1))
        self.cid = {}
        if fig != 'model':
            self.ax = self.figure.add_subplot(111)
        else:
            self.gs = gridspec.GridSpec(2, 1, height_ratios=[1, 3])
            self.ax1 = self.figure.add_subplot(self.gs[0])
            self.ax2 = self.figure.add_subplot(self.gs[1])#, aspect='equal')
        self.cb = None
        self.span = None

        super(MatplotlibWidget, self).__init__(self.figure)
        super(MatplotlibWidget, self).setSizePolicy(QtGui.QSizePolicy.Expanding, 
            QtGui.QSizePolicy.Expanding)
        super(MatplotlibWidget, self).updateGeometry()
        if fig != 'model':
            self.toolbar = NavigationToolbar(self, parent)
            self.cid[0] = self.figure.canvas.mpl_connect('pick_event', 
            self.on_span_pick)
        else:
            self.cid[0] = self.figure.canvas.mpl_connect('pick_event', 
                self.on_shell_pick)

    def show_line_info(self):
        """Show line info for span selected region."""
        self.parent.line_info.append(LineInfo(self.parent, self.span.xy[0][0], 
            self.span.xy[2][0]))

    def show_span(self, garbage=0, left=5000, right=10000):
        """Hide/Show/Change the buttons that show line info
        in spectrum plot widget.

        """
        if self.parent.spectrum_span_button.text() == 'Show Wavelength Range':
            if not self.span:
                self.span = self.ax.axvspan(left, right, color='r', alpha=0.3, 
                    picker=self.span_picker)
            else:
                self.span.set_visible(True)
            self.parent.spectrum_line_info_button.show()
            self.parent.spectrum_span_button.setText('Hide Wavelength Range')
        else:
            self.span.set_visible(False)
            self.parent.spectrum_line_info_button.hide()
            self.parent.spectrum_span_button.setText('Show Wavelength Range')
        self.draw()

    def on_span_pick(self, event):
        """Callback to 'pick'(grab with mouse) the span selector tool."""
        self.figure.canvas.mpl_disconnect(self.cid[0])
        self.span.set_edgecolor('m')
        self.span.set_linewidth(5)
        self.draw()
        if event.edge == 'left':
            self.cid[1] = self.figure.canvas.mpl_connect('motion_notify_event', 
                self.on_span_left_motion)
        elif event.edge == 'right':
            self.cid[1] = self.figure.canvas.mpl_connect('motion_notify_event', 
                self.on_span_right_motion)
        self.cid[2] = self.figure.canvas.mpl_connect('button_press_event', 
            self.on_span_resized)

    def on_span_left_motion(self, mouseevent):
        """Update data of span selector tool on left movement of mouse and
        redraw.

        """
        if mouseevent.xdata < self.span.xy[2][0]:
            self.span.xy[0][0] = mouseevent.xdata
            self.span.xy[1][0] = mouseevent.xdata
            self.span.xy[4][0] = mouseevent.xdata
            self.draw()

    def on_span_right_motion(self, mouseevent):
        """Update data of span selector tool on right movement of mouse and
        redraw.

        """
        if mouseevent.xdata > self.span.xy[0][0]:
            self.span.xy[2][0] = mouseevent.xdata
            self.span.xy[3][0] = mouseevent.xdata
            self.draw()

    def on_span_resized(self, mouseevent):
        """Redraw the red rectangle to currently selected span."""
        self.figure.canvas.mpl_disconnect(self.cid[1])
        self.figure.canvas.mpl_disconnect(self.cid[2])
        self.cid[0] = self.figure.canvas.mpl_connect('pick_event', 
            self.on_span_pick)
        self.span.set_edgecolor('r')
        self.span.set_linewidth(1)
        self.draw()

    def on_shell_pick(self, event):
        """Highlight the shell that was picked."""
        self.highlight_shell(event.artist.index)

    def highlight_shell(self, index):
        """Change edgecolor of highlighted shell."""
        self.parent.tableview.selectRow(index)
        for i in range(len(self.parent.shells)):
            if i != index and i != index + 1:
                self.parent.shells[i].set_edgecolor('k')
            else:
                self.parent.shells[i].set_edgecolor('w')
        self.draw()

    def shell_picker(self, shell, mouseevent):
        """Enable picking shells in the shell plot."""
        if mouseevent.xdata is None:
            return False, dict()
        mouse_r2 = mouseevent.xdata ** 2 + mouseevent.ydata ** 2
        if shell.r_inner ** 2 < mouse_r2 < shell.r_outer ** 2:
            return True, dict()
        return False, dict()

    def span_picker(self, span, mouseevent, tolerance=5):
        """Detect mouseclicks inside tolerance region of the span selector
        tool and pick it.

        """
        left = float(span.xy[0][0])
        right = float(span.xy[2][0])
        tolerance = span.axes.transData.inverted().transform((tolerance, 0)
            )[0] - span.axes.transData.inverted().transform((0, 0))[0]
        event_attributes = {'edge': None}
        if mouseevent.xdata is None:
            return False, event_attributes
        if left - tolerance <= mouseevent.xdata <= left + tolerance:
            event_attributes['edge'] = 'left'
            return True, event_attributes
        elif right - tolerance <= mouseevent.xdata <= right + tolerance:
            event_attributes['edge'] = 'right'
            return True, event_attributes
        return False, event_attributes

class Shell(matplotlib.patches.Wedge):
    """A data holder to store measurements of shells that will be drawn in 
    the plot.

    """
    def __init__(self, index, center, r_inner, r_outer, **kwargs):
        super(Shell, self).__init__(center, r_outer, 0, 90, 
            width=r_outer - r_inner, **kwargs)
        self.index = index
        self.center = center
        self.r_outer = r_outer
        self.r_inner = r_inner
        self.width = r_outer - r_inner