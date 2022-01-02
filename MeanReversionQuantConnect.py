from AlgorithmImports import *
import numpy as np
import pandas as pd
from io import StringIO
#Sentiment analysis 
# from vaderSentiment import SentimentIntensityAnalyzer, pairwise 

class RetrospectiveFluorescentPinkCobra(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2020, 1, 1)  # Set Start Date
        self.SetEndDate(2022,1,1) # Set End Date
        self.SetCash(100000)  # Set Strategy Cash
        
        self.stocklist = ["HAL", "SRE", "RGS", "CAT", "WYNN"] # list of stocks to be traded
        self.number_of_stocks = len(self.stocklist) # number of stocks
        stock = 0
        self.list_of_securities = [] #lists that contains symbol object of each stock
        self.rsi = [] # list that contains rsi data of eachs stock
        self.bb = [] #list that contains rsi and bollinger band data of each stock
        self.stocks_to_hold = []
        self.portfolio_change = False
        
        # Sentiment Analysis
        
        for i in range(self.number_of_stocks):
            stock = self.AddEquity(self.stocklist[i], Resolution.Minute)
            stock.SetDataNormalizationMode(DataNormalizationMode.Adjusted)
            self.list_of_securities.append(stock.Symbol) 
            #adds symbol object to list of securities
            
            self.rsi.append(self.RSI(self.list_of_securities[i], 14,  MovingAverageType.Simple, Resolution.Daily))
            self.bb.append(self.BB(self.list_of_securities[i], 14, 2, MovingAverageType.Simple, Resolution.Daily))
            #adds rsi and bollinger band indicators for each stock
            
        self.SetBenchmark("SPY") #S&P 500 benchmark
        self.SetWarmup(timedelta(14)) #Warmup time for indicators


    def OnData(self, data):
        for l in range(self.number_of_stocks):
            if (data.Bars.ContainsKey(self.list_of_securities[l])) and (data[self.list_of_securities[l]] is not None) : #checks if data exists for that point in time
                
                price = data[self.list_of_securities[l]].Value #sets price of each stock
                
                if (self.rsi[l].IsReady) and (self.bb[l].IsReady):
                    rsi_value = self.rsi[l].Current.Value
                    upper_band = self.bb[l].UpperBand.Current.Value
                    lower_band = self.bb[l].LowerBand.Current.Value
                    #sets rsi, upper and lower band values at that point in time
                    
                    if (rsi_value < 30) and (price < lower_band) and (not self.Portfolio[self.list_of_securities[l]].Invested):
                        self.stocks_to_hold.append(self.list_of_securities[l])
                        self.portfolio_change = True
                        #buying condition ADD SENTIMENT ANALYSIS HERE
                
                    if (self.Portfolio[self.list_of_securities[l]].Invested) and (rsi_value > 70) and (price > upper_band):
                        self.Liquidate(self.list_of_securities[l])
                        self.stocks_to_hold.remove(self.list_of_securities[l])
                        self.portfolio_change = True
                        #selling condition ADD SENTIMENT ANALYSIS HERE
                        
        if self.portfolio_change == True: #porfolio rebalancing
            self.Liquidate()
            for j in range(len(self.stocks_to_hold)):
                self.SetHoldings(self.stocks_to_hold[j], 1/len(self.stocks_to_hold))
                self.Log(str(self.stocks_to_hold[j]))
            self.portfolio_change = False