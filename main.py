import os, sys
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox
from glob import glob
import pprint


class MainGUI(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self.master = master
        self.master.title("sample")
        self.grid(row=0, column=0)

        self.imgList = []
        self.nowImg = 0

        self.canvasWidth = 800
        self.canvasHeight = 450

        self.imgWidthGain = 1
        self.imgHeightGain = 1

        self.mouseMovedFlag = False
        self.mousePoint = []
        self.mousePointList = []

        self.drawRectangles = [[]]

        self.resultFile = "/result.txt"
        self.result = {}

        self.createWidgets()

    def createWidgets(self):
        self.initSetting()
        self.initCanvas()

    def initSetting(self):
        propertyFrame = tk.LabelFrame(self.master, text="設定")
        propertyFrame.grid(row=0, column=0)

        self.imgFolderVar = tk.StringVar()
        tk.Label(propertyFrame, text="画像フォルダ：").grid(row=0, column=0)
        imgFolderEntry = tk.Entry(propertyFrame, width=20, textvariable=self.imgFolderVar)
        imgFolderEntry.grid(row=0, column=1)

        tk.Button(propertyFrame, text="参照", command=self.getImgDirectory).grid(row=0, column=2)

        self.imgFrame = tk.LabelFrame(self.master, text="画像")
        self.imgFrame.grid(row=0, column=1)

    def initCanvas(self):
        self.imgNameVar = tk.StringVar()
        if len(self.imgList) != 0:
            self.imgNameVar.set(self.imgList[self.nowImg])
        else:
            self.imgNameVar.set("ここに表示している画像名が表示されます")

        tk.Label(self.imgFrame,
                 textvariable=self.imgNameVar).grid(row=0, column=0, columnspan=4)

        tk.Button(self.imgFrame, text="前の画像", command=self.getBeforeImg).grid(row=1, column=0)
        tk.Button(self.imgFrame, text="次の画像", command=self.getAfterImg).grid(row=1, column=1)

        self.imgCanvas = tk.Canvas(self.imgFrame, bg="white", width=800, height=450)
        self.imgCanvas.grid(row=10, column=0)

        imgText = self.imgCanvas.create_text(400, 201, text="画像フォルダを設定してください", font=("", 24))
        self.imgCanvas.create_rectangle(self.imgCanvas.bbox(imgText))

        self.imgCanvas.bind("<ButtonPress-1>", self.mousePressed)
        self.imgCanvas.bind("<B1-Motion>", self.mouseMoved)
        self.imgCanvas.bind("<ButtonRelease-1>", self.mouseReleased)

        tk.Button(self.imgFrame, text="四角を全て削除", command=self.rectDeleteAll).grid(row=11, column=0)
        tk.Button(self.imgFrame, text="最後に描いた四角を削除", command=self.rectDeleteLast).grid(row=11, column=1)

    def setImage(self, imgPath):
        read_img = Image.open(imgPath)

        self.imgWidthGain = self.canvasWidth / read_img.width
        self.imgHeightGain = self.canvasHeight / read_img.height

        read_img = read_img.resize((int(read_img.width * self.imgWidthGain), int(read_img.height * self.imgHeightGain)))

        img = ImageTk.PhotoImage(image=read_img)
        self.imgCanvas.photo = img
        self.imgCanvas.create_image(0, 0, anchor="nw", image=self.imgCanvas.photo)

    def getImgDirectory(self):
        initDir = os.path.abspath(os.path.dirname(__file__))
        filePath = filedialog.askdirectory(initialdir=initDir)
        self.imgFolderVar.set(filePath)

        self.imgList = glob(filePath + "/*.jpg")
        self.imgList += glob(filePath + "/*.png")
        self.nowImg = 0

        if self.imgList == []:
            return

        self.imgNameVar.set(self.imgList[self.nowImg])
        self.setImage(self.imgList[self.nowImg])

        self.drawRectangles = [[]]
        self.mousePointList = []
        self.result = {}

    def getBeforeImg(self):
        self.resultOutput()

        if self.imgList == []:
            messagebox.showwarning("エラー", "画像フォルダを設定してください")
            return

        if self.nowImg != 0:
            self.nowImg -= 1
            self.imgNameVar.set(self.imgList[self.nowImg])
            self.setImage(self.imgList[self.nowImg])
        else:
            messagebox.showwarning("エラー", "この画像が最初の１枚です")

        self.drawRectangles = [[]]
        self.mousePointList = []

    def getAfterImg(self):
        self.resultOutput()

        if self.imgList == []:
            messagebox.showwarning("エラー", "画像フォルダを設定してください")
            return

        if self.nowImg != (len(self.imgList) - 1):
            self.nowImg += 1
            self.imgNameVar.set(self.imgList[self.nowImg])
            self.setImage(self.imgList[self.nowImg])
        else:
            messagebox.showwarning("エラー", "この画像が最後の１枚です")

        self.drawRectangles = [[]]
        self.mousePointList = []

    def resultOutput(self):
        if self.imgFolderVar.get() == "":
            return

        print("drs:", self.drawRectangles)
        print("mpl:", self.mousePointList)

        with open(self.imgFolderVar.get() + self.resultFile, "w") as f:
            for k, v in self.result.items():
                if v != [[]]:
                    # 画像名、矩形の番号（1～）、x0,、y0、x1、y1
                    c = 1
                    for _v in v:
                        f.write(("{} {} {} {} {} {}\n").format(k, c,
                                                               int(_v[0] / self.imgWidthGain),
                                                               int(_v[1] / self.imgHeightGain),
                                                               int(_v[2] / self.imgWidthGain),
                                                               int(_v[3] / self.imgHeightGain)))
                        c += 1

    def mousePressed(self, event):
        mx = event.x
        my = event.y
        self.mousePoint = [mx, my, mx, my]
        self.mouseMovedFlag = True

    def mouseMoved(self, event):
        if self.mouseMovedFlag:
            mx = event.x
            my = event.y
            self.mousePoint[2] = mx
            self.mousePoint[3] = my

            if len(self.drawRectangles[-1]) > 0:
                self.imgCanvas.delete(self.drawRectangles[-1][-1])

            rect = self.imgCanvas.create_rectangle(self.mousePoint)

            self.drawRectangles[-1].append(rect)

    def mouseReleased(self, event):
        self.mouseMovedFlag = False

        self.mousePointList.append(self.mousePoint)
        self.drawRectangles[-1] = [self.drawRectangles[-1][-1]]
        self.drawRectangles.append([])

        if self.imgList == []:
            return

        self.result[self.imgList[self.nowImg]] = self.mousePointList
        # pprint.pprint(self.result)

    def rectDeleteAll(self):
        if self.drawRectangles == [[]]:
            return

        [self.imgCanvas.delete(i[0]) for i in self.drawRectangles[:-1]]

        self.drawRectangles = [[]]
        self.mousePoint = []
        self.mousePointList = []

    def rectDeleteLast(self):
        if self.drawRectangles == [[]]:
            return

        self.imgCanvas.delete(self.drawRectangles[-2][0])
        self.drawRectangles = self.drawRectangles[:-1]
        self.mousePointList = self.mousePointList[:-1]


root = tk.Tk()
app = MainGUI(master=root)
app.mainloop()
