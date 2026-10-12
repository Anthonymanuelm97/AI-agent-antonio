from .data_access import load_business_data, save_order_record

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
            "name": "get_business_information",
            "description": (
                "Always use this tool when a customer asks about business "
                "services, branches, location, contact details, or feedback. "
                "Use only the relevant returned information to answer, and "
                "do not invent details that are not listed."
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
            "name": "save_order",
            "description": (
                "After the customer explicitly confirms they want to place "
                "the order, call this tool exactly once. Never call it again "
                "for the same order. Do not use it for price questions, "
                "quotes, or order calculations alone."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "The customer's name.",
                    },
                    "items": {
                        "type": "array",
                        "description": "Confirmed products and quantities.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product": {
                                    "type": "string",
                                    "description": "The product name.",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "description": "The quantity ordered.",
                                },
                            },
                            "required": ["product", "quantity"],
                        },
                    },
                },
                "required": ["customer_name", "items"],
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


def save_order(customer_name, items):
    if not isinstance(customer_name, str) or not customer_name.strip():
        raise ValueError("A customer name is required to save an order.")
    if not isinstance(items, list) or not items:
        raise ValueError("At least one order item is required.")

    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each order item must include a product and quantity.")
        product = item.get("product")
        quantity = item.get("quantity")
        if not isinstance(product, str) or not product.strip():
            raise ValueError("Each order item must include a product name.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Each order item must have a positive integer quantity.")

    try:
        _, item_descriptions, total, _ = _calculate_order(items)
    except ValueError as error:
        return f"Order was not saved: {error}"

    order_id = save_order_record(
        customer_name.strip(),
        ", ".join(item_descriptions),
        total,
    )
    return f"Order {order_id} was registered successfully with status Pending."


def get_business_information():
    business_data = load_business_data()
    information = business_data["information"]
    if not information:
        return "There is no business information configured."

    return "\n".join(
        f"- {item['topic']}: {item['detail']}"
        for item in information
    )


def get_menu():
    business_data = load_business_data()
    currency = business_data["currency"]
    products = business_data["products"]
    lines = [
        "Menu entries (reference information; availability and prices are "
        "not verified):"
    ]

    for category in dict.fromkeys(product["category"] for product in products):
        items = [
            product for product in products if product["category"] == category
        ]
        lines.append(f"\n{category}:")
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


def _calculate_order(items):
    business_data = load_business_data()
    menu = {
        item["name"].strip().lower(): item
        for item in business_data["products"]
    }
    currency = business_data["currency"]
    order_details = []
    item_descriptions = []
    total = 0

    for item in items:
        product = item["product"].strip().lower()
        quantity = item["quantity"]

        if product not in menu:
            raise ValueError(
                f"{item['product']} is not available on the menu."
            )

        menu_item = menu[product]
        subtotal = menu_item["price"] * quantity
        total += subtotal
        order_details.append(
            f"{quantity} x {menu_item['name']} = {currency}{subtotal}"
        )
        item_descriptions.append(f"{quantity} x {item['product'].strip()}")

    return order_details, item_descriptions, total, currency


def calculate_order(items):
    try:
        order_details, _, total, currency = _calculate_order(items)
    except ValueError as error:
        return str(error)

    return (
        "\n".join(order_details)
        + f"\n\nTotal: {currency}{total}"
        + "\n\nPrices are for reference only and are subject to confirmation."
    )


def execute_tool(name, arguments):
    if name == "save_order":
        if not isinstance(arguments, dict):
            return "The save_order tool request must be an object."
        required_arguments = ("customer_name", "items")
        if any(argument not in arguments for argument in required_arguments):
            return "The save_order tool request is missing required order details."
        try:
            return save_order(
                arguments["customer_name"],
                arguments["items"],
            )
        except (OSError, KeyError, TypeError, ValueError):
            return "The order could not be registered in the orders workbook."

    if name == "get_business_information":
        try:
            return get_business_information()
        except (OSError, KeyError, TypeError, ValueError):
            return (
                "Business information could not be retrieved from the "
                "available business data."
            )

    if name == "get_menu":
        try:
            return get_menu()
        except (OSError, KeyError, TypeError, ValueError):
            return "The menu could not be retrieved from the available business data."

    if name == "calculate_order":
        if not isinstance(arguments, dict) or "items" not in arguments:
            return "The calculate_order tool request is missing required items."
        try:
            return calculate_order(arguments["items"])
        except (OSError, KeyError, TypeError, ValueError):
            return "The order could not be calculated from the available business data."

    return f"The requested tool '{name}' does not exist."
