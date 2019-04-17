#!/usr/bin/env python
#  -*- coding: utf-8 -*-

from tqsdk import TqApi, TqSim
import json


class doubleMA():
    def __init__(self, account, symbol, MA1, MA2, max_value, mini_value, trading_direction, trading_cycle, volume_number):
        self.account = account #交易账号
        self.symbol = symbol #合约代码
        self.MA1 = MA1 #小周期
        self.MA2 = MA2 #大周期
        self.max_value = max_value #震荡区间的最高点
        self.mini_value = mini_value #震荡区间的最低点
        self.trading_direction = trading_direction #交易方向 1为涨 0为跌 以下均以 1 0 为定义
        self.trading_cycle = trading_cycle #交易周期（以分钟记）
        self.volume_number = volume_number #交易数量
        self.position_flag = 0 #持仓标记
        self.kline_flag = 0   #K线标记 避免单根K线上多次开仓 
        self.open_flag = 0      #开仓标记，避免止损点移动

        self.api = TqApi(self.account)
        self.kline = self.api.get_kline_serial(self.symbol, self.trading_cycle * 60, data_length=200)
        self.position = self.api.get_position(self.symbol)  #获得持仓状态
        self.sell_list = []
        self.buy_list = []      #存放开仓时的两个k线的最高或者最低点,在开仓时记录平仓时清空
        
    def open_json(self):
        try:
            fp = open('F:\python\PythonApplication1\PythonApplication1\doubleMA.json','r')
            result = json.load(fp)
            self.buy_list = result['self.buy_list']
            self.sell_list = result['self.sell_list']
            print('buy_list: ', self.buy_list)
            print('sell_list: ', self.sell_list)
        except:
            print("还没有json")
        
    def save_json(self):
        fp = open('F:\python\PythonApplication1\PythonApplication1\doubleMA.json','w')
        save = {'self.buy_list':self.buy_list,'self.sell_list':self.sell_list}
        json.dump(save,fp)


    def ma(self, daytime):
        close_list = []
        for i in range(1,daytime+1):
            close_list.append(self.kline[-i]["close"])
        avg = sum(close_list)/daytime
        return avg

    def account_trading(self, trading_direction, offset_flag, td_price):
        if self.position["volume_long"] or self.position["volume_short"] != 0:
            self.position_flag = 1    
        if offset_flag == "OPEN":
            if self.position_flag != 1:
                self.api.insert_order(symbol=self.symbol,direction=trading_direction,offset=offset_flag,volume=self.volume_number,limit_price=td_price)
                self.position_flag = 1
        if offset_flag == "CLOSE":
            if self.position_flag == 1:
                if self.position["volume_long_today"] or self.position["volume_short_today"]!= 0:
                    self.api.insert_order(symbol=self.symbol,direction=trading_direction,offset="CLOSETODAY",volume=self.volume_number,limit_price=td_price)
                    self.position_flag = 0
                elif self.position["volume_long_his"] or self.position["volume_short_his"] != 0:
                    self.api.insert_order(symbol=self.symbol,direction=trading_direction,offset="CLOSE",volume=self.volume_number,limit_price=td_price)
                    self.position_flag = 0

    def close_buy(self):
        if self.position_flag == 1:
            if(self.trading_direction == 1):         #平多
                while True:
                    self.api.wait_update()
                    if(self.kline[-1]["close"] < self.buy_list[-1]):
                        self.account_trading("SELL","CLOSE", self.kline[-1]["close"])
                        self.kline_flag += 1
                        self.buy_list.clear()
                        self.save_json()
                        self.open_flag -= 1
                        break
                    if(self.kline[-1]["close"] > self.max_value):
                        break
            if(self.trading_direction == 0):
                while True:
                    self.api.wait_update()
                    if(self.kline[-1]["close"] > self.sell_list[-1]):
                        self.account_trading("BUY", "CLOSE", self.kline[-1]["close"])
                        self.kline_flag += 1
                        self.open_flag -= 1
                        self.sell_list.clear()
                        self.save_json()
                        break
                    if(self.kline[-1]["close"] < self.mini_value):
                        break

    def open_buy(self):
        if self.position_flag == 0:
            if(self.trading_direction == 1):       #交易方向为涨
                if self.kline_flag == 0:
                    while True:
                        self.api.wait_update()
                        ma1 = self.ma(self.MA1)
                        ma2 = self.ma(self.MA2)
                        if(self.kline[-1]["close"] >= self.kline[-2]["high"]):  #突破最高点开仓
                            self.account_trading("BUY", "OPEN", self.kline[-1]["close"])
                            if self.open_flag == 0:
                                self.buy_list.append(int(self.kline[-1]["low"]))
                                self.buy_list.append(int(self.kline[-2]["low"]))
                                self.buy_list.sort()
                                self.buy_list.pop()      #抛弃掉最大的
                                self.save_json()
                                self.open_flag += 1
                            self.kline_flag += 1
                            print("止损点：" ,self.buy_list[-1])
                            break  
                        if(self.kline[-1]["close"] < self.mini_value) or (ma1 > ma2):
                            break  
            elif(self.trading_direction == 0):     #交易方向为跌
                if self.kline_flag == 0:
                    while True:
                        self.api.wait_update()
                        ma1 = self.ma(self.MA1)
                        ma2 = self.ma(self.MA2)
                        if(self.kline[-1]["close"] <= self.kline[-2]["low"]):
                            self.account_trading("SELL", "OPEN", self.kline[-1]["close"])
                            if self.open_flag == 0:
                                self.sell_list.append(int(self.kline[-1]["high"]))
                                self.sell_list.append(int(self.kline[-2]["high"]))
                                self.sell_list.sort(reverse = True)
                                self.sell_list.pop()    #抛弃掉最小的
                                self.open_flag += 1
                                self.save_json()
                            self.kline_flag += 1
                            print("止损点：" ,self.sell_list[-1])
                            break    
                        if(self.kline[-1]["close"] > self.max_value) or (ma1 < ma2):
                            break  

    def star(self):
        self.open_json()
        if self.position["volume_long"] or self.position["volume_short"] != 0:
            self.position_flag = 1    
        while True:
            self.api.wait_update()
            if self.api.is_changing(self.kline[-1],"datetime"):
                self.kline_flag = 0
            #开仓方法 
            ma1 = self.ma(self.MA1)
            ma2 = self.ma(self.MA2)
            if self.trading_direction == 1:   #做多
                if self.kline[-1]["close"] > self.mini_value and self.kline[-1]["close"] < self.max_value:
                    if ma2 > ma1:
                        #print('震荡区间中')
                        self.open_buy()
                        self.close_buy()
                elif self.kline[-1]["close"] <self.mini_value:
                    self.close_buy()
                    break
                elif self.kline[-1]["close"] > self.max_value:
                    if ma1 < ma2:
                        self.account_trading("SELL","CLOSE",self.kline[-1]["close"])
                        break
                    else:
                        self.open_buy()
                        self.close_buy()
            elif self.trading_direction == 0:  #做空
                if self.kline[-1]["close"] > self.mini_value and self.kline[-1]["close"] < self.max_value:
                    if ma1 > ma2:
                        self.open_buy()
                        self.close_buy()
                elif self.kline[-1]["close"] > self.max_value:
                    self.close_buy()
                    break
                elif self.kline[-1]["close"] < self.mini_value:
                    if ma1 > ma2:
                        self.account_trading("BUY","CLOSE",self.kline[-1]["close"])
                        break
                    else:
                        self.open_buy()
                        self.close_buy()
        self.api.close()

a = doubleMA("120276","SHFE.rb1910",3,20,3843,3791,1,5,1)
a.star()
print('策略已退出')