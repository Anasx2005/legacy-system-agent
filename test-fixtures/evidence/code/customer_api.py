"""Tiny fictional legacy Customer API."""


class CustomerApi:
    """The current application component serving customer data."""

    legacy_service_alias = "customer-api"

    def get_customer(self, customer_id: str) -> dict[str, str]:
        return {"id": customer_id, "status": "active"}
