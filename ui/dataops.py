import cv2ops
from data import Data, ActiveImageData
from globals import *

def reorder_leaves(active_data, use_lr):
    indx = 1
    if use_lr:
        indx = 0
    active_data.leaves.sort(key = lambda x:cv2ops.contour_center(x.contour)[indx])


def run_auto_on_count(data, start,count):
    with g_data_lock:
        for x in range(count):
            index = start + x
            if g_event_close.is_set():
                return
            print(index)
            imgData = ActiveImageData(data, index)
            img = imgData.source_resized

            if img is None:
                continue

            square,leaves = cv2ops.find_all_in_RGB(img,0)
            imgData.leaves = leaves
            imgData.square = square
            reorder_leaves(imgData, True)
            imgData.save(data)
            
            #progress.value = float(x)/count * 100
        print ("done")

def run_auto_all(data):
    run_auto_on_count(data, 0, len(data.images))

def run_auto_10(data):
    dif = len(data.images) - data.activeIndex
    run_auto_on_count(data, max(0,data.activeIndex), min(10, dif))

def run_auto_current(data):
    if data.activeIndex >= 0:
        run_auto_on_count(data, data.activeIndex,1)

def manual_select_square(activeData, point):
    for x in range(len(activeData.leaves)):
        if(cv2ops.point_inside_contour(activeData.leaves[x].contour,point)):
            activeData.square = cv2.minAreaRect(activeData.leaves[x].contour)            
            del activeData.leaves[x]
            return True
    return False

def manual_remove_leaf(activeData, point):
    for x in range(len(activeData.leaves)):
        if(cv2ops.point_inside_contour(activeData.leaves[x].contour,point)):
            del activeData.leaves[x]
            return True
    return False