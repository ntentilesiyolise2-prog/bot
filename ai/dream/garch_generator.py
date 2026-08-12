import numpy as np
import pandas as pd
from arch import arch_model

class GARCHGenerator:
    def __init__(self, returns):
        self.model = arch_model(returns, vol='Garch', p=1, q=1)
        self.res = self.model.fit(disp='off')

    def generate(self, n_steps=100, n_paths=100):
        # Simulate from fitted GARCH
        sim = self.res.forecast(horizon=n_steps, simulations=n_paths)
        paths = sim.simulations.values[-1, :, :]  # shape (n_paths, n_steps)
        return paths
