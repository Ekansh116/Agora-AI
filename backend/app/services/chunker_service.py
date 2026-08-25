from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import timedelta

class ChunkerStrategy(ABC):
    @abstractmethod
    def chunk(self, messages: List[Dict]) -> List[List[Dict]]:
        """
        Group a list of message dicts into sub-lists (conversations).
        Each message in the list must have keys: 'timestamp' (datetime), 'sender' (str), 'content' (str)
        """
        pass

class TimeGapMessageCountChunkerStrategy(ChunkerStrategy):
    def __init__(self, max_gap_minutes: float = 15.0, max_messages: int = 50):
        self.max_gap = timedelta(minutes=max_gap_minutes)
        self.max_messages = max_messages

    def chunk(self, messages: List[Dict]) -> List[List[Dict]]:
        if not messages:
            return []
        
        # Sort messages by timestamp chronologically
        sorted_messages = sorted(messages, key=lambda m: m["timestamp"])
        
        chunks = []
        current_chunk = [sorted_messages[0]]
        
        for msg in sorted_messages[1:]:
            prev_msg = current_chunk[-1]
            time_gap = msg["timestamp"] - prev_msg["timestamp"]
            
            # Start new chunk if gap is too large or message limit is reached
            if time_gap > self.max_gap or len(current_chunk) >= self.max_messages:
                chunks.append(current_chunk)
                current_chunk = [msg]
            else:
                current_chunk.append(msg)
                
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

class ConversationChunker:
    def __init__(self, strategy: ChunkerStrategy = None):
        self.strategy = strategy or TimeGapMessageCountChunkerStrategy()

    def chunk_messages(self, messages: List[Dict]) -> List[List[Dict]]:
        return self.strategy.chunk(messages)
