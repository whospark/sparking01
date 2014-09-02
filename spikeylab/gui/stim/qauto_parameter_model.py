from PyQt4 import QtCore, QtGui
import numpy as np

from spikeylab.gui.stim.selectionmodel import ComponentSelectionModel
from spikeylab.gui.abstract_drag_view import AbstractDragView
from spikeylab.stim.auto_parameter_model import AutoParameterModel

ERRCELL = QtGui.QColor('firebrick')

class QAutoParameterModel(QtCore.QAbstractTableModel):
    SelectionModelRole = 34
    emptied = QtCore.pyqtSignal(bool)
    hintRequested = QtCore.pyqtSignal(str)
    countChanged = QtCore.pyqtSignal()
    def __init__(self, model):
        super(QAutoParameterModel, self).__init__()
        self.model = model
        self._selectionmap = {}

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.model.header(section)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return self.model.nrows()

    def columnCount(self, parent=QtCore.QModelIndex()):
        return self.model.ncols()

    def clearParameters(self):
        self.beginRemoveRows(QtCore.QModelIndex(), 0, self.rowCount())
        self.model.clear_parameters()
        self.endRemoveRows()

    def data(self, index, role=QtCore.Qt.UserRole):
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            row = index.row()
            field = self.model.header(index.column())
            return self.model.scaledValue(row, field)
        elif role == QtCore.Qt.ToolTipRole:
            if 1 <= index.column() <= 3:
                label = self.model.getDetail(index.row(), 'label')
                return label
        elif role == QtCore.Qt.ForegroundRole:
            # color the background red for bad values
            if not self.checkValidCell(index):
                return QtGui.QBrush(ERRCELL)
        elif role == QtCore.Qt.FontRole:
            # color the background red for bad values
            if not self.checkValidCell(index):
                f = QtGui.QFont()
                f.setWeight(QtGui.QFont.Bold)
                return f

        elif role == QtCore.Qt.UserRole or role == AbstractDragView.DragRole:  #return the whole python object
            param = self.model.param(index.row())
            for comp in param['selection']:
                comp.clean()
            return param

        elif role == self.SelectionModelRole:
            # may need to translate to QModelIndexes
            return self.model.selection(self.model.param(index.row()))

    def setData(self, index, value, role=QtCore.Qt.UserRole):
        if role == QtCore.Qt.EditRole:
            if isinstance(value, QtCore.QVariant):
                value = value.toPyObject()
            elif isinstance(value, QtCore.QString):
                value = str(value)
            self.model.setScaledValue(index.row(), self.model.header(index.column()), value)
            self.countChanged.emit()
        elif role == QtCore.Qt.UserRole:
            print "replace all values"
            row = index.row()
            if row == -1:
                row = self.rowCount() -1
            self.model.overwriteParam(row, value)
        return True

    def checkValidCell(self, index):
        col = index.column()
        row = index.row()
        return self.model.isFieldValid(row, self.model.header(col))

    def findFileParam(self, comp):
        return self.model.findFileParam(comp)

    def setParameterList(self, paramlist):
        self._parameters = paramlist

    def insertRows(self, position, rows, parent = QtCore.QModelIndex()):
        self.beginInsertRows(parent, position, position + rows - 1)
        for i in range(rows):
            self.model.insertRow(position)
            # self._selectionmap[self._paramid].hintRequested.connect(self.hintRequested)
        self.endInsertRows()
        if self.rowCount() == 1:
            self.emptied.emit(False)
        return True

    def removeRows(self, position, rows, parent = QtCore.QModelIndex()):
        self.beginRemoveRows(parent, position, position + rows - 1)
        for i in range(rows):
            self.model.removeRow(position)
            # cannot purge selection model, or else we have no way of 
            # recovering it when reordering
        self.endRemoveRows()
        if self.rowCount() == 0:
            self.emptied.emit(True)
        return True

    def removeItem(self, index):
        self.removeRows(index.row(), 1)

    def insertItem(self, index, item):
        """For reorder only, item must already have selectionModel in
        for its id"""
        row = index.row()
        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        self.model.insertRow(row)
        self.endInsertRows()
        self.model.overwriteParam(index.row(), item)

    def flags(self, index):
        if index.isValid():
            if self.model.editableRow(index.row()) and index.column() < 4:
                return QtCore.Qt.ItemIsDragEnabled | \
                       QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | \
                       QtCore.Qt.ItemIsEditable
            else:
                return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        else:
            print 'flags: index invalid'

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def toggleSelection(self, index, comp):
        self.model.toggleSelection(index.row(), comp)

    def selection(self, index):
        """
        Return the selected Indexes for the given parameter
        """
        return self.model.selection(index.row())

    def selectedParameterTypes(self, index):
        return self.model.selectedParameterTypes(index.row())

    def fileParameter(self, comp):
        return self.model.fileParameter(comp)

    def verify(self):
        return self.model.verify()