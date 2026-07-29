"""Pluggable tax engine. Computes tax breakdown for India (GST) / Nepal (VAT) / None.

Usage:
    from utils.tax import get_tax_engine
    engine = get_tax_engine()
    breakdown = engine.compute_tax_breakdown(subtotal=1000, rate_percent=18, is_interstate=False)
    # breakdown -> dict with tax_amount, components (list), total_with_tax, etc.
"""
from typing import Dict, Optional
from config import get_setting


class BaseTaxEngine:
    name = "None"
    country = "None"

    def compute_tax_breakdown(self, subtotal: float, rate_percent: float = 0.0,
                              is_interstate: bool = False, qty: float = 1.0,
                              unit_price: Optional[float] = None) -> Dict:
        """Return dict: { tax_amount, components: [...], total_with_tax, rate }"""
        if rate_percent <= 0 or subtotal <= 0:
            return {
                "tax_amount": 0.0,
                "components": [],
                "total_with_tax": subtotal,
                "rate": 0.0,
                "system": self.name,
            }
        tax_amount = round(subtotal * rate_percent / 100.0, 2)
        return {
            "tax_amount": tax_amount,
            "components": [{
                "label": f"{self.name} @{rate_percent}%",
                "amount": tax_amount,
                "rate": rate_percent,
            }],
            "total_with_tax": round(subtotal + tax_amount, 2),
            "rate": rate_percent,
            "system": self.name,
        }

    def rates_default(self) -> list:
        return [0.0]

    def format_for_receipt(self, breakdown: Dict, currency_symbol: str = "₹") -> str:
        if breakdown["rate"] <= 0:
            return f"Tax: Not applicable"
        return f"Tax ({self.name} @{breakdown['rate']}%): {currency_symbol}{breakdown['tax_amount']:.2f}"


class NoTaxEngine(BaseTaxEngine):
    name = "None"
    country = "None"


class IndiaTaxEngine(BaseTaxEngine):
    """GST (India): CGST + SGST for intra-state, IGST for inter-state."""
    name = "GST"
    country = "India"

    def compute_tax_breakdown(self, subtotal: float, rate_percent: float = 0.0,
                              is_interstate: bool = False, qty: float = 1.0,
                              unit_price: Optional[float] = None) -> Dict:
        if rate_percent <= 0 or subtotal <= 0:
            return {
                "tax_amount": 0.0, "components": [], "total_with_tax": subtotal,
                "rate": 0.0, "system": self.name,
            }
        total_tax = round(subtotal * rate_percent / 100.0, 2)
        if is_interstate:
            components = [{
                "label": f"IGST @{rate_percent}%",
                "amount": total_tax, "rate": rate_percent,
            }]
        else:
            half = round(total_tax / 2.0, 2)
            components = [
                {"label": f"CGST @{rate_percent/2}%", "amount": half, "rate": rate_percent / 2},
                {"label": f"SGST @{rate_percent/2}%", "amount": half, "rate": rate_percent / 2},
            ]
        return {
            "tax_amount": total_tax,
            "components": components,
            "total_with_tax": round(subtotal + total_tax, 2),
            "rate": rate_percent,
            "system": self.name,
        }

    def rates_default(self) -> list:
        rates = get_setting("tax.india_rates", [0, 5, 12, 18, 28])
        return rates if isinstance(rates, list) and rates else [0, 5, 12, 18, 28]

    def format_for_receipt(self, breakdown: Dict, currency_symbol: str = "₹") -> str:
        if breakdown["rate"] <= 0:
            return "GST: Not applicable"
        lines = []
        for c in breakdown["components"]:
            lines.append(f"  {c['label']}: {currency_symbol}{c['amount']:.2f}")
        return "\n".join(lines) if lines else f"  GST @{breakdown['rate']}%: {currency_symbol}{breakdown['tax_amount']:.2f}"


class NepalTaxEngine(BaseTaxEngine):
    """VAT (Nepal): 13% standard VAT, applies to most goods/services."""
    name = "VAT"
    country = "Nepal"

    def rates_default(self) -> list:
        rates = get_setting("tax.nepal_rates", [0, 13])
        return rates if isinstance(rates, list) and rates else [0, 13]

    def format_for_receipt(self, breakdown: Dict, currency_symbol: str = "Rs.") -> str:
        if breakdown["rate"] <= 0:
            return "VAT: Not applicable"
        return f"VAT @{breakdown['rate']}%: {currency_symbol}{breakdown['tax_amount']:.2f}"


def get_tax_engine() -> BaseTaxEngine:
    """Return the tax engine based on settings. Returns NoTaxEngine if disabled or unknown."""
    tax_enabled = get_setting("feature_flags.tax_system", True)
    if not tax_enabled:
        return NoTaxEngine()
    country = get_setting("country", "India")
    if country == "India":
        return IndiaTaxEngine()
    if country == "Nepal":
        return NepalTaxEngine()
    return NoTaxEngine()


def is_tax_enabled() -> bool:
    return bool(get_setting("feature_flags.tax_system", True))


def get_default_rate() -> float:
    """Default tax rate to use on invoices based on country."""
    country = get_setting("country", "India")
    if country == "India":
        rates = get_setting("tax.india_rates", [0, 5, 12, 18, 28])
        return float(get_setting("tax.india_default_rate", 18 if 18 in rates else rates[-1]))
    if country == "Nepal":
        rates = get_setting("tax.nepal_rates", [0, 13])
        return float(get_setting("tax.nepal_default_rate", 13 if 13 in rates else rates[-1]))
    return 0.0
