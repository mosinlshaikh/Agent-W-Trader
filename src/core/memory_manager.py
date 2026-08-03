"""Local memory foundation for trade decisions and agent learning."""

class MemoryManager:
    def __init__(self):
        self.memory = []

    def store(self, record):
        self.memory.append(record)

    def search(self, keyword=None):
        if not keyword:
            return self.memory
        return [item for item in self.memory if keyword in str(item)]
