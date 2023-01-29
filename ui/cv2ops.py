import cv2
import numpy as np
from data import Leaf

def resize_img(img, percent):
    if img is None:
        return None

    dim = (int(img.shape[1] * percent), int(img.shape[0] * percent))
    return cv2.resize(img, dim, interpolation = cv2.INTER_AREA)

def point_inside_contour(contour, point):
    return cv2.pointPolygonTest(contour, point, False) >= 0 

def find_square_rect_in_contours(contours):
    max_rect = None
    max_proportion = 0
    max_idx = -1

    for idx in range(len(contours)):
        x = contours[idx]
        if x is None:
            continue
        rect = cv2.minAreaRect(x)
        rect_size = rect[1] #[position, size, angle]
        
        if  rect_size[0] <= rect_size[1]:
            squaredness_score =rect_size[0]/rect_size[1]
        else:
            squaredness_score =rect_size[1]/rect_size[0]

        if squaredness_score < 0.8:
            continue
        
        
        rect_area = rect_size[0]*rect_size[1]
        area = cv2.contourArea(x)
        fill_score = area/rect_area
        
        prop = fill_score * squaredness_score
    
    #find the squarest contour min area rect
        if(prop > max_proportion):
            max_proportion = prop
            max_rect = rect
            max_idx = idx
    return max_idx, max_rect

def find_leaves_contours_in_GRAY(_image):

    if cv2.getVersionMajor() in [2, 4]:
    # OpenCV 2, OpenCV 4 case
        contours, hierarchy = cv2.findContours(_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    else:
    # OpenCV 3 case
        _, contours, hierarchy = cv2.findContours(_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    fitting_size = filter_contours(_image,contours)
    return fitting_size, hierarchy

def filter_contours(_image, _contours):
    out = []
    img_area = _image.shape[0]*_image.shape[1]
    for idx in range(len(_contours)):
        x = _contours[idx]
        area = cv2.contourArea(x)
        area_percent = area/img_area
        if  area_percent < 0.0001 or area_percent > 0.5:
            out.append(None)
        else:
            out.append(x)
    return out

def generate_mask_from_leaves(image_source, leaves, color_primary, color_secondary):
    image_mask = np.zeros(image_source.shape, dtype='uint8')
    for x in range(len(leaves)):
        cv2.drawContours(image_mask,[leaves[x].contour],0, color_primary,15)
        holes = leaves[x].holes
        if holes:
            for hole in holes:
                cv2.drawContours(image_mask,[hole],0, color_secondary,15)

    return image_mask

def generate_mask_from_rect(image_source, rect, color):
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    image_mask = np.zeros(image_source.shape, dtype='uint8')
    cv2.drawContours(image_mask,[box],0, color,15)

    return image_mask

def find_contour_containing(contours, point):
    for x in range(len(contours)):
        if cv2.pointPolygonTest(contours[x], point, False) >= 0:
            return x
    return -1


def add_text(image, org, color, text):
    font = cv2.FONT_HERSHEY_SIMPLEX
    return cv2.putText(image, text, org, font, 2, color, 3, cv2.LINE_AA)


def contour_center(contour):
    M = cv2.moments(contour)
    x = int(M["m10"] / M["m00"])
    y = int(M["m01"] / M["m00"])
    return (x, y)

def rect_center(rect):
     return (int(rect[0][0]),int(rect[0][1])) #[position, size, angle]

def create_preview_mask(source, leaves, square):
    leaf_mask = generate_mask_from_leaves(source, leaves, (255,0,0), (255,255,0))
    square_mask = generate_mask_from_rect(source, square, (0,0,255))
    res = cv2.add(source, leaf_mask)
    res = cv2.add(res,square_mask)

    #if square is not None:
    #    res = add_text(res, rect_center(square), (0,0,255),"Square")

    for x in range(len(leaves)):
        leaf = leaves[x].contour
        res = add_text(res, contour_center(leaf), (255,255,255),str(x))

    return res

def create_debug0(source):
    image_gray = cv2.cvtColor(source, cv2.COLOR_RGB2GRAY)
    ret,image_otsu = cv2.threshold(image_gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    return image_otsu

def create_debug1(source):
    image_gray = cv2.cvtColor(source, cv2.COLOR_RGB2GRAY)
    smooth = cv2.GaussianBlur(image_gray, (33,33), 0)
    division = cv2.divide(image_gray, smooth, scale=192)
    return division

def gamma_transform(img, gamma, darkness):
    gamma_table=[np.power(max(0, x/255.0 - darkness),gamma)*255.0 for x in range(256)]
    gamma_table=np.round(np.array(gamma_table)).astype(np.uint8)
    return cv2.LUT(img,gamma_table)

def create_debug2(source):
    image_gray = cv2.cvtColor(source, cv2.COLOR_RGB2GRAY)
    image_gamma_correct=gamma_transform(image_gray,0.1,0)
    return image_gamma_correct

def create_debug3(source):
    ret,image_otsu = cv2.threshold(create_debug2(source),0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    return image_otsu

def filter_holes_in_leaves(contours, hierarchy):
    out_leaves = []
    map = {}
    indx = 0

    # first pass, collect leaves
    for x in range(len(contours)):
        if contours[x] is None:
            continue

        parent = hierarchy[0,x,3]
        if parent == -1 or contours[parent] is None: #parent info
            leaf = Leaf(contours[x])
            out_leaves.append(leaf)
            map[x] = indx
            indx +=1

    #second pass, match holes
    for x in range(len(contours)):
        if contours[x] is None:
            continue

        parent = hierarchy[0,x,3]
        if parent != -1 and contours[parent] is not None: 
            #parent is leaf
            if parent in map:
                leaf = out_leaves[map[parent]]
                if leaf.holes is None:
                    leaf.holes = []
                leaf.holes.append(contours[x])
            else:
                #contour is not direct child of leaf
                pass
            
    return out_leaves

def mean_color_of_contour(source,gray, contour):
    if contour is None:
        return cv2.mean(source)

    mask = np.zeros(gray.shape, np.uint8)
    cv2.drawContours(mask, contour, -1, 255, -1)
    return cv2.mean(source, mask=mask)

def leaf_passes_checks(source, image_gray, leaf):

    color = mean_color_of_contour(source,image_gray, leaf.contour)
    #main color should be green
    if color[1] < color[0] or color[1] < color[2]:
        return False

    return True

def find_all_in_RGB(source, threshold_offset):
    image_gray = cv2.cvtColor(source, cv2.COLOR_RGB2GRAY)
    ret,image_otsu = cv2.threshold(image_gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    #apply threshold offset if defined
    if threshold_offset != 0:
        ret,image_otsu = cv2.threshold(image_gray,ret + threshold_offset,255,cv2.THRESH_BINARY)

    contours, hierarchy = find_leaves_contours_in_GRAY(image_otsu)
    idx, square = find_square_rect_in_contours(contours)

    #remove square from leaves
    if idx >= 0:
        contours[idx] = None

    leaves = filter_holes_in_leaves(contours, hierarchy)  

    leaves[:] = [x for x in leaves if leaf_passes_checks(source, image_gray, x)]
    
    return square, leaves