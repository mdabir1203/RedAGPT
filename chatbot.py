"""Streamlit application for RedAGPT."""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import streamlit as st
import tldextract
import validators
import whois
from dotenv import load_dotenv
from PIL import Image

from tools.login_checker import LoginChecker
from tools.payments import StripeCheckoutError, create_checkout_session

BASE_DIR = Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / "imgs"
AUDIO_DIR = BASE_DIR / "audio"


@dataclass
class StripeConfig:
    price_id: Optional[str]
    success_url: str
    cancel_url: str

    @classmethod
    def from_env(cls) -> "StripeConfig":
        return cls(
            price_id=os.getenv("STRIPE_PRICE_ID"),
            success_url=os.getenv("STRIPE_SUCCESS_URL", "https://example.com/success"),
            cancel_url=os.getenv("STRIPE_CANCEL_URL", "https://example.com/cancel"),
        )


def _get_image_bytes(image_path: Path) -> Optional[bytes]:
    if not image_path.exists():
        return None
    return image_path.read_bytes()


def _set_background(image_path: Path) -> None:
    image_bytes = _get_image_bytes(image_path)
    if not image_bytes:
        return

    encoded = base64.b64encode(image_bytes).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url('data:image/png;base64,{encoded}');
            background-size: cover;
            background-position: center;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _play_sidebar_audio(audio_path: Path) -> None:
    if not audio_path.exists():
        return
    st.sidebar.audio(audio_path.read_bytes(), format="audio/mp3", start_time=0)


def is_corporate_or_government_target(url: str) -> bool:
    """Return True if the target is likely to be corporate or government owned."""

    try:
        ext = tldextract.extract(url)
    except Exception:
        return False

    tld = ext.suffix.lower()
    if tld in {"gov", "mil"}:
        return True

    if tld in {"com", "org", "net"}:
        try:
            domain = url.split("//")[-1].split("/")[0]
            info = whois.whois(domain)
            if info and getattr(info, "name", None):
                name_value = str(info.name).lower()
                if "government" in name_value or ".gov" in name_value:
                    return True
        except Exception:
            # WHOIS lookups can fail for many reasons; treat as non-government.
            return False

    return False


def _render_feature_grid() -> None:
    st.subheader("Why security teams trust RedAGPT")
    cols = st.columns(3)
    features = [
        ("Autonomous testing", "LangChain AutoGPT orchestrates full login audits with zero setup."),
        ("Actionable reporting", "Generate remediation-ready security summaries for every run."),
        ("Compliance guardrails", "Automatic checks prevent scans on sensitive or disallowed targets."),
    ]
    for col, (title, body) in zip(cols, features):
        with col:
            st.markdown(f"### {title}")
            st.write(body)


def _render_stripe_cta(config: StripeConfig) -> None:
    st.markdown("---")
    st.subheader("Launch unlimited audits")
    st.write(
        "Unlock RedAGPT Pro for unlimited automated login form tests, priority support, and early access to tooling upgrades."
    )

    if not config.price_id:
        st.info(
            "Configure STRIPE_PRICE_ID, STRIPE_SUCCESS_URL, and STRIPE_CANCEL_URL to enable checkout."
        )
        return

    if st.button("Subscribe securely with Stripe", type="primary"):
        try:
            checkout_url = create_checkout_session(
                price_id=config.price_id,
                success_url=config.success_url,
                cancel_url=config.cancel_url,
            )
            st.session_state["checkout_url"] = checkout_url
            st.success("Checkout session created. Complete your subscription below.")
        except StripeCheckoutError as exc:
            st.error(str(exc))

    checkout_url = st.session_state.get("checkout_url")
    if checkout_url:
        st.link_button("Open secure Stripe checkout", checkout_url, type="secondary")


def render_landing_page() -> None:
    st.title("RedAGPT Security Suite")
    st.write(
        "Automate login form penetration testing with production-ready guardrails."
    )

    _render_feature_grid()

    st.markdown(
        """
        #### Built for scale
        * Queue AI-driven investigations while your team focuses on remediation.
        * Store structured findings in Redis or fall back to in-memory FAISS automatically.
        * Deploy in minutes with `.env` driven configuration.
        """
    )

    _render_stripe_cta(StripeConfig.from_env())


def _validate_target(url: str, mode: str) -> Optional[str]:
    if not validators.url(url):
        return "Please provide a valid URL, including the scheme (e.g. https://example.com/login)."

    if mode == "Remote" and is_corporate_or_government_target(url):
        return "Remote scans are restricted for corporate or government-owned targets."

    return None


def _display_run_results(checker: LoginChecker) -> None:
    summary_path = Path(checker.summary_file_path)
    log_path = Path(checker.logging_file_path)

    if summary_path.exists():
        summary_text = summary_path.read_text(encoding="utf-8")
        st.success("Audit completed successfully.")
        st.markdown("#### Security summary")
        st.write(summary_text)
        st.download_button(
            "Download report",
            data=summary_text,
            file_name=summary_path.name,
            mime="text/plain",
        )
    else:
        st.error("Audit failed — no summary was generated.")

    if log_path.exists():
        with st.expander("Execution log", expanded=False):
            st.code(log_path.read_text(encoding="utf-8") or "Log file was empty.")


def render_security_audit() -> None:
    st.header("Login form penetration test")
    st.write(
        "Provide a login form URL to orchestrate an automated penetration test with RedAGPT."
    )

    mode = st.radio("Target location", ["Local", "Remote"], horizontal=True)
    url = st.text_input("Login form URL", placeholder="https://your-app/login")

    if st.button("Run security audit", type="primary"):
        error = _validate_target(url, mode)
        if error:
            st.error(error)
            return

        try:
            checker = LoginChecker(url)
        except EnvironmentError as exc:
            st.error(str(exc))
            return

        with st.spinner("Running autonomous security audit. This can take several minutes..."):
            try:
                checker.run()
            except Exception as exc:  # pragma: no cover - surfaced to UI
                st.error(f"Audit failed: {exc}")
                return

        _display_run_results(checker)


def main() -> None:
    load_dotenv()

    icon_path = IMG_DIR / "web_icon.png"
    icon_image = Image.open(icon_path) if icon_path.exists() else None
    st.set_page_config(
        page_title="RedAGPT Security Suite",
        page_icon=icon_image,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _set_background(IMG_DIR / "bg_img.jpg")
    _play_sidebar_audio(AUDIO_DIR / "blade_soundtrack.mp3")

    page = st.sidebar.radio("Navigation", ["Overview", "Security audit"], index=0)

    if page == "Overview":
        render_landing_page()
    else:
        render_security_audit()

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "Need help? Email **support@redagpt.io** for onboarding assistance."
    )


if __name__ == "__main__":
    main()
