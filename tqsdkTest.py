#!/usr/bin/env python
#  -*- coding: utf-8 -*-


from tqsdk.api import TqApi


#时间转换函数
def timeChange(second = 0,minute = 0,hour = 0):
    return second + minute * 60 + hour * 3600

api = TqApi("SIM")
ticks = api.get_tick_serial("SHFE.rb1901")
K_Line_one = api.get_kline_serial("SHFE.rb1901",timeChange(0,3)) #负责大周期突破判断(时间自己判断)
K_Line_two = api.get_kline_serial("SHFE.rb1901",timeChange(0,15)) #负责止盈(时间自己判断)
K_Line_three = api.get_kline_serial("SHFE.rb1901",timeChange(0,0,1)) #负责止损(时间自己判断)
signBuy = 0 
signSell = 0
cciValue = 0
sarLittleUp = [0]
sarLittleDown = [0]
sarBigUp = [0]
sarBigDown = [0]

#震荡指标（任意震荡指标 CCI默认n = 20）
def CCI(n = 20):
    TP = ((K_Line_one[-1]["close"] + K_Line_one[-1]["low"] + K_Line_one[-1]["high"]) / 3)
    MAList = []
    for i in range(1, n + 1):
        MAList.append(K_Line_one[-i]["close"])
        if len(MAList) > n:
            MAList.pop(0)
    MA = sum(MAList) / n
    MDList = []
    for i in range(1, n + 1):
        MDList.append(abs(MA - K_Line_one[-i]["close"]))
        if len(MDList) > n:
            MDList.pop(0)
    MD = sum(MDList) / n
    cci = (TP - MA) / MD /0.015
    return cci


#趋势跟踪指标
class SAR():
    def __init__(self, sarList, KLine, n, step, m):
        if sarList[-1] == 0:
            self.sar = {"value":[0], "trends":[0], "step":[0]} 
        else:
            self.sar = sarList[-1]
        self.KLine = KLine
        self.n = n
        self.step = step
        self.m = m

    def getSAR(self): 
        if self.sar["value"][-1] == 0:    #第一次SAR计算           
            uptrend = self.KLine[-1]["close"] - self.KLine[-1]["open"]
            if uptrend > 0:
                KLineLow = []
                for i in range(2, self.n + 2):
                    KLineLow.append(self.KLine[-i]["low"])
                if len(KLineLow) > self.n:
                    KLineLow.pop(0)
                Low = min(KLineLow)
                self.sar["value"][-1] = Low
                self.sar["trends"][-1] = 1
                self.sar["step"][-1] = self.step
            else:
                KLineHigh = []
                for i in range(2, self.n + 2):
                    KLineHigh.append(self.KLine[-i]["high"])
                if len(KLineHigh) > self.n:
                    KLineHigh.pop(0)
                High = max(KLineHigh)
                self.sar["value"][-1] = High
                self.sar["trends"][-1] = -1
                self.sar["step"][-1] = self.step
            return self.sar

        else:
            if self.sar["trends"][-1] == 1:             #方向为涨
                ep = []
                for i in  range(2, self.n + 2):
                    ep.append(self.KLine[-i]["high"])
                if len(ep) > self.n:
                    ep.pop(0)
                if self.KLine[-2]["low"] > self.sar["value"][-1]:
                    self.sar["value"][-1] = (self.sar["value"][-1] + self.sar["step"][-1] * (max(ep) - self.sar["value"][-1]))
                    self.sar["trends"][-1] = 1
                    if self.KLine[-2]["high"] > self.KLine[-3]["high"]:
                        newStep = self.sar["step"][-1] + self.step
                        if newStep <= self.m:
                            self.sar["step"][-1] = newStep
                        else:
                            self.sar["step"][-1] = self.m
                    else:
                        self.sar["step"][-1] = self.sar["step"][-1]
                else:                       #跌破止损点
                    newSar = []
                    for i in range(2, self.n + 2):
                        newSar.append(self.KLine[-i]["high"])
                    if len(newSar) > self.n:
                        newSar.pop(0)
                    self.sar["value"][-1] = max(newSar)
                    self.sar["trends"][-1] = -1
                    self.sar["step"][-1] = self.step
                return self.sar

            if self.sar["trends"][-1] == -1:           #方向为跌
                ep = []
                for i in range(2, self.n + 2):
                    ep.append(self.KLine[-i]["low"])
                if len(ep) > self.n:
                    ep.pop(0)
                if self.KLine[-2]["high"] < self.sar["value"][-1]:
                    self.sar["value"][-1] = (self.sar["value"][-1] + self.sar["step"][-1] * (min(ep) - self.sar["value"][-1]))
                    self.sar["trends"][-1] = -1
                    newStep = self.sar["step"][-1] + self.step
                    if self.KLine[-2]["low"] < self.KLine[-3]["low"]:
                        if newStep <= self.m:
                            self.sar["step"][-1] = newStep
                        else:
                            self.sar["step"][-1] = self.m
                    else:
                        self.sar["step"][-1]  = self.sar["step"][-1]
                else:                             #涨破止损点
                    newSar = []
                    for i in range(2, self.n + 2):
                        newSar.append(self.KLine[-i]["low"])
                    if len(newSar) > self.n:
                        newSar.pop(0)
                    self.sar["value"][-1] = min(newSar)
                    self.sar["trends"][-1] = 1
                    self.sar["step"][-1] = self.step
                return self.sar

sarLittleValue = [0]
sarBigValue = [0]
sarLittle = SAR( sarLittleValue, K_Line_three, 4, 0.02, 0.2)
sarBig = SAR(sarBigValue, K_Line_two, 4, 0.02, 0.2)


while True:
    api.wait_update()
    if api.is_changing(ticks):
        tickPrice = ticks[-1]["last_price"]
    if api.is_changing(K_Line_three[-1], "datetime"): #计算止损SAR，到时更新
        sarLittleValue[-1] = sarLittle.getSAR()
        if sarLittleValue[-1]["trends"][-1] == 1:
           sarLittleUp.append(sarLittleValue[-1])
        else:
            sarLittleDown.append(sarLittleValue[-1])
        if len(sarLittleUp) > 10:
            sarLittleUp.pop(0)
        if len(sarLittleDown) > 10:
            sarLittleDown.pop(0)
    if api.is_changing(K_Line_two[-1], "datetime"):  #计算止盈SAR，到时更新
        sarBigValue[-1] = sarBig.getSAR()
        if sarBigValue[-1]["trends"][-1] ==1:
            sarBigUp.append(sarBigValue[-1])
        else:
            sarBigDown.append(sarBigValue[-1])

        if len(sarBigUp) > 10:
            sarBigUp.pop(0)
        if len(sarBigDown) > 10:
            sarBigDown.pop(0)

    if api.is_changing(K_Line_one):  #计算大周期突破标志
        cciValue =  CCI()
    if cciValue >= 100:      #大周期向上突破
        if signBuy != 1:
            if sarLittleUp[-1] != 0:
                print("开多头，价位：" ,tickPrice)
                signBuy = 1
                buyPrice = tickPrice           #不考虑仓位信息，假设开仓价为信号出现时的盘口价
    if signBuy == 1:
        if buyPrice - tickPrice > 20:         
            if tickPrice < sarBigUp[-1]["value"][-1]:   #20点浮动范围外由大周期止盈
                print("平多头,价位：" ,tickPrice)
                signBuy = 0
        else:
            if tickPrice < sarLittleUp[-1]["value"][-1]:  #20点浮动范围内由小周期止损
                print("平多头,价位：" ,tickPrice)
                signBuy = 0

    if cciValue <= -100:
        if signSell != 1:
            if sarLittleDown[-1] != 0:
                print("开空头,价位：" , tickPrice)
                signSell = 1
                sellPrice = tickPrice
    if signSell == 1:
        if sellPrice - tickPrice > 20:
            if tickPrice > sarBigDown[-1]["value"][-1]:
                print("平空头，价位：" ,tickPrice)
                signSell = 0
        else:
            if tickPrice > sarLittleDown[-1]["value"][-1]:
                print("平空头，价位：",tickPrice)
                signSell = 0

