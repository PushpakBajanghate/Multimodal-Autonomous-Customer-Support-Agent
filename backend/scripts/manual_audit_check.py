import httpx
import json

BASE = 'http://127.0.0.1:8000/api/v1'

def run_checks():
    client = httpx.Client()
    print("==================================================")
    print("1. TRACK ORDER #1")
    print("==================================================")
    r1 = client.get(f"{BASE}/orders/1/tracking")
    print(f"HTTP Status: {r1.status_code}")
    print(json.dumps(r1.json(), indent=2))

    # Find a shipped order
    shipped_order = None
    for cid in range(1, 16):
        res = client.get(f"{BASE}/customers/{cid}/orders").json()
        orders = res.get("data", [])
        shipped_order = next((o for o in orders if o["status"] == "shipped"), None)
        if shipped_order:
            break

    print("\n==================================================")
    print("2. ATTEMPT REFUND ON INELIGIBLE (SHIPPED) ORDER")
    print("==================================================")
    if shipped_order:
        oid = shipped_order["id"]
        r2 = client.post(f"{BASE}/orders/{oid}/refund", json={"reason": "Item defective"})
        print(f"Target: Order #{oid} (Current Status: '{shipped_order['status']}')")
        print(f"HTTP Status: {r2.status_code}")
        print(json.dumps(r2.json(), indent=2))

    print("\n==================================================")
    print("3. ATTEMPT CANCELLATION ON NON-CANCELLABLE (SHIPPED) ORDER")
    print("==================================================")
    if shipped_order:
        oid = shipped_order["id"]
        r3 = client.post(f"{BASE}/orders/{oid}/cancel", json={"reason": "Customer changed mind"})
        print(f"Target: Order #{oid} (Current Status: '{shipped_order['status']}')")
        print(f"HTTP Status: {r3.status_code}")
        print(json.dumps(r3.json(), indent=2))

if __name__ == "__main__":
    run_checks()
