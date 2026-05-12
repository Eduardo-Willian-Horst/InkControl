from studio.models import StudioBilling


def get_billing() -> StudioBilling:
    return StudioBilling.get_solo()
