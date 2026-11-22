"""A local mock order API. Start with: python GET_JSON.py."""
from decimal import Decimal
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="Demo Order API", description="Local mock data for a function-calling lab.")
SAMPLE_ORDER_NUMBER = "123456789"


@app.get("/test")
def get_order_status(order_number: Annotated[str | None, Query(pattern=r"^[0-9]{1,32}$")] = None):
    """Return the sample order, or 404 for any other well-formed order number."""
    if order_number is not None and order_number != SAMPLE_ORDER_NUMBER:
        raise HTTPException(status_code=404, detail="Order not found in the demo dataset.")
    value, shipping = Decimal("1999.99"), Decimal("15.99")
    total = value + shipping
    return {
        "DemoData": True,
        "OrderNumber": SAMPLE_ORDER_NUMBER,
        "OrderDate": "2024-07-01",
        "TrackingNumber": "1Z999AA10123456784",
        "EstimatedDeliveryDate": "2024-07-28",
        "OrderStatus": "Shipped",
        "ItemDescription": "Surface Laptop, Copilot+ PC, 13.8 inch, Snapdragon X Elite, Black, 32GB RAM, 1TB SSD",
        "Currency": "USD",
        "OrderValue": float(value),
        "ShippingCosts": float(shipping),
        "OrderTotal": float(total),
        "ShippingPercentageOfTotal": float((shipping / total * 100).quantize(Decimal("0.0001"))),
        "Email": "customer@example.com",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
