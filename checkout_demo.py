@'
def calculate_total(price, quantity, discount=0):
    subtotal = price * quantity
    discounted_total = subtotal - (subtotal * discount / 100)
    return round(discounted_total, 2)


def apply_coupon(total, coupon_code):
    coupons = {
        "SAVE10": 10,
        "SAVE20": 20,
    }
    discount = coupons.get(coupon_code, 0)
    return total - (total * discount / 100)


def checkout(price, quantity, discount=0, coupon_code=None):
    total = calculate_total(price, quantity, discount)
    if coupon_code:
        total = apply_coupon(total, coupon_code)
    print("Final amount: ₹" + str(total))
    return total
'@ | Set-Content -Encoding utf8 checkout_demo.py