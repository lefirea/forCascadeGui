import os, sys
import json, copy
import cv2
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.simpledialog import askstring
from glob import glob
from PIL import Image, ImageTk
import pprint


class MainGUI(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)

        # ウィンドウ本体
        self.master = master
        self.master.title("sample")
        self.grid(row=0, column=0)

        # フォルダの中の画像のリスト
        self.imgList = []  # ファイルパスを保持
        self.nowImg = 0  # 今何枚目の画像か

        # 画像を表示するキャンバスのサイズ
        self.canvasWidth = 800
        self.canvasHeight = 450

        # 読み込んだ画像をキャンバスのサイズにするための倍率
        # 設定した枠の座標を元画像の座標位置に直すのにも使う
        self.imgWidthGain = {}
        self.imgHeightGain = {}

        # 枠付けに関する情報
        self.mouseMovedFlag = False  # マウスが動いてるかどうか（多分使わなくても良い）（そのうち消す）
        self.mousePoint = []  # 今のマウスの座標（左上ｘ、左上ｙ、右下ｘ、右下ｙ）
        self.mousePointList = []  # 描画した枠の座標

        # 描画した枠の情報
        # 削除したりするのに使う
        self.drawRectangles = [[]]
        self.drawTexts = []

        # 枠付けの結果を出力するファイル名
        # OpenCVのカスケード作成を想定した記述をする
        self.resultFile = "/result.txt"
        self.resultJson = "/result.json"
        self.result = {}  # 出力するデータを辞書型で保持

        # ウィジェット配置
        self.createWidgets()

    def createWidgets(self):
        self.initSetting()  # 読み込むフォルダとかの設定ウィジェットを配置
        self.initCanvas()  # キャンバスを配置

    def initSetting(self):
        # 設定のラベルフレーム作成
        propertyFrame = tk.LabelFrame(self.master, text="設定")
        propertyFrame.grid(row=0, column=0)

        # 処理する画像フォルダの読み込み
        self.imgFolderVar = tk.StringVar()  # フォルダパスが入る
        tk.Label(propertyFrame, text="画像フォルダ：").grid(row=0, column=0)
        imgFolderEntry = tk.Entry(propertyFrame, width=20, textvariable=self.imgFolderVar)  # フォルダパスが入力される
        imgFolderEntry.grid(row=0, column=1)

        # 検索ボタン
        tk.Button(propertyFrame, text="参照", command=self.getImgDirectory).grid(row=0, column=2)

        # 枠の線の太さを変えられるように
        tk.Label(propertyFrame, text="線の太さ：").grid(row=1, column=0, sticky=tk.E)
        self.lineWidth = tk.StringVar()
        self.lineWidth.set("1")  # 初期値は１
        tk.Entry(propertyFrame, width=10, textvariable=self.lineWidth).grid(row=1, column=1, sticky=tk.W)

        # 線と文字の色を変えられるように
        colors = ["black", "white", "red", "green", "blue", "cyan", "yellow", "magenta"]
        tk.Label(propertyFrame, text="線と文字の色：").grid(row=2, column=0, sticky=tk.E)
        self.lineColor = tk.StringVar()
        cb = ttk.Combobox(propertyFrame, textvariable=self.lineColor, values=colors, width=10)
        cb.grid(row=2, column=1, sticky=tk.W)
        cb.set(colors[0])

        # キャンバス用のラベルフレーム
        self.imgFrame = tk.LabelFrame(self.master, text="画像")
        self.imgFrame.grid(row=0, column=1)

    def initCanvas(self):
        # 画像の名前を入れる（フルパス）
        self.imgNameVar = tk.StringVar()

        # フォルダが指定されていれば１枚めの画像名を表示
        # 指定されてなければサンプル表示にする
        if len(self.imgList) != 0:
            self.imgNameVar.set(self.imgList[self.nowImg])
        else:
            self.imgNameVar.set("ここに表示している画像名が表示されます")

        # 画像のファイル名を表示
        tk.Label(self.imgFrame,
                 textvariable=self.imgNameVar).grid(row=0, column=0, columnspan=4)

        # 表示する画像を切替える
        tk.Button(self.imgFrame, text="前の画像", command=self.getBeforeImg).grid(row=1, column=0, sticky=tk.W)
        tk.Button(self.imgFrame, text="次の画像", command=self.getAfterImg).grid(row=1, column=1)

        # キャンバスを表示
        self.imgCanvas = tk.Canvas(self.imgFrame, bg="white", width=self.canvasWidth, height=self.canvasHeight)
        self.imgCanvas.grid(row=10, column=0)

        # 初期表示
        imgText = self.imgCanvas.create_text(400, 201, text="画像フォルダを設定してください", font=("", 24))
        self.imgCanvas.create_rectangle(self.imgCanvas.bbox(imgText))

        # マウスイベントの紐付け
        self.imgCanvas.bind("<ButtonPress-1>", self.mousePressed)
        self.imgCanvas.bind("<B1-Motion>", self.mouseMoved)
        self.imgCanvas.bind("<ButtonRelease-1>", self.mouseReleased)

        # 削除ボタン
        tk.Button(self.imgFrame, text="四角を全て削除", command=self.rectDeleteAll).grid(row=11, column=0)
        tk.Button(self.imgFrame, text="最後に描いた四角を削除", command=self.rectDeleteLast).grid(row=11, column=1)

    def setImage(self, imgPath):
        # 画像を読み込む
        read_img = cv2.imread(imgPath, 1)
        read_img = cv2.cvtColor(read_img, cv2.COLOR_BGR2RGB)
        read_img = Image.fromarray(read_img)

        # 画像をキャンバスの大きさに変更するための倍率を計算
        imgWidthGain = self.canvasWidth / read_img.width
        imgHeightGain = self.canvasHeight / read_img.height
        # print(imgWidthGain, imgHeightGain)

        self.imgWidthGain[imgPath] = imgWidthGain
        self.imgHeightGain[imgPath] = imgHeightGain

        # 倍率に沿ってリサイズ
        read_img = read_img.resize((int(read_img.width * imgWidthGain), int(read_img.height * imgHeightGain)))

        # キャンバスに画像を貼る
        img = ImageTk.PhotoImage(image=read_img)
        self.imgCanvas.delete("all")
        self.imgCanvas.photo = img
        self.imgCanvas.create_image(0, 0, anchor="nw", image=self.imgCanvas.photo)

        # 過去の処理結果を読み込んでいたら枠を描画
        if self.result != {}:
            self.reconstRect()

    def readJson(self):
        try:
            with open(self.imgFolderVar.get() + self.resultJson, "r") as f:
                result = json.load(f)  # 過去の処理結果を読み来む
                for n, v in result.items():
                    # read_img = Image.open(n)  # 画像を読み込む
                    read_img = cv2.imread(n, 1)
                    read_img = cv2.cvtColor(read_img, cv2.COLOR_BGR2RGB)

                    # 画像をキャンバスの大きさに変更するための倍率を計算
                    imgWidthGain = self.canvasWidth / read_img.shape[1]
                    imgHeightGain = self.canvasHeight / read_img.shape[0]

                    # もとの座標からキャンバスの座標に変換
                    for i, (k, x) in enumerate(v):
                        x["lux"] = int(x["lux"] * imgWidthGain)
                        x["luy"] = int(x["luy"] * imgHeightGain)
                        x["rlx"] = int(x["rlx"] * imgWidthGain)
                        x["rly"] = int(x["rly"] * imgHeightGain)
                        result[n][i][1] = x
                self.result = copy.deepcopy(result)

            # ファイル名の最後のものから表示させる
            last = list(self.result.keys())[-1]
            self.nowImg = self.imgList.index(last)
        except:
            # ファイルに異常があった場合は初期値を設定
            self.result = {}
            self.nowImg = 0

    def getImgDirectory(self):
        # 初期化
        self.drawRectangles = [[]]
        self.drawTexts = []
        self.mousePointList = []
        self.result = {}

        # 画像フォルダを取得する
        initDir = os.path.abspath(os.path.dirname(__file__))
        filePath = filedialog.askdirectory(initialdir=initDir)  # 検索ウィンドウ
        self.imgFolderVar.set(filePath)

        # 画像一覧を取得
        # jpgとpngにのみ対応
        self.imgList = glob(filePath + "/*.jpg")
        self.imgList += glob(filePath + "/*.png")
        self.nowImg = 0  # １枚目に設定

        # 画像が無かったら
        if self.imgList == []:
            messagebox.showwarning("error", "画像がありません。jpgとpngにのみ対応しています")
            return

        # 既にresult.jsonがあれば
        if os.path.exists(self.imgFolderVar.get() + self.resultJson):
            # with open(self.imgFolderVar.get() + "result.json", "r") as f:
            #     self.result = json.load(f)
            self.readJson()

        # 画像名を取得してラベルに反映
        self.imgNameVar.set(self.imgList[self.nowImg])
        self.setImage(self.imgList[self.nowImg])  # 画像をキャンバスに設定する

    def reconstRect(self):
        # 初期化
        self.drawRectangles = []
        self.mousePointList = []

        try:
            for name, points in self.result[self.imgList[self.nowImg]]:
                # 枠を描画
                rect = self.imgCanvas.create_rectangle([points["lux"], points["luy"], points["rlx"], points["rly"]],
                                                       width=points["thick"], outline=points["color"])
                self.drawRectangles.append([rect])
                self.mousePoint = [points[k] for k in points.keys()]
                self.mousePointList.append(self.mousePoint)

                # オブジェクト名を表示
                text = self.imgCanvas.create_text(min(points["lux"], points["rlx"]) + 15,
                                                  min(points["luy"], points["rly"]) + 15,
                                                  text=name, font=("", 24), fill=points["color"])
                self.drawTexts.append([text, name])
        except:
            pass

        self.drawRectangles.append([])

    def getBeforeImg(self):
        # １つ前の画像に切替える

        # 設定された枠の情報を出力
        self.resultOutput()

        # 画像が無ければ
        if self.imgList == []:
            messagebox.showwarning("エラー", "画像フォルダを設定してください")
            return

        # 画像があれば
        if self.nowImg != 0:
            # 画像番号をへらす
            self.nowImg -= 1
            # 次に表示する画像名を取得
            self.imgNameVar.set(self.imgList[self.nowImg])
            self.setImage(self.imgList[self.nowImg])  # キャンバスに反映
        else:
            messagebox.showwarning("エラー", "この画像が最初の１枚です")

        self.reconstRect()

    def getAfterImg(self):
        # 設定した枠の情報を出力
        self.resultOutput()

        # エラー処理
        if self.imgList == []:
            messagebox.showwarning("エラー", "画像フォルダを設定してください")
            return

        # 表示する画像を変える
        if self.nowImg != (len(self.imgList) - 1):
            self.nowImg += 1
            self.imgNameVar.set(self.imgList[self.nowImg])
            self.setImage(self.imgList[self.nowImg])
        else:
            messagebox.showwarning("エラー", "この画像が最後の１枚です")

        self.reconstRect()

    def resultOutput(self):
        # フォルダが設定されてなければ何もせず
        if self.imgFolderVar.get() == "":
            return

        # 出力ファイルに書き込み
        # pprint.pprint(self.result)
        with open(self.imgFolderVar.get() + self.resultFile, "w") as f:
            for k, v in self.result.items():
                fileName = k
                if not (fileName in list(self.imgWidthGain.keys())):
                    continue
                if len(v) != 0:
                    c = 1
                    for n, p in v:
                        f.write(("{} {} {} {} {} {}\n").format(fileName, c,
                                                               int(p["lux"] / self.imgWidthGain[fileName]),
                                                               int(p["luy"] / self.imgHeightGain[fileName]),
                                                               int(p["rlx"] / self.imgWidthGain[fileName]),
                                                               int(p["rly"] / self.imgHeightGain[fileName])))
                        c += 1

        with open(self.imgFolderVar.get() + self.resultJson, "w") as f:
            result = copy.deepcopy(self.result)
            for n, v in result.items():
                if not (n in list(self.imgWidthGain.keys())):
                    continue
                for i, (k, x) in enumerate(v):
                    x["lux"] = int(x["lux"] / self.imgWidthGain[n])
                    x["luy"] = int(x["luy"] / self.imgHeightGain[n])
                    x["rlx"] = int(x["rlx"] / self.imgWidthGain[n])
                    x["rly"] = int(x["rly"] / self.imgHeightGain[n])
                    result[n][i][1] = x
            json.dump(result, f, ensure_ascii=False, indent=4)

    def mousePressed(self, event):
        # マウスが押されたときの座標
        mx = event.x
        my = event.y
        self.mousePoint = [mx, my, mx, my]
        self.mouseMovedFlag = True

    def mouseMoved(self, event):
        # マウスが押されながら動いてるとき（ドラッグされてる状態）
        if self.mouseMovedFlag:
            mx = event.x
            my = event.y

            # 枠外に出た場合
            if mx < 0:
                mx = 0
            elif mx > self.canvasWidth:
                mx = self.canvasWidth

            if my < 0:
                my = 0
            elif my > self.canvasHeight:
                my = self.canvasHeight

            self.mousePoint[2] = mx
            self.mousePoint[3] = my

            # 直前の表示を削除
            if len(self.drawRectangles[-1]) > 0:
                self.imgCanvas.delete(self.drawRectangles[-1][-1])

            # 線の太さを変更
            lineWidth = int(self.lineWidth.get())
            lineColor = self.lineColor.get()
            rect = self.imgCanvas.create_rectangle(self.mousePoint, width=lineWidth, outline=lineColor)

            # 最新の枠に更新
            self.drawRectangles[-1].append(rect)

    def mouseReleased(self, event):
        # マウスが押されなくなった（指が離れた）
        self.mouseMovedFlag = False

        # 座標を記録
        # print(self.mousePoint)
        self.mousePointList.append(self.mousePoint)
        self.drawRectangles[-1] = [self.drawRectangles[-1][-1]]
        self.drawRectangles.append([])

        # 囲われたオブジェクトの名称を取得
        boxName = askstring("input", "そのオブジェクトの名前は？", )
        if boxName is None or boxName == "":  # キャンセルされたら枠ごと消して終わり
            self.rectDeleteLast()
            return

        # 枠の左上に名称を追記
        text = self.imgCanvas.create_text(min(self.mousePoint[0], self.mousePoint[2]) + 15,
                                          min(self.mousePoint[1], self.mousePoint[3]) + 15,
                                          text=boxName, font=("", 24), fill=self.lineColor.get())
        self.drawTexts.append([text, boxName])  # テキストオブジェクトを保持

        if self.imgList == []:
            return

        try:
            isinstance(self.result[self.imgList[self.nowImg]][boxName], list)
        except:
            # ファイル名のキーが登録されてなければ登録する
            try:
                isinstance(self.result[self.imgList[self.nowImg]], dict)
            except:
                self.result[self.imgList[self.nowImg]] = []

        # 辞書に追加
        self.result[self.imgList[self.nowImg]].append([boxName, {"color": self.lineColor.get(),
                                                                 "thick": int(self.lineWidth.get()),
                                                                 "lux": self.mousePoint[0],
                                                                 "luy": self.mousePoint[1],
                                                                 "rlx": self.mousePoint[2],
                                                                 "rly": self.mousePoint[3]}])

    def rectDeleteAll(self):
        # 表示されている枠を全て削除
        if self.drawRectangles == [[]]:
            return

        [self.imgCanvas.delete(i[0]) for i in self.drawRectangles[:-1]]
        [self.imgCanvas.delete(i[0]) for i in self.drawTexts]

        self.drawRectangles = [[]]
        self.drawTexts = []
        self.mousePoint = []
        self.mousePointList = []

        if self.result != {}:
            del (self.result[self.imgList[self.nowImg]])

    def rectDeleteLast(self):
        # 一番新しい枠だけ削除
        if self.drawRectangles == [[]]:
            return

        if len(self.drawRectangles) >= 2:
            self.imgCanvas.delete(self.drawRectangles[-2][0])
            self.drawRectangles = self.drawRectangles[:-1]
        if len(self.drawTexts) >= 1:
            self.imgCanvas.delete(self.drawTexts[-1][0])
            self.drawTexts = self.drawTexts[:-1]

        self.mousePointList = self.mousePointList[:-1]

        # 今表示されている画像の、最後に作られた枠名の、最新の情報を削除
        try:
            if self.result[self.imgList[self.nowImg]] != []:
                del (self.result[self.imgList[self.nowImg]][-1])
        except:
            pass


root = tk.Tk()
app = MainGUI(master=root)
app.mainloop()
