"""Expose the shared catalogue to the frontend (single source of truth = ml/disease_catalog)."""
from ml.disease_catalog import (ACTIONS, CROPS, DISEASE_MAP, GENERIC_SAFETY,
                                REFERRAL_REASONS, TREATMENT_MAP, TRAP_TYPES)


def full_catalog() -> dict:
    return {
        "crops": CROPS,
        "disease_map": DISEASE_MAP,
        "treatment_map": TREATMENT_MAP,
        "actions": ACTIONS,
        "safety": GENERIC_SAFETY,
        "trap_types": TRAP_TYPES,
        "referral_reasons": REFERRAL_REASONS,
    }
