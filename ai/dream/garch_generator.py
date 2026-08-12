import numpy as np
import pandas as pd
from arch import arch_model
from scipy.fft import fft, ifft

class GARCHGenerator:
    def __init__(self, returns):
        self.returns = returns
        self.model = arch_model(returns, vol='Garch', p=1, q=1)
        self.res = self.model.fit(disp='off')

    def generate(self, n_steps=100, n_paths=100):
        # Simulate GARCH paths
        sim = self.res.forecast(horizon=n_steps, simulations=n_paths)
        paths = sim.simulations.values[-1, :, :].T  # shape (n_paths, n_steps)

        # Add Fourier surrogate for extra realism (preserve spectrum)
        # For each path, add a small Fourier perturbation
        for i in range(n_paths):
            path = paths[i]
            # Compute FFT, add random phase, invert
            f = fft(path)
            phase_shift = np.exp(1j * 2 * np.pi * np.random.rand(len(path)))
            f_shifted = f * phase_shift
            path_surrogate = np.real(ifft(f_shifted))
            paths[i] = path_surrogate

        return paths
