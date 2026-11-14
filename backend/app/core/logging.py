import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure consistent application-wide logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
