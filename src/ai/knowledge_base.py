"""Local trading knowledge base foundation."""

class KnowledgeBase:
    def __init__(self):
        self.entries = []

    def add(self, knowledge):
        self.entries.append(knowledge)

    def search(self, query):
        return [item for item in self.entries if query.lower() in str(item).lower()]
