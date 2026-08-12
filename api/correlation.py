from fastapi import APIRouter
import pandas as pd
import numpy as np

router = APIRouter()

@router.get("/api/correlation")
async def get_correlation():
    app = router.app
    symbols = app.state.config.get('symbols', ['BTCUSD', 'EURUSD', 'GOLD'])
    data = {}
    for sym in symbols:
        df = await app.state.data_fabric.get_candles(sym, "D1", limit=100)
        if not df.empty:
            data[sym] = df['Close'].pct_change()
    df = pd.DataFrame(data)
    corr = df.corr().round(2)
    return corr.to_dict()
