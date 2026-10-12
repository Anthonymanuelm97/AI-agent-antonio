from .data_access import load_business_data, save_order_record


def create_order(customer_name, items):
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
    return f"Order {order_id} was registered successfully with status Confirmed."


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
