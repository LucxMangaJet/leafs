from pyforms.basewidget import BaseWidget
from pyforms.controls   import ControlFile
from pyforms.controls   import ControlLabel
from pyforms.controls   import ControlButton
from pyforms.controls   import ControlImage
from pyforms.controls   import ControlEmptyWidget
from pyforms.controls   import ControlCheckBox
from pyforms.controls   import ControlProgress
from AnyQt.QtWidgets import QFileDialog
import cv2
import time
import numpy as np

import cv2ops
import dataops
from data import Data, ActiveImageData, Config
from globals import *

class Leafz(BaseWidget):
    def __init__(self, *args, **kwargs):
        super().__init__('Leafz')

        #ui init
        self.info = ControlLabel("Info")
        self.prev = ControlButton("<")
        self.prev.value = self.onPrevClicked
        self.next = ControlButton(">")
        self.next.value = self.onNextClicked
        self.addLeaf = ControlButton("Apply")
        self.addLeaf.value = self.onActionClicked
        self.check = ControlCheckBox("Ready")
        self.check.changed_event = self.onCheckClicked
        self.dock = ControlEmptyWidget()

        self.formset = ["dock", ("info","check"), ("prev","addLeaf","next")]

        self.preview = ImagePreview(self.preview_onSelectSquare, self.preview_onRemoveLeaf)
        self.preview.parent = self
        self.dock.value = self.preview

        self.mainmenu = [
            {"File" : [
                {"Load": self.file_openClicked},
                {"Save": self.file_saveClicked},
                {"Save As": self.file_saveAsClicked},
                {"Export": self.file_exportClicked},
            ]},
            
            { "Edit" : [
                {"Order Leaves - Left to Right" : self.edit_order_leafs_lr},
                {"Order Leaves - Top to Bottom" : self.edit_order_leafs_td},
                {"Export Preview" : self.edit_exportPreviewClicked}
            ]},

            { "Actions" : [
                {"Run Auto on 10": self.data_run10Clicked},
                {"Run Auto on All": self.data_runAllClicked}
            ]}
        ]

        self.closeEvent = self.onClose
        #data init
        self.loadDataFromPath(g_config.lastFile)

    def onClose(self, sth):
        g_event_close.set()

    def loadDataFromPath(self, path):
        self.activeData = None
        with g_data_lock:
            global g_data
            g_data = Data(path)
            g_config.lastFile = path
        self.refresh()

    def preview_onSelectSquare(self, point):
        success = dataops.manual_select_square(self.activeData, point)
        if(success):
            self.save_and_refresh()
        pass

    def preview_onRemoveLeaf(self, point):
        success = dataops.manual_remove_leaf(self.activeData, point)
        if(success):
            self.save_and_refresh()
        pass

    def file_openClicked(self):
        file = self.selectFile()
        if file:
            self.loadDataFromPath(file)

    def file_saveClicked(self):
        file = g_config.lastFile
        if file and file[-5:] == ".json":
            with g_data_lock:
                g_data.saveToPath(file)
        else:
            self.file_saveAsClicked()
    
    def file_saveAsClicked(self):
        file = self.selectSaveFile()
        if file:
            with g_data_lock:
                g_data.saveToPath(file)
    
    def file_exportClicked(self):
        file = self.selectSaveFile()
        if file:
            with g_data_lock:
                g_data.exportAsCSV(file)

    def onActionClicked(self):
        dataops.run_auto_current(g_data)
        self.refresh()

    def onCheckClicked(self):
        self.activeData.isReady = self.check.value
        self.activeData.save(g_data)

    def selectFile(self):
        value = QFileDialog.getOpenFileName(self, "Load", "")[0]
        if len(value) == 0:
            return None
        return value

    def selectSaveFile(self):
        value,_ = QFileDialog.getSaveFileName(self, "Save", "")
        if len(value) == 0:
            return None
        return value

    def edit_order_leafs_td(self):
        dataops.reorder_leaves(self.activeData, False)
        self.save_and_refresh()

    def edit_order_leafs_lr(self):
        dataops.reorder_leaves(self.activeData, True)
        self.save_and_refresh()

    def save_and_refresh(self):
        self.activeData.save(g_data)
        self.refresh()

    def edit_exportPreviewClicked(self):
        file = self.selectSaveFile()
        if file:
            cv2.imwrite(file, self.preview.createPreviewFrom(self.activeData))

    def data_runAllClicked(self):
        dataops.run_auto_all(g_data)
        self.refresh()

    def data_run10Clicked(self):
        dataops.run_auto_10(g_data)
        self.refresh()

    def onPrevClicked(self):
        self.loadImageAtPosition(g_data.activeIndex-1)

    def onNextClicked(self):
        self.loadNextImage()

    def loadNextImage(self):
        self.loadImageAtPosition(g_data.activeIndex+1)

    def refresh(self):
        self.loadImageAtPosition(g_data.activeIndex)

    def loadImageAtPosition(self, position):
        if len(g_data.images) == 0:
            return

        if position >= len(g_data.images):
            position = 0
        elif position < 0:
            position = len(g_data.images)-1
        g_data.activeIndex = position

        self.activeData = ActiveImageData(g_data, g_data.activeIndex)
        self.preview.update(self.activeData)
        self.check.value = self.activeData.isReady
        self.updateInfo()

    def updateInfo(self):
        self.info.value = f"{g_data.activeIndex + 1}/{len(g_data.images)} \n {self.activeData.path}"


class ImagePreview(BaseWidget):
    def __init__(self, onSelectSquare, onRemoveLeaf):
        super().__init__("Preview")
        self._img = ControlImage()

        self.onSelectSquareCallback = onSelectSquare
        self.onRemoveLeafCallback = onRemoveLeaf

        self._img.add_popup_menu_option("Remove Leaf", self.onRemoveLeaf)
        self._img.add_popup_menu_option("Select Square", self.onSelectSquare)

        self._imgDebug0 = ControlImage()
        self._imgDebug1 = ControlImage()
        self._imgDebug2 = ControlImage()
        self._imgDebug3 = ControlImage()

        self._imgDebug0.hide()
        self._imgDebug1.hide()
        self._imgDebug2.hide()
        self._imgDebug3.hide()

        self.formset = ["_img", ("_imgDebug0", "_imgDebug1"),("_imgDebug2", "_imgDebug3")]
    
    def onSelectSquare(self):
        self.onSelectSquareCallback(self.get_mouse_point())

    def get_mouse_point(self):
        p = self._img._imageWidget._get_current_mouse_point()
        return p
 
    def onRemoveLeaf(self):
        self.onRemoveLeafCallback(self.get_mouse_point())
        pass

    def update(self, data):
        if data.source is None:
            image = g_fallbackImg
        else:
            image = self.createPreviewFrom(data)
        self._img.value = image

        if hasattr(data,"debug0"):
            self._imgDebug0.value = data.debug0
            self._imgDebug0.show()
        else:
            self._imgDebug0.hide()

        if hasattr(data, "debug1"):
            self._imgDebug1.value = data.debug1
            self._imgDebug1.show()
        else:
            self._imgDebug1.hide()

        if hasattr(data, "debug2"):
            self._imgDebug2.value = data.debug2
            self._imgDebug2.show()
        else:
            self._imgDebug2.hide()

        if hasattr(data, "debug3"):
            self._imgDebug3.value = data.debug3
            self._imgDebug3.show()
        else:
            self._imgDebug3.hide()


    def createPreviewFrom(self,data):
        base = data.source_resized
        preview = cv2ops.create_preview_mask(base, data.leaves,data.square)
        return preview

if __name__ == '__main__':

    from pyforms import start_app

    g_config = Config.load()
    start_app(Leafz, geometry=(100, 100, 640, 520))
    g_config.save()