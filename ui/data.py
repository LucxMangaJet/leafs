import csv
import os
import cv2ops
import cv2
import numpy as np
import jsonpickle
g_debug = True
g_resizeRate = 1


class Config():
    fileName = "config.json"
    def __init__(self) -> None:
        self.lastFile = None
        pass

    def path():
        return os.path.dirname(os.path.realpath(__file__)) + os.path.sep + Config.fileName

    def load():
        path = Config.path()
        try:
            with open (path, "r") as f:
                text = f.read()
                result = jsonpickle.decode(text)
                print (f"Load from {path} successful")
                return result
        except FileNotFoundError:
            return Config()

    def save(self):
        path = Config.path()
        with open (path, "w") as f:
            data = self
            json = jsonpickle.encode(data)
            f.write(json)
            print (f"Save to {path} successful")

class Leaf():
    def __init__(self, _contour) -> None:
        self.contour = _contour
        self.holes = None

class DataEntry():
    def __init__(self, _path) -> None:
        self.path = _path
        self.leaves = []
        self.square = None
        self.isReady = False
        pass

class Data():
    def __init__(self, path) -> None:
        self.images = []
        self.activeIndex = -1

        if path is None or not os.path.exists(path):
            return

        _, file_extension = os.path.splitext(path)

        if file_extension == ".csv":
            self.loadFromCSV(path)
        elif file_extension == ".json":
            loaded = Data.loadFromJson(path)
            self.__dict__.update(loaded.__dict__)

    def loadFromCSV(self, path):
        with open(path, "r", newline="") as input_csv:
            csv_reader = csv.reader(input_csv, delimiter=',')
            next(csv_reader)
            for row in csv_reader:
                if row[4] == "duplicate":
                    continue
            
                for x in range(int(row[4])):
                    content = row[5+x]
                    if content == "file not found":
                        continue

                    entry = DataEntry(content)
                    self.images.append(entry)

            self.activeIndex = 0

    def loadFromJson(path):
        with open (path, "r") as f:
            text = f.read()
            result = jsonpickle.decode(text)
            #if not hasattr(self,"activeIndex"):
            #    self.activeIndex = -1
            print (f"Load from {path} successful")
            return result

    def saveToPath(self, path):
        with open (path, "w") as f:
            data = self
            json = jsonpickle.encode(data)
            f.write(json)
            print (f"Save to {path} successful")

    def exportAsCSV(self, path):
        with open(path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile, delimiter= ",")
            writer.writerow(["File Name", "File Path", "Status", "Leaf Count", "Square Pixel Size", "Square Position",
                             "Leaf ID", "Leaf Size cm2", "Leaf Size PX", "Leaf Position"])

            for i in range(len(self.images)):
                entry = self.images[i]
                

                filePath = entry.path
                fileName = os.path.splitext(os.path.basename(filePath))[0]
                leafCount = len(entry.leaves)
                square = entry.square #[position, size, angle]
                status = "Ready"
                if not entry.isReady:
                    status = "Not Ready"

                row = [fileName, filePath, status]
                
                if entry.isReady:
                    row.append(leafCount)
                    squareArea = None
                    if square is not None:
                        squareSize = square[1]
                        squareArea = squareSize[0]*squareSize[1]
                        row.append(squareArea)
                        row.append(square[0])
                
                writer.writerow(row)

                if not entry.isReady:
                    continue

                leaves = entry.leaves
                for j in range(len(leaves)):
                    leaf = leaves[j]
                    area = None
                    pxArea = cv2.contourArea(leaf.contour)

                    #remove holes
                    if leaf.holes:
                        for x in leaf.holes:
                            pxArea -= cv2.contourArea(x)

                    if squareArea is not None:
                        area = pxArea/squareArea
                    x,y,w,h =  cv2.boundingRect(leaf.contour)
                    row = ["","","","","","",j,"{:.2f}".format(area), pxArea, [x,y]]
                    writer.writerow(row)

        print (f"Export to {path} successful")


class ActiveImageData():
        def __init__(self, data, index):
            self.index = index
            entry =data.images[index]
            self.path = entry.path
            self.isReady = entry.isReady

            if self.path is None or self.path == "file not found":
                source = None
            else:
                source = cv2.imread(self.path.replace('\\','/'))
            self.source = source
            if source is not None:
                self.source_resized = cv2ops.resize_img(self.source, g_resizeRate)
                if g_debug:
                    self.debug0 = cv2ops.create_debug0(self.source_resized)
                    #self.debug1 = cv2ops.create_debug1(self.source_resized)
                    #self.debug2 = cv2ops.create_debug2(self.source_resized)
                    #self.debug3 = cv2ops.create_debug3(self.source_resized)
            else:
                self.source_resized = None

            self.leaves = entry.leaves
            self.square = entry.square

        def save(self, data):
            index = self.index
            entry = data.images[index]
            entry.path = self.path
            entry.leaves = self.leaves
            entry.isReady = self.isReady

            if self.square is not None:
                entry.square = self.square
            else:
                entry.square = None