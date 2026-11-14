from ._shared import *
from .requirements import _tag
from .cities import normalize_city
from .bus import normalize_bus_pref, normalize_city, normalize_ac, normalize_seat_type
from .pipeline import empty_result

# ----------------------------------------------------------------------------
def _canon_time(v):
    s = re.sub(r"\s+", " ", str(v).strip().lower())
    return re.sub(r"\b(\d):(\d{2})\b", r"0\1:\2", s)


_STATUS_SYN = {"provided": "filled", "present": "filled", "given": "filled", "captured": "filled",
               "not_provided": "missing", "unfilled": "missing", "empty": "missing", "absent": "missing",
               "unclear": "ambiguous", "needs_clarification": "ambiguous", "uncertain": "ambiguous",
               "updated": "corrected", "revised": "corrected", "changed": "corrected"}


def canon(field, v):
    if isinstance(v, float) and v != v:                 # pandas turns None into NaN
        v = None
    if field in LIST_FIELDS:
        if v is None or v == "" or v == []:
            return None
        if isinstance(v, str):
            v = [x for x in re.split(r"[,;|]", v) if x.strip()]
        return tuple(sorted({_tag(x) for x in v})) or None
    if field in DICT_FIELDS:
        if not isinstance(v, dict) or not v:
            return None
        norm = {_tag(k): _tag(x) for k, x in v.items()}
        return {k: _STATUS_SYN.get(x, x) for k, x in norm.items()} if field == "field_status" else norm
    if field in BOOL_FIELDS:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return v.strip().lower() in ("true", "yes", "y", "1")
        return bool(v)
    if v is None or v == "":
        return None
    if field in ("origin", "destination"):
        return normalize_city(v)
    if field in ("budget", "passengers"):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None
    if field == "bus_preference":
        return normalize_bus_pref(v)
    if field == "seat_type":
        return normalize_seat_type(v)
    if field == "ac_preference":
        return normalize_ac(v)
    if field == "budget_scope":
        return str(v).strip().lower().replace("-", "_").replace(" ", "_")
    if field in ("arrival_deadline", "departure_preference"):
        return _canon_time(v)
    return str(v).strip().lower()


def _match(field, g, p):
    cg, cp = canon(field, g), canon(field, p)
    if field in DICT_FIELDS and isinstance(cg, dict) and isinstance(cp, dict):
        return all(cp.get(k) == x for k, x in cg.items())      # GT may label only some fields
    return cg == cp


def _gt(item):
    gt = dict(item["ground_truth"])
    for key in NESTED_GT_KEYS:                          # {"travel_requirements": {...}} -> flat slots
        if isinstance(gt.get(key), dict):
            gt.update(gt.pop(key))
    for old, new in GT_ALIASES.items():
        if old in gt and new not in gt:
            gt[new] = gt.pop(old)
    return gt


def detect_fields(dataset):
    """Score only the slots the dataset actually labels (old 7-slot or refined schema)."""
    present = set()
    for item in dataset:
        present |= set(_gt(item))
    return [f for f in ALL_FIELDS if f in present]


def evaluate(extractor, dataset, fields=None):
    fields = fields or detect_fields(dataset)
    rows = []
    for item in dataset:
        err = None
        try:
            pred = extractor(item["utterance"])
        except Exception as e:                           # keep going; record the failure
            pred, err = empty_result(), repr(e)
        gt = _gt(item)
        row = {"id": item["id"], "utterance": item["utterance"], "error": err}
        for f in fields:
            row[f"gt_{f}"], row[f"pred_{f}"] = gt.get(f), pred.get(f)
            row[f"ok_{f}"] = _match(f, gt.get(f), pred.get(f))
        row["exact_match"] = all(row[f"ok_{f}"] for f in fields)
        rows.append(row)
    return pd.DataFrame(rows)


def summarize(df, name, fields):
    out = []
    for f in fields:
        gt_has = df[f"gt_{f}"].map(lambda x: canon(f, x) is not None)
        pr_has = df[f"pred_{f}"].map(lambda x: canon(f, x) is not None)
        out.append({
            "extractor": name, "category": FIELD_CATEGORY.get(f, "other"), "field": f,
            "accuracy": round(df[f"ok_{f}"].mean(), 3),
            "miss_rate": round((gt_has & ~pr_has).sum() / max(gt_has.sum(), 1), 3),            # gt present, pred null
            "hallucination_rate": round((~gt_has & pr_has).sum() / max((~gt_has).sum(), 1), 3),  # gt null, pred present
        })
    out.append({"extractor": name, "category": "ALL", "field": f"EXACT_MATCH (all {len(fields)} slots)",
                "accuracy": round(df["exact_match"].mean(), 3), "miss_rate": None, "hallucination_rate": None})
    return pd.DataFrame(out)


# Two ground-truth labels in the generated dataset look inconsistent; set True to patch them in memory.
APPLY_DATASET_FIXES = False


def apply_dataset_fixes(ds):
    for item in ds:
        if item["id"] == "utt_025":      # "in the morning" gives no actual date
            item["ground_truth"]["travel_date"] = None
        if item["id"] == "utt_067":      # "Non AC seater": seat type wins, like the "AC sleeper" rows
            item["ground_truth"]["bus_preference"] = "seater"
    return ds


__all__ = [name for name in globals() if not name.startswith("__")]
