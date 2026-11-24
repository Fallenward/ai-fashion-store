STORE_DOCUMENTS = [
    {
        "source_id": "shipping",
        "title": "Shipping",
        "content": """Shipping is a flat $8 inside the United States. Orders with a merchandise subtotal of $150 or more ship free. The free-shipping threshold is calculated before promo codes.

Standard delivery takes 3 to 5 business days after the order is marked shipped. We do not currently ship outside the United States. You can track an order from your account once you are signed in. Pending orders have not shipped. Status values are pending, paid, processing, shipped, delivered, cancelled, and refunded.

We do not offer overnight shipping in this shop.""",
    },
    {
        "source_id": "returns",
        "title": "Returns and refunds",
        "content": """Return policy: you may return unworn items with the original tags within 30 days of delivery. Refunds go back to the original payment method after we receive and inspect the return. Shipping fees are non-refundable unless we made an error.

Items marked final sale cannot be returned. To start a return, contact the studio from the contact page and include your order number. Customers can also see order status in the account dashboard. Administrators can mark a paid order refunded, which restores inventory.""",
    },
    {
        "source_id": "faq",
        "title": "Frequently asked questions",
        "content": """What sizes do you carry? Most clothing is offered in XS, S, M, L, and XL. Shoes are listed by their own sizes. Always check the size on the product page, because not every size is in stock.

How do I know something is in stock? The product page shows a quantity for each size and color. The shopping assistant checks the same inventory and will not claim an item is available when the quantity is zero.

Do you restock? Popular sizes are reordered when we can. If a size shows zero, it is unavailable right now.

Can I change an order? Contact us before the order is marked shipped and we will try to help. Shipped orders follow the return policy.

What is the promo code? WELCOME10 takes 10 percent off merchandise. It does not reduce the shipping fee.""",
    },
    {
        "source_id": "brand",
        "title": "Atelier style guide",
        "content": """Atelier is a minimalist fashion house. The palette is black, cream, ivory, navy, olive, sand, camel, and charcoal. We prefer quiet tailoring, good materials, and outfits that can move from day to dinner.

The voice is calm, precise, and warm. Do not use slang, urgency tricks, or invented scarcity. Recommend pieces that are actually in the catalog. A casual dinner outfit is usually a refined top or knit, a tailored trouser or dress, and a simple shoe. Office looks favor shirts, trousers, and a blazer or coat.""",
    },
    {
        "source_id": "privacy",
        "title": "Privacy summary",
        "content": """We store the account details needed to run the shop: name, email, optional phone, shipping addresses, orders, wishlist, and style preferences you choose to save. Style preferences can be edited, cleared, or turned off. We do not ask for government IDs or payment card numbers. Card data, when Stripe is configured, is handled by Stripe and never stored here.

The shopping assistant can read your own style profile, wishlist, and orders when you are signed in. It cannot read another customer's records.""",
    },
]


def product_text(product) -> str:
    colors = []
    sizes = []
    for variant in product.variants:
        if variant.color not in colors:
            colors.append(variant.color)
        if variant.size not in sizes:
            sizes.append(variant.size)
    return "\n".join(
        [
            f"Product: {product.name}",
            f"Brand: {product.brand}",
            f"Category: {product.category.name}",
            f"Indexed price, which may be stale: {product.price}. Confirm the live price with product tools before quoting it.",
            f"Description: {product.description}",
            f"Material: {product.material or 'not listed'}",
            f"Care: {product.care or 'not listed'}",
            f"Colors: {', '.join(colors) or 'not listed'}",
            f"Sizes offered: {', '.join(sizes) or 'not listed'}",
            "Stock changes. Use get_product_inventory or search_products for availability.",
        ]
    )
