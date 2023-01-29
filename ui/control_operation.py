from pyforms.basewidget import BaseWidget
from pyforms.controls   import ControlProgress
import cv2
import numpy as np
import cv2ops

import threading
from globals import *


class ThreadedOperationWidget(BaseWidget):
    def __init__(self):
        super().__init__("Unnamed")
        self.progress = ControlProgress()
    
    def run(self, name, method):
        self.title = name
        self.show()
        self.thread = threading.Thread(target=method, args=[self.progress])
        self.thread.start()