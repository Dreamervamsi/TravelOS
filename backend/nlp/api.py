from .spacy_extractor import extract_spacy
from .contract import to_travel_blueprint


def extract_travel_blueprint(text):
    """Extract text and return a draft while required details are being collected."""
    return to_travel_blueprint(extract_spacy(text))


__all__ = ["extract_spacy", "extract_travel_blueprint", "to_travel_blueprint"]
