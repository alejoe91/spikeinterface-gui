from .myqt import QT
import pyqtgraph as pg

import numpy as np
import itertools

from .base import WidgetBase
from .tools import ParamDialog, get_dict_from_group_param, CustomItem


class CurationView(WidgetBase):
    """
    """

    _need_compute = False

    def __init__(self, controller=None, parent=None):
        WidgetBase.__init__(self, parent=parent, controller=controller)

        self.merge_info = {}
        self.layout = QT.QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(QT.QLabel("Merge"))
        self.table_merge = QT.QTableWidget(selectionMode=QT.QAbstractItemView.SingleSelection,
                                     selectionBehavior=QT.QAbstractItemView.SelectRows)
        # self.table_merge.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.layout.addWidget(self.table_merge)
        # self.table.itemSelectionChanged.connect(self.on_item_selection_changed)


        self.layout.addWidget(QT.QLabel("Delete"))
        self.table_delete = QT.QTableWidget(selectionMode=QT.QAbstractItemView.SingleSelection,
                                     selectionBehavior=QT.QAbstractItemView.SelectRows)
        # self.table_delete.setContextMenuPolicy(QT.Qt.CustomContextMenu)
        self.layout.addWidget(self.table_delete)


        self.refresh()

    def _refresh(self):
        print("curation refresh")
        print(self.controller.manual_curation_data)
        # Merged
        merged_units = self.controller.manual_curation_data["merged_unit_groups"]
        self.table_merge.clear()
        self.table_merge.setRowCount(len(merged_units))
        self.table_merge.setColumnCount(1)
        self.table_merge.setHorizontalHeaderLabels(["Merged groups"])
        self.table_merge.setSortingEnabled(False)
        for ix, group in enumerate(merged_units):
            item = QT.QTableWidgetItem(str(group))
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table_merge.setItem(ix, 0, item)

        ## deleted        
        removed_units = self.controller.manual_curation_data["removed_units"]
        self.table_delete.clear()
        self.table_delete.setRowCount(len(removed_units))
        self.table_delete.setColumnCount(1)
        self.table_delete.setHorizontalHeaderLabels(["unit_id"])
        self.table_delete.setSortingEnabled(False)
        for i, unit_id in enumerate(removed_units):
            color = self.controller.qcolors.get(unit_id, QT.QColor( 'black'))
            pix = QT.QPixmap(16,16)
            pix.fill(color)
            icon = QT.QIcon(pix)
            item = QT.QTableWidgetItem( f'{unit_id}')
            item.setFlags(QT.Qt.ItemIsEnabled|QT.Qt.ItemIsSelectable)
            self.table_delete.setItem(i,0, item)
            item.setIcon(icon)


    def on_manual_curation_updated(self):
        self._refresh()


CurationView._gui_help_txt = """
"""
