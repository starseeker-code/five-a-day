from decimal import Decimal


class PricingService:
    """Centralized pricing logic. SiteConfiguration is the single source of truth."""

    @staticmethod
    def get_config():
        from billing.models import SiteConfiguration

        return SiteConfiguration.get_config()

    @staticmethod
    def get_monthly_fee(schedule_type, config=None):
        """Get the monthly fee for a given schedule type."""
        if config is None:
            config = PricingService.get_config()
        fees = {
            "full_time": config.full_time_monthly_fee,
            "part_time": config.part_time_monthly_fee,
            "adult_group": config.adult_group_monthly_fee,
        }
        return fees.get(schedule_type, config.full_time_monthly_fee)

    @staticmethod
    def get_enrollment_fee(is_adult, config=None):
        """Get the enrollment fee based on student type."""
        if config is None:
            config = PricingService.get_config()
        return config.adult_enrollment_fee if is_adult else config.children_enrollment_fee

    @staticmethod
    def calculate_quarterly_price(config=None):
        """Calculate the quarterly base price (3 months * full_time - discount%)."""
        if config is None:
            config = PricingService.get_config()
        base = config.full_time_monthly_fee * 3
        discount = base * (config.quarterly_enrollment_discount / Decimal("100"))
        return base - discount
