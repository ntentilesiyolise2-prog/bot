import random
import numpy as np
import pandas as pd
from copy import deepcopy
from utils.logger import setup_logger
logger = setup_logger(__name__)

class AlphaForge:
    def __init__(self, population_size=50, mutation_rate=0.2):
        self.population = []
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.best_fitness = -999

    def _generate_random_strategy(self):
        """Generate a random mathematical formula as a strategy."""
        # Base indicators available
        indicators = ['rsi_14', 'ema_9', 'ema_21', 'macd', 'atr_14', 'adx', 'bb_high', 'bb_low']
        ops = ['+', '-', '*', '/']
        
        # Build a random expression tree (simplified)
        term1 = random.choice(indicators)
        term2 = random.choice(indicators)
        op = random.choice(ops)
        
        # Create a simple expression: e.g., rsi_14 * ema_9
        # We'll evaluate this on a DataFrame
        expr = f"({term1} {op} {term2})"
        # Add a threshold
        threshold = random.uniform(0, 100)
        direction = random.choice(['BUY', 'SELL'])
        
        return {
            'expr': expr,
            'threshold': threshold,
            'direction': direction,
            'name': f"gen_{random.randint(1000,9999)}"
        }

    def _evaluate_strategy(self, strategy, df):
        """Test a strategy on historical data and return Sharpe ratio."""
        try:
            # Evaluate the expression on the DataFrame
            # We use a simple proxy: compute the value of the expression
            # If value > threshold, trigger signal
            # We'll simulate a 5-bar hold
            signal = eval(strategy['expr'])  # Simplified! In production, use pandas eval safely.
            if not isinstance(signal, pd.Series):
                return 0.0
            
            # Simulate PnL: if signal > threshold, enter trade
            entry_signal = signal > strategy['threshold']
            # Backtest: long or short based on direction
            # For simplicity, we calculate average return
            returns = df['Close'].pct_change().shift(-1)
            pnl = (returns * entry_signal).sum()
            # Maximize Sharpe
            sharpe = pnl / (returns.std() + 1e-6)
            return abs(sharpe)  # We want high absolute performance
        except Exception as e:
            return 0.0

    def evolve(self, df, generations=10):
        """Evolve new strategies over multiple generations."""
        # Initialize population
        for _ in range(self.population_size):
            self.population.append(self._generate_random_strategy())
        
        for gen in range(generations):
            fitness_scores = []
            for strat in self.population:
                fit = self._evaluate_strategy(strat, df)
                fitness_scores.append(fit)
                strat['fitness'] = fit
            
            # Sort by fitness
            sorted_pop = sorted(self.population, key=lambda x: x['fitness'], reverse=True)
            self.population = sorted_pop[:self.population_size//2]
            self.best_fitness = self.population[0]['fitness']
            
            logger.info(f"Generation {gen}: Best Fitness = {self.best_fitness:.4f}")
            
            # Crossover and mutation
            new_pop = self.population.copy()
            while len(new_pop) < self.population_size:
                parent1 = random.choice(self.population)
                parent2 = random.choice(self.population)
                child = self._crossover(parent1, parent2)
                child = self._mutate(child)
                new_pop.append(child)
            self.population = new_pop
        
        # Return the best strategy found
        best = max(self.population, key=lambda x: x.get('fitness', 0))
        logger.info(f"Best strategy found: {best['name']} with fitness {best['fitness']}")
        return best

    def _crossover(self, p1, p2):
        child = {}
        if random.random() > 0.5:
            child['expr'] = p1['expr']
            child['threshold'] = p2['threshold']
        else:
            child['expr'] = p2['expr']
            child['threshold'] = p1['threshold']
        child['direction'] = random.choice([p1['direction'], p2['direction']])
        child['name'] = f"gen_{random.randint(1000,9999)}"
        return child

    def _mutate(self, child):
        if random.random() < self.mutation_rate:
            child['threshold'] += random.uniform(-5, 5)
            child['threshold'] = max(0, min(100, child['threshold']))
        if random.random() < self.mutation_rate / 2:
            child['direction'] = 'BUY' if child['direction'] == 'SELL' else 'SELL'
        return child
