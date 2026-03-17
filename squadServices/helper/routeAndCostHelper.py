from squadServices.models.rateManagementModel.customerRate import CustomerRate
from squadServices.models.rateManagementModel.vendorRate import VendorRate
from squadServices.models.routeManager.customRoute import CustomRoute
from squadServices.models.transaction.transaction import (
    ClientTransaction,
    VendorTransaction,
)


def get_route_and_cost(originating_client, destination_country):
    """
    Finds the route and cost using ONLY the Country Code (Flat Rate Routing).
    """
    print("================== SMS Client ID ==================", originating_client.id)
    print("================== SMS Country ID =================", destination_country.id)

    # 1. FIND THE ROUTE (Ignoring the operator)
    route = CustomRoute.objects.filter(
        orginatingClient=originating_client,
        country=destination_country,
        status="ACTIVE",
        isDeleted=False,
    ).first()
    print("==================get_route_and_cost=================", route)

    if not route:
        return None, f"No active route found for {destination_country.name}."

    vendor = route.terminatingVendor
    terminatingCompany = route.terminatingCompany

    client = route.orginatingClient
    clientCompany = route.orginatingCompany
    mnc_value = route.operator.MNC if route.operator else "All"
    if not vendor.ratePlanName:
        return None, f"Vendor '{vendor.profileName}' has no ratePlan assigned."

    # 2. SANITIZE THE MCC
    try:
        mcc_integer = int(str(destination_country.MCC).strip())
        mccClient = int(str(clientCompany.country.MCC).strip())
    except (ValueError, TypeError):
        return None, f"Invalid MCC format in Country '{destination_country.name}'."

    # 3. FIND THE COST (Country-level only!)
    rate_entry = (
        VendorRate.objects.filter(
            ratePlan=vendor.ratePlanName,
            MCC=mcc_integer,
            # We no longer filter by MNC. We just take the rate assigned to the MCC.
            isDeleted=False,
        )
        .order_by("-createdAt")
        .first()
    )

    customerRateEntry = (
        CustomerRate.objects.filter(
            ratePlan=client.ratePlanName,
            MCC=mcc_integer,
            isDeleted=False,
        )
        .order_by("-createdAt")
        .first()
    )

    if not rate_entry or not rate_entry.rate:
        return (
            None,
            f"No price configured in vendor rate plan '{vendor.ratePlanName}' for Country {destination_country.name}.",
        )

    if not customerRateEntry or not customerRateEntry.rate:
        return (
            None,
            f"No price configured in client rate plan '{client.ratePlanName}' for Country {clientCompany.country.name}.",
        )

    smpp_config = vendor.smpp
    # Success!
    return {
        "vendor": vendor,
        "client": client,
        "terminatingCompany": terminatingCompany,
        "vendor_cost": rate_entry.rate,
        "client_cost": customerRateEntry.rate,
        "route_id": route.id,
        "smpp": smpp_config,
        "country_code": mcc_integer,
        "mnc": mnc_value,
    }, None
