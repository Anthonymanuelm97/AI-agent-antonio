import json
from pathlib import Path


_BUSINESS_DATA_PATH = Path(__file__).resolve().parent.parent / "business_data.json"


def load_business_data():
    with _BUSINESS_DATA_PATH.open(encoding="utf-8") as business_data_file:
        return json.load(business_data_file)

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
HERRAMIENTAS = TOOLS


def calculate_order(items):
    business_data = load_business_data()
    menu = {
        item["name"].strip().lower(): item
        for category in business_data["menu"]["categories"]
        for item in category["items"]
    }
    currency = business_data["business"]["currency"]["display"]
    order_details = []
    total = 0

    for item in items:
        product = item["product"].strip().lower()
        quantity = item["quantity"]

        if product not in menu:
            return f"{item['product']} is not available on the menu."

        menu_item = menu[product]
        subtotal = menu_item["price"] * quantity
        total += subtotal
        order_details.append(
            f"{quantity} x {menu_item['name']} = {currency}{subtotal}"
        )

    return (
        "\n".join(order_details)
        + f"\n\nTotal: {currency}{total}"
        + "\n\nPrices are for reference only and are subject to confirmation."
    )


def execute_tool(name, arguments):
    if name == "calculate_order":
        if not isinstance(arguments, dict) or "items" not in arguments:
            return "The calculate_order tool request is missing required items."
        try:
            return calculate_order(arguments["items"])
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return "The order could not be calculated from the available business data."

    return f"The requested tool '{name}' does not exist."
