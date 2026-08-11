import pandas as pd

def add_ict_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Swing highs/lows (simplified)
    df['swing_high'] = df['High'].rolling(5).max() == df['High']
    df['swing_low'] = df['Low'].rolling(5).min() == df['Low']

    # Fair Value Gaps
    df['fvg_bull'] = (df['Low'].shift(1) > df['High'].shift(3)) & (df['High'].shift(1) < df['Low'].shift(3))
    df['fvg_bear'] = (df['High'].shift(1) < df['Low'].shift(3)) & (df['Low'].shift(1) > df['High'].shift(3))

    # Order Blocks (simplified)
    df['ob_bull'] = df['swing_low'] & (df['Low'] < df['Low'].shift(-1))
    df['ob_bear'] = df['swing_high'] & (df['High'] > df['High'].shift(-1))

    # Liquidity Sweeps
    df['liq_sweep_bull'] = (df['Low'] < df['Low'].rolling(20).min()) & (df['Close'] > df['Open'])
    df['liq_sweep_bear'] = (df['High'] > df['High'].rolling(20).max()) & (df['Close'] < df['Open'])

    return df
