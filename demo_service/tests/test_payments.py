import pytest

from demo_service.app.payments import total_cents


def test_discount():
    assert total_cents(10000, 1000) == 9000


def test_zero():
    assert total_cents(0) == 0


@pytest.mark.parametrize("subtotal,discount", [(-1, 0), (100, 10001), (100, -1)])
def test_invalid(subtotal, discount):
    with pytest.raises(ValueError):
        total_cents(subtotal, discount)
