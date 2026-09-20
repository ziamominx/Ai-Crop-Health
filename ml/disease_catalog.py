"""Shared ML constants: crop catalogue and disease map (mirrors the Agricure UI)."""

CROPS = ["Tomato", "Wheat", "Cotton", "Rice", "Onion"]

DISEASE_MAP = {
    "Tomato": ["Early Blight", "Late Blight", "Leaf Curl Virus"],
    "Wheat": ["Yellow Rust", "Powdery Mildew"],
    "Cotton": ["Bollworm Damage", "Leaf Curl Virus"],
    "Rice": ["Blast", "Bacterial Leaf Blight"],
    "Onion": ["Purple Blotch"],
}

# Treatment catalogue (label-first, general guidance — no invented doses)
TREATMENT_MAP = {
    "Early Blight": {"category": "Fungicide (protectant)", "timing": "Spray in the early morning or evening, not in direct sun", "phi": "7 days", "note": "Rotate fungicide groups each season to avoid resistance."},
    "Late Blight": {"category": "Fungicide (systemic)", "timing": "Apply before rain if forecast; reapply after heavy rain", "phi": "7–10 days", "note": "Destroy infected debris away from the field — do not compost."},
    "Leaf Curl Virus": {"category": "No direct chemical cure — control the whitefly vector", "timing": "Use yellow sticky traps; treat only the vector as per label", "phi": "As per vector treatment label", "note": "Remove and destroy infected plants to stop virus spread."},
    "Yellow Rust": {"category": "Fungicide (triazole group)", "timing": "Apply at first sign of yellow stripes on leaves", "phi": "21–35 days (cereal-specific)", "note": "Check resistant wheat varieties for your next sowing."},
    "Powdery Mildew": {"category": "Fungicide (sulfur-based or systemic)", "timing": "Apply when white powdery patches first appear", "phi": "As per label", "note": "Improve row spacing to reduce humidity around plants."},
    "Bollworm Damage": {"category": "Insecticide (as per IPM ladder) or Bt-based biopesticide", "timing": "Spray in the evening when pollinators are less active", "phi": "As per label", "note": "Install pheromone traps to monitor moth activity first."},
    "Blast": {"category": "Fungicide (systemic, rice-specific)", "timing": "Apply at boot-leaf stage if disease pressure is high", "phi": "21 days", "note": "Avoid excess nitrogen fertilizer — it increases blast risk."},
    "Bacterial Leaf Blight": {"category": "Copper-based bactericide", "timing": "Apply at first yellowing of leaf margins", "phi": "As per label", "note": "Avoid working in wet fields — this spreads bacteria on tools and hands."},
    "Purple Blotch": {"category": "Fungicide (protectant)", "timing": "Begin spraying at first purple lesions on leaves", "phi": "7–14 days", "note": "Avoid overhead irrigation late in the day."},
}

# Actions per severity (mirrors the farmer result screen)
ACTIONS = {
    "Low": [
        "Monitor the affected plants every 2-3 days",
        "Remove any visibly damaged leaves",
        "Continue normal watering and spacing",
    ],
    "Moderate": [
        "Remove and destroy the worst-affected leaves",
        "Improve airflow between rows",
        "Check neighbouring plants for the same signs",
        "Contact your local Krishi Vigyan Kendra if it spreads",
    ],
    "High": [
        "Isolate and remove severely affected plants immediately",
        "Improve field drainage and sanitation",
        "Request an on-site visit from an agriculture officer",
        "Avoid working in the field while leaves are wet",
    ],
}

GENERIC_SAFETY = [
    "Always read and follow the product label before use",
    "Wear gloves, a mask, and full sleeves while spraying",
    "Do not spray in windy conditions or right before rain",
    "Keep children and animals away from treated fields",
    "Wash hands and equipment thoroughly after use",
]

TRAP_TYPES = ["Pheromone trap", "Yellow sticky trap", "Light trap"]

REFERRAL_REASONS = [
    "Confirm diagnosis in person",
    "Send a sample to the lab",
    "Outbreak risk to neighbouring farms",
    "Unsure how to treat safely",
]
