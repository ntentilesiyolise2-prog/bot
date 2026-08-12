import json
import os
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger(__name__)

LESSONS = {
    "beginner": [
        {"id": 1, "title": "What is a Candlestick?", "content": "Candlesticks show Open, High, Low, Close. They represent price action over a period.", "quiz": [{"q": "What does a green candle mean?", "a": "Price closed higher than it opened"}]},
        {"id": 2, "title": "Support and Resistance", "content": "Support is a price level where buying interest is strong. Resistance is where selling interest is strong.", "quiz": [{"q": "What happens when price breaks resistance?", "a": "It often continues higher"}]},
        {"id": 3, "title": "Fair Value Gaps (FVG)", "content": "FVG are gaps left by aggressive moves. Institutions often fill these gaps.", "quiz": [{"q": "What is an FVG?", "a": "A gap between consecutive candles"}]}
    ],
    "intermediate": [
        {"id": 4, "title": "Order Blocks", "content": "Order blocks are institutional limit order zones where large players place their orders."},
        {"id": 5, "title": "Liquidity Sweeps", "content": "Price moves to take out stops (liquidity) before reversing."}
    ],
    "advanced": [
        {"id": 6, "title": "Causal Inference", "content": "Understanding the root cause of price movements (e.g., oil -> USDJPY)."},
        {"id": 7, "title": "Digital Twin Simulation", "content": "Testing trades in a simulated market before execution."}
    ]
}

class LessonManager:
    def __init__(self):
        self.progress_file = "learning_progress.json"
        self.progress = self._load_progress()

    def _load_progress(self):
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=4)

    def get_lesson(self, level, lesson_id):
        lessons = LESSONS.get(level, [])
        for l in lessons:
            if l['id'] == lesson_id:
                return l
        return None

    def get_next_lesson(self, level, current_id):
        lessons = LESSONS.get(level, [])
        for i, l in enumerate(lessons):
            if l['id'] == current_id:
                if i+1 < len(lessons):
                    return lessons[i+1]
                else:
                    # Move to next level
                    levels = ['beginner', 'intermediate', 'advanced']
                    idx = levels.index(level)
                    if idx+1 < len(levels):
                        return LESSONS[levels[idx+1]][0]
        return None

    def mark_complete(self, user_id, lesson_id):
        key = str(user_id)
        if key not in self.progress:
            self.progress[key] = {'completed': [], 'level': 'beginner'}
        if lesson_id not in self.progress[key]['completed']:
            self.progress[key]['completed'].append(lesson_id)
        self._save_progress()
        return self.progress[key]
