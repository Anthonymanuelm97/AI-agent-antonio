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

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_order",
            "description": (
                "Always call this tool whenever a customer asks how much one "
                "or more products cost, asks for the price of an order, or "
                "wants to know the total cost of multiple products. This "
                "includes questions such as 'How much is a coffee?', 'How "
                "much would two cookies cost?', 'What would be the price of "
                "2 cold brews and 3 cookies?', and 'How much would my order "
                "cost?' or any similar price calculation. Include every "
                "requested product and quantity; use quantity 1 when a "
                "single product is asked about without a quantity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": (
                            "The products and quantities to include in the "
                            "price calculation."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "product": {
                                    "type": "string",
                                    "description": "The product name.",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": (
                                        "The quantity of the product."
                                    ),
                                },
                            },
                            "required": ["product", "quantity"],
                        },
                    }
                },
                "required": ["items"],
            },
        },
    }
]


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


def execute_tool(name, arguments):
    if name == "calculate_order":
        return calculate_order(arguments["items"])

    return f"The requested tool '{name}' does not exist."
