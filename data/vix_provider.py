import yfinance as yf
import pandas as pd

class VIXProvider:
    def __init__(self):
        self.vix = yf.Ticker("^VIX")
        self.vxv = yf.Ticker("^VXV")

    def get_term_structure(self):
        vix_spot = self.vix.history(period="1d")['Close'].iloc[-1]
        vix_future = self.vxv.history(period="1d")['Close'].iloc[-1]
        term = vix_future - vix_spot
        return term
