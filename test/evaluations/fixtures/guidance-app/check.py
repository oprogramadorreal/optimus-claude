from catalog import Catalog

items = {"AbC": "first", "abc": "second"}
catalog = Catalog(items)
assert catalog.lookup("AbC") == "first"
assert catalog.lookup("abc") == "second"
assert catalog.lookup("missing") is None
print("3 existing checks passed")
