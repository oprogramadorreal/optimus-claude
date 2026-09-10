class Catalog:
    def __init__(self, items):
        self.items = items

    def lookup(self, identifier):
        return self.items.get(identifier)
