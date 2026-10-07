import json
from pathlib import Path


_BUSINESS_DATA_PATH = Path(__file__).resolve().parent.parent / "business_data.json"

with _BUSINESS_DATA_PATH.open(encoding="utf-8") as business_data_file:
    _business_data = json.load(business_data_file)

_MENU = {
    item["name"].strip().lower(): item
    for category in _business_data["menu"]["categories"]
    for item in category["items"]
}


def calculate_order(items):
    order_details = []
    total = 0

    for item in items:
        product = item["product"].strip().lower()
        quantity = item["quantity"]

        if product not in _MENU:
            return f"{item['product']} is not available on the menu."

        menu_item = _MENU[product]
        subtotal = menu_item["price"] * quantity
        total += subtotal
        order_details.append(
            f"{quantity} x {menu_item['name']} = RD${subtotal}"
        )

    return (
        "\n".join(order_details)
        + f"\n\nTotal: RD${total}"
        + "\n\nPrices are for reference only and are subject to confirmation."
    )
