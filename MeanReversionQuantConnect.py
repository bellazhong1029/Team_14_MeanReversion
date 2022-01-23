from AlgorithmImports import *
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from io import StringIO

class CrawlingFluorescentPinkLemur(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2022, 1, 1) # Set Start Date
        self.SetEndDate(2022,1,21) # Set End Date
        self.SetCash(100000)  # Set Strategy Cash
        self.spy = self.AddEquity('SPY', Resolution.Daily).Symbol #manually add SPY
        
        self.stocklist = [] # list of stocks to be traded
        csv = self.Download("https://raw.githubusercontent.com/mugsy1437/files/main/S%26P_500.csv")
        sp500data = pd.read_csv(StringIO(csv)) #imports data into pandas
        self.symbols = sp500data['Symbol'] #filters to column of symbols
        
        for k in range(self.symbols.size):
            self.stocklist.append(str(self.symbols[k]))
            #self.Log(self.stocklist[k])
        
        self.list_of_securities = [] #list that contains the symbol object of each stock
        self.sma = [] #list that contains the sma data for each stock
        self.rsi = [] # list that contains rsi data of eachs stock
        self.bb = [] #list that contains rsi and bollinger band data of each stock
        
        self.number_of_stocks = len(self.stocklist) #number of stocks
        self.Log(str(self.number_of_stocks))
        
        self.stocks_to_hold = [] #array of stocks to buy
        self.portfolio_change = False #triggered if a stock is to be sold or bought 
        
        # RSI frequency strat
        self.rsi_span = [30, 70]
        self.rsi_freq = 1
        # paul end
        
        #creates a numpy matrix used in horizontal function   
        self.rolling_avg = np.zeros((self.number_of_stocks,10))  
        
        #adds stocks as symbol object to list of securities
        for i in self.stocklist:
            stock = self.AddEquity(i, Resolution.Hour)
            stock.SetDataNormalizationMode(DataNormalizationMode.Adjusted)
            stock = stock.Symbol
            if self.History([i], 20, Resolution.Daily).empty == False: 
                self.list_of_securities.append(stock)
           
        self.number_of_stocks = len(self.list_of_securities) 
        self.horizontal_bool = [0 for mm in range(self.number_of_stocks)]
        self.slopevalues = [0 for mmm in range(self.number_of_stocks)]
             
        #adds sma, rsi and bollinger band indicators for each stock    
        for j in self.list_of_securities:
            self.sma.append(self.SMA(j, 10, Resolution.Daily) )
            self.rsi.append(self.RSI(j, 14,  MovingAverageType.Simple, Resolution.Daily))
            self.bb.append(self.BB(j, 14, 2, MovingAverageType.Simple, Resolution.Daily))
        
        #updates horizontal function every day
        self.Schedule.On(self.DateRules.EveryDay('SPY'), self.TimeRules.AfterMarketOpen('SPY', 0), self.Horizontal_trend)
        
        #manually warms up horizontal, sma, rsi and bb 
        for k in range(self.number_of_stocks):
            history = self.History([self.list_of_securities[k]], 20, Resolution.Daily)   
            for time, row in history.loc[self.list_of_securities[k]].iterrows():
                self.sma[k].Update(time, row["close"])
                self.rsi[k].Update(time, row["close"])
                self.bb[k].Update(time, row["close"])
                row = self.rolling_avg[k]
                row = row[1:]
                row = np.append(row,np.array([self.sma[k].Current.Value]))
                self.rolling_avg[k] = row
                
        self.Log(str(self.number_of_stocks))
        self.time = np.linspace(0,9,10)
        self.time = self.time.reshape(-1,1)
        self.reg = LinearRegression()


    def OnData(self, data):
        #if not self.Portfolio[self.spy].Invested:
            #self.SetHoldings(self.spy, 1/2)
        for l in range(self.number_of_stocks):
            if (data.Bars.ContainsKey(self.list_of_securities[l])) and (data[self.list_of_securities[l]] is not None) : #checks if data exists for that point in time
                
                price = data[self.list_of_securities[l]].Value #sets price of each stock
                
                if (self.rsi[l].IsReady) and (self.bb[l].IsReady):
                    horizontal = self.horizontal_bool[l]
                    m_value = self.slopevalues[l]
                    rsi_value = self.rsi[l].Current.Value
                    upper_band = self.bb[l].UpperBand.Current.Value
                    lower_band = self.bb[l].LowerBand.Current.Value
                    #sets rsi, upper and lower band values at that point in time     
                
                    if (rsi_value < self.rsi_span[0]) and (price < lower_band) and (horizontal == True) and (not self.Portfolio[self.list_of_securities[l]].Invested):
                        self.stocks_to_hold.append(self.list_of_securities[l])
                        self.portfolio_change = True
                    #buying conditions     
                        
                    if self.Portfolio[self.list_of_securities[l]].Invested and ((not horizontal) or ((rsi_value > self.rsi_span[1]) and (price > upper_band))):
                        self.Liquidate(self.list_of_securities[l])
                        self.stocks_to_hold.remove(self.list_of_securities[l])
                        self.portfolio_change = True    

                        # usage of rsi_feq
                        if ((price-self.Portfolio[str(self.stocklist[l])].AveragePrice) < 0 and self.rsi_freq > -5):
                            self.rsi_freq -= 1
                        if ((price-self.Portfolio[str(self.stocklist[l])].AveragePrice) > 0 and self.rsi_freq < 5):
                            self.rsi_freq += 1
                            
                        if (self.rsi_span[0] > 20):
                            self.rsi_span[0] -= 2 * self.rsi_freq
                        else:
                            self.rsi_freq += 1
                            self.rsi_span[0] = 30
                        
                        if (self.rsi_span[1] < 80):
                            self.rsi_span[1] += 2 * self.rsi_freq
                        else:
                            self.rsi_freq -= 1
                            self.rsi_span[1] = 70  
                        # paul end
                                  
                    #selling conditions
        
        #porfolio rebalancing                
        if self.portfolio_change == True: 
            for j in range(len(self.stocks_to_hold)):
                self.SetHoldings(self.stocks_to_hold[j], 1/len(self.stocks_to_hold))
                #self.Log(str(self.stocks_to_hold[j]))  
            self.portfolio_change = False

    
    def Horizontal_trend(self):
        #list of bool values that represent if the stock at index position is moving horizontally
        self.horizontal_bool = [0 for p in range(self.number_of_stocks)]
        self.slopevalues = [0 for pp in range(self.number_of_stocks)]
        
        for z in range(self.number_of_stocks):
            row = self.rolling_avg[z]
            row = row[1:]
            row = np.append(row,np.array([self.sma[z].Current.Value]))
            self.rolling_avg[z] = row
            self.reg.fit(self.time, self.rolling_avg[z])
            self.m = self.reg.coef_
            self.slopevalues[z] = self.m
            #self.Log(str(self.rolling_avg))
            #self.Log(str(self.m))

            if - 0.1 < self.m < 0.1:
                self.horizontal_bool[z] = True
            else:
                self.horizontal_bool[z] = False     
            #self.Log(str(self.horizontal_bool))