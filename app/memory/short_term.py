from typing import Optional, List

class SimpleMessage:
    """Simple message class to mimic LangChain message interface."""
    def __init__(self, content: str, type: str):
        self.content = content
        self.type = type

class HumanMessage(SimpleMessage):
    def __init__(self, content: str):
        super().__init__(content, "human")

class AIMessage(SimpleMessage):
    def __init__(self, content: str):
        super().__init__(content, "ai")

class ShortTermMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._messages: List[SimpleMessage] = []

    def save_context(self, inputs: dict, outputs: dict):
        input_text = inputs.get("input", "")
        output_text = outputs.get("output", "")
        self._messages.append(HumanMessage(input_text))
        self._messages.append(AIMessage(output_text))

    def get_messages(self):
        return self._messages

    def get_context(self) -> str:
        history = []
        for msg in self._messages:
            if isinstance(msg, HumanMessage):
                history.append(f"Human: {msg.content}")
            elif isinstance(msg, AIMessage):
                history.append(f"AI: {msg.content}")
        return "\n".join(history)

    def clear(self):
        self._messages.clear()

_short_term_stores: dict = {}

def get_short_term_memory(session_id: str) -> ShortTermMemory:
    if session_id not in _short_term_stores:
        _short_term_stores[session_id] = ShortTermMemory(session_id)
    return _short_term_stores[session_id]