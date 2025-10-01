"""Utilities for handling Stripe checkout sessions."""
from __future__ import annotations

import os
from dataclasses import dataclass

import stripe


class StripeCheckoutError(RuntimeError):
    """Raised when the application cannot create a checkout session."""


@dataclass
class StripeCredentials:
    api_key: str
    price_id: str
    success_url: str
    cancel_url: str


def _load_credentials(price_id: str, success_url: str, cancel_url: str) -> StripeCredentials:
    api_key = os.getenv("STRIPE_API_KEY")
    if not api_key:
        raise StripeCheckoutError(
            "STRIPE_API_KEY must be configured to create Stripe checkout sessions."
        )

    if not price_id:
        raise StripeCheckoutError("A Stripe price identifier is required.")

    return StripeCredentials(
        api_key=api_key,
        price_id=price_id,
        success_url=success_url,
        cancel_url=cancel_url,
    )


def create_checkout_session(*, price_id: str, success_url: str, cancel_url: str) -> str:
    """Create a Stripe checkout session and return the hosted URL."""

    credentials = _load_credentials(price_id, success_url, cancel_url)
    stripe.api_key = credentials.api_key

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": credentials.price_id, "quantity": 1}],
            success_url=credentials.success_url,
            cancel_url=credentials.cancel_url,
        )
    except Exception as exc:  # pragma: no cover - relies on external API
        raise StripeCheckoutError(f"Failed to create checkout session: {exc}") from exc

    if not session.url:
        raise StripeCheckoutError("Stripe did not return a checkout URL.")

    return session.url


__all__ = ["StripeCheckoutError", "create_checkout_session"]
