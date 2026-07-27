class CustomerApi:
    def get_customer(self, customer_id: str) -> dict:
        return {"id": customer_id, "name": "Example Customer"}