from ._shared import *
from .cities import *
from .pipeline import *
from .pipeline import _rule_extract

# ----------------------------------------------------------------------------
def _get_spacy():
    global _SPACY
    if _SPACY is None:
        import spacy
        from spacy.matcher import PhraseMatcher
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            nlp = spacy.blank("en")
        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        matcher.add("CITY", [nlp.make_doc(a) for a in ALIAS_TO_CITY])
        _SPACY = (nlp, matcher)
    return _SPACY


def extract_spacy(text):
    from spacy.util import filter_spans
    nlp, matcher = _get_spacy()
    doc = nlp(text)
    spans = filter_spans([doc[s:e] for _, s, e in matcher(doc)])
    mentions = []
    for sp in spans:
        key = re.sub(r"\s+", " ", sp.text.lower())
        if key in ALIAS_TO_CITY:
            mentions.append((sp.start_char, sp.end_char, ALIAS_TO_CITY[key]))
    mentions += fuzzy_mentions(text, mentions)
    if len({c for *_, c in mentions}) < 2:                      # cities outside the gazetteer
        gpe = [(e.start_char, e.end_char, e.text.title()) for e in doc.ents if e.label_ == "GPE"]
        mentions += unknown_city_mentions(text, mentions, extra=gpe)
    return _rule_extract(text, sorted(mentions))



__all__ = [name for name in globals() if not name.startswith("__")]
