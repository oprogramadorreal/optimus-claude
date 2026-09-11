def normalize(identifier):
    return identifier.strip() if identifier is not None else None


class Catalog:
    def __init__(self, items):
        self.items = items

    def lookup(self, identifier):
        return self.items.get(identifier)


def route(identifier, catalog):
    normalized = normalize(identifier)
    return catalog.lookup(identifier)
