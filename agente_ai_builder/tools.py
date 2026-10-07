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
            "name": "get_menu",
            "description": (
                "Always use this tool when a customer asks what products "
                "are on the menu, what products are registered, or asks to "
                "see the menu. In the customer-facing response, list every "
                "returned product together with its listed price; do not "
                "omit prices just because the customer did not explicitly "
                "ask for them. Clearly explain that the returned entries and "
                "prices are unverified reference data."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_order",
            "description": (
                "Always call this tool when a customer asks the price or "
                "total cost of one or more specifically identified menu "
                "products or an order. Include every requested product and "
                "quantity; use quantity 1 when a specific product is asked "
                "about without a quantity. If the customer uses a generic "
                "or ambiguous product name that does not exactly identify a "
                "menu entry, call get_menu first and clarify the intended "
                "product instead of guessing."
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


def get_menu():
    business_data = load_business_data()
    currency = business_data["business"]["currency"]["display"]
    menu = business_data["menu"]
    lines = [
        "Menu entries (reference information; availability and prices are "
        "not verified):"
    ]

    for category in menu["categories"]:
        items = category["items"]
        if not items:
            continue

        lines.append(f"\n{category['name']}:")
        for item in items:
            price = item.get("price")
            price_text = (
                f"{currency}{price}" if price is not None else "price unavailable"
            )
            lines.append(f"- {item['name']}: {price_text}")

    if len(lines) == 1:
        return "There are no menu products configured in the business data."

    lines.append("\nThese entries are unverified reference information.")
    return "\n".join(lines)


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
    if name == "get_menu":
        try:
            return get_menu()
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return "The menu could not be retrieved from the available business data."

    if name == "calculate_order":
        if not isinstance(arguments, dict) or "items" not in arguments:
            return "The calculate_order tool request is missing required items."
        try:
            return calculate_order(arguments["items"])
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return "The order could not be calculated from the available business data."

    return f"The requested tool '{name}' does not exist."
