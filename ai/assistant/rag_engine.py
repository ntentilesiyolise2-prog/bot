import chromadb
from chromadb.utils import embedding_functions
import os
import json
from utils.logger import setup_logger

logger = setup_logger(__name__)

class RAGAssistant:
    def __init__(self, collection_name="bot_knowledge"):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_functions.DefaultEmbeddingFunction()
        )
        self.initialized = False

    async def initialize(self):
        if self.initialized:
            return
        # Load the bot's own documentation into memory
        docs = [
            "NEXUS INFINITUM is a self-evolving trading bot.",
            "It uses LSTM for price prediction and DQN for trade timing.",
            "Risk is managed via VaR, CVaR, and Monte Carlo simulations.",
            "The bot has an Auto-Trade engine that executes based on confluence scores.",
            "It supports Telegram alerts and MT5 execution.",
            "The UI has 5 tabs: Quotes, Chart, Trade, History, Settings.",
            "The AI Chart Scanner uses YOLO to detect candlestick patterns.",
            "The Oracle Whisper provides LLM-based explanations.",
            "The bot can run in paper or live trading mode.",
            "Configuration is stored in config.json and .env."
        ]
        try:
            self.collection.add(
                documents=docs,
                ids=[f"doc_{i}" for i in range(len(docs))]
            )
            self.initialized = True
            logger.info(f"RAG Assistant initialized with {len(docs)} documents.")
        except Exception as e:
            logger.error(f"RAG init error: {e}")

    async def query(self, question: str) -> str:
        if not self.initialized:
            return "Assistant is still loading. Please wait."
        try:
            results = self.collection.query(query_texts=[question], n_results=3)
            context = "\n".join(results['documents'][0])
            # For a real answer, we would call an LLM with this context.
            # For now, we return the context directly.
            return f"Context:\n{context}\n\n(LLM response generation coming soon with Groq/Ollama integration)"
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            return "I couldn't find an answer right now."
