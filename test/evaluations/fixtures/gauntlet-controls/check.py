from app import Catalog, normalize, route

items = {"AbC": "first", "abc": "second"}
catalog = Catalog(items)
assert normalize(" AbC ") == "AbC"
assert catalog.lookup("AbC") == "first"
assert route("AbC", catalog) == "first"
assert route(None, catalog) is None
print("Existing component and basic route checks pass.")
