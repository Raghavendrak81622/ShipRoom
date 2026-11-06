"""Payment amounts are integer cents; discounts use basis points."""


def total_cents(subtotal, discount_bps=0):
    if not isinstance(subtotal, int) or subtotal < 0:
        raise ValueError("subtotal must be nonnegative integer cents")
    if not isinstance(discount_bps, int) or not 0 <= discount_bps <= 10000:
        raise ValueError("discount must be 0..10000 basis points")
    return subtotal * (10000 - discount_bps) // 10000
