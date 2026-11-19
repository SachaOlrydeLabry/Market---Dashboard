"""Asset symbols, currencies, and selectable time windows."""

import pandas as pd



INDICES={"S&P 500":"^GSPC","Nasdaq 100":"^NDX","Dow Jones":"^DJI","Russell 2000":"^RUT","STOXX Europe 600":"^STOXX","EURO STOXX 50":"^STOXX50E","CAC 40":"^FCHI","DAX":"^GDAXI","FTSE 100":"^FTSE","SMI":"^SSMI","Nikkei 225":"^N225","TOPIX":"^TOPX","Hang Seng":"^HSI","CSI 300":"000300.SS","Nifty 50":"^NSEI"}

COMMODITY_UNITS={"Gold":("USD","troy oz"),"Silver":("USD","troy oz"),"Copper":("USD","lb"),"WTI crude":("USD","barrel"),"Brent crude":("USD","barrel"),"Natural gas":("USD","MMBtu"),"Wheat":("US cents","bushel"),"Corn":("US cents","bushel")}

COMMODITIES={"Gold":"GC=F","Silver":"SI=F","Copper":"HG=F","WTI crude":"CL=F","Brent crude":"BZ=F","Natural gas":"NG=F","Wheat":"ZW=F","Corn":"ZC=F"}

FX_CODES=["USD","EUR","GBP","JPY","CHF","AUD","CAD","NZD"]

US_CURVE={"3M":"DGS3MO","2Y":"DGS2","5Y":"DGS5","10Y":"DGS10","30Y":"DGS30"}

COUNTRY_10Y = {
    "US": "DGS10",
    "UK": "IRLTLT01GBM156N",
    "France": "IRLTLT01FRM156N",
    "Germany": "IRLTLT01DEM156N",
    "Japan": "IRLTLT01JPM156N",
    "Switzerland": "IRLTLT01CHM156N",
}

INDEX_CURRENCY={"S&P 500":"USD","Nasdaq 100":"USD","Dow Jones":"USD","Russell 2000":"USD", "STOXX Europe 600":"EUR","EURO STOXX 50":"EUR","CAC 40":"EUR","DAX":"EUR", "FTSE 100":"GBP","SMI":"CHF","Nikkei 225":"JPY","TOPIX":"JPY","Hang Seng":"HKD","CSI 300":"CNY","Nifty 50":"INR"}

RF_SOURCE={"USD":"US Treasury 2Y (DGS2)"}

WINDOWS={"1M":pd.DateOffset(months=1),"3M":pd.DateOffset(months=3),"6M":pd.DateOffset(months=6),"1Y":pd.DateOffset(years=1),"3Y":pd.DateOffset(years=3),"5Y":pd.DateOffset(years=5),"10Y":pd.DateOffset(years=10),"Max":None}

DATE_FORMAT = "%d %b %y"

PLOT_DATE_FORMAT = "%d %b %y"
