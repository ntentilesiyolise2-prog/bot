import os
from openai import OpenAI
from utils.logger import setup_logger

logger = setup_logger(__name__)

class OracleWhisper:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "groq")
        if self.provider == "groq":
            self.client = OpenAI(
                api_key=os.getenv("GROQ_API_KEY"),
                base_url="https://api.groq.com/openai/v1"
            )
            self.model = "llama3-70b-8192"
        elif self.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            self.client = None
        else:
            # Ollama
            self.client = OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama"
            )
            self.model = "llama3"

    async def initialize(self):
        logger.info(f"Oracle Whisper initialized with provider: {self.provider}")

    def generate(self, signal, features=None):
        try:
            if self.provider == "gemini":
                prompt = self._build_prompt(signal, features)
                response = self.model.generate_content(prompt)
                return response.text.strip()
            else:
                messages = [
                    {"role": "system", "content": "You are a professional trading assistant. Explain trading signals in clear, concise language."},
                    {"role": "user", "content": self._build_prompt(signal, features)}
                ]
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=100
                )
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Oracle Whisper error: {e}")
            return f"Signal: {signal.get('direction', 'HOLD')} with {signal.get('confluence', 0)}% confluence."

    def _build_prompt(self, signal, features):
        direction = signal.get('direction', 'HOLD')
        confluence = signal.get('confluence', 0)
        symbol = signal.get('symbol', 'UNKNOWN')
        explanation = signal.get('explanation', 'No additional context.')
        return f"Symbol: {symbol}\nDirection: {direction}\nConfidence: {confluence}%\nExplanation: {explanation}\n\nProvide a 1-sentence rationale for this trade signal."
