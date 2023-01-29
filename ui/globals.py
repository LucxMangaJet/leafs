from data import Data
import threading
import cv2
import os

g_fileDir = os.path.dirname(os.path.realpath(__file__))
g_fallbackImg =  cv2.imread( g_fileDir + "/empty.jpg")
g_data = Data(None)
g_config = None
g_data_lock = threading.Lock()
g_event_close = threading.Event()