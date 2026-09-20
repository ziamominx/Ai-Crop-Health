"""Insert static-demo i18n keys into all four language blocks of translations.js.

Idempotent: skips languages that already contain the keys.
Run:  python scripts/add_static_demo_i18n.py
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "frontend", "src", "i18n", "translations.js")

KEYS = {
    "en": {
        "staticDemoTitle": "Static demo:",
        "staticDemoBody": "this published build runs without the backend, on a bundled sample dataset. Every analysis shown was produced by the project's own model during the build. To analyse your own photo, run the project locally.",
        "close": "Close",
        "staticUploadNote": "Uploading a new photo needs the FastAPI backend — this published build is a static demo. Use \"Use a demo photo\" below to see the full agent flow, or run the project locally to analyse your own images.",
    },
    "hi": {
        "staticDemoTitle": "स्टैटिक डेमो:",
        "staticDemoBody": "यह प्रकाशित बिल्ड बैकएंड के बिना, बंडल किए गए नमूना डेटा पर चलता है। यहाँ दिखाया गया हर विश्लेषण बिल्ड के समय परियोजना के अपने मॉडल द्वारा बनाया गया है। अपनी फोटो जाँचने के लिए परियोजना को लोकल में चलाएँ।",
        "close": "बंद करें",
        "staticUploadNote": "नई फोटो अपलोड करने के लिए FastAPI बैकएंड चाहिए — यह प्रकाशित बिल्ड स्टैटिक डेमो है। पूरा एजेंट प्रवाह देखने के लिए नीचे \"डेमो फोटो उपयोग करें\" दबाएँ, या अपनी छवियाँ जाँचने के लिए परियोजना लोकल में चलाएँ।",
    },
    "mr": {
        "staticDemoTitle": "स्टॅटिक डेमो:",
        "staticDemoBody": "हे प्रकाशित बिल्ड बॅकएंडशिवाय, बंडल केलेल्या नमुना डेटावर चालते. येथे दाखवलेले प्रत्येक विश्लेषण बिल्डच्या वेळी प्रकल्पाच्या स्वतःच्या मॉडेलने तयार केले आहे. तुमचा फोटो तपासण्यासाठी प्रकल्प स्थानिक पातळीवर चालवा.",
        "close": "बंद करा",
        "staticUploadNote": "नवीन फोटो अपलोड करण्यासाठी FastAPI बॅकएंड लागतो — हे प्रकाशित बिल्ड स्टॅटिक डेमो आहे. संपूर्ण एजंट प्रवाह पाहण्यासाठी खालील \"डेमो फोटो वापरा\" दाबा, किंवा तुमच्या प्रतिमा तपासण्यासाठी प्रकल्प स्थानिक पातळीवर चालवा.",
    },
    "kn": {
        "staticDemoTitle": "ಸ್ಟಾಟಿಕ್ ಡೆಮೊ:",
        "staticDemoBody": "ಈ ಪ್ರಕಟಿತ ಬಿಲ್ಡ್ ಬ್ಯಾಕೆಂಡ್ ಇಲ್ಲದೆ, ಬಂಡಲ್ ಮಾಡಿದ ಮಾದರಿ ಡೇಟಾದಲ್ಲಿ ಚಲಿಸುತ್ತದೆ. ಇಲ್ಲಿ ತೋರಿಸಿರುವ ಪ್ರತಿಯೊಂದು ವಿಶ್ಲೇಷಣೆಯನ್ನು ಬಿಲ್ಡ್ ಸಮಯದಲ್ಲಿ ಯೋಜನೆಯ ಸ್ವಂತ ಮಾದರಿಯೇ ಮಾಡಿದೆ. ನಿಮ್ಮ ಫೋಟೋ ಪರಿಶೀಲಿಸಲು ಯೋಜನೆಯನ್ನು ಸ್ಥಳೀಯವಾಗಿ ಚಲಾಯಿಸಿ.",
        "close": "ಮುಚ್ಚಿ",
        "staticUploadNote": "ಹೊಸ ಫೋಟೋ ಅಪ್‌ಲೋಡ್ ಮಾಡಲು FastAPI ಬ್ಯಾಕೆಂಡ್ ಬೇಕು — ಈ ಪ್ರಕಟಿತ ಬಿಲ್ಡ್ ಸ್ಟಾಟಿಕ್ ಡೆಮೊ. ಪೂರ್ಣ ಏಜೆಂಟ್ ಹರಿವನ್ನು ನೋಡಲು ಕೆಳಗಿನ \"ಡೆಮೊ ಫೋಟೋ ಬಳಸಿ\" ಒತ್ತಿರಿ, ಅಥವಾ ನಿಮ್ಮ ಚಿತ್ರಗಳನ್ನು ಪರಿಶೀಲಿಸಲು ಯೋಜನೆಯನ್ನು ಸ್ಥಳೀಯವಾಗಿ ಚಲಾಯಿಸಿ.",
    },
}

with io.open(PATH, encoding="utf-8") as fh:
    src = fh.read()

MANAGED = set(KEYS["en"])

# Drop any previously inserted lines for these keys so the script is re-runnable
src = "\n".join(
    line for line in src.split("\n")
    if not any(line.strip().startswith(f"{k}:") for k in MANAGED)
)

for lang, keys in KEYS.items():
    start = src.index(f"\n  {lang}: {{")          # block marker
    end = src.index("\n  },", start)             # block close
    # json.dumps gives us correct escaping for quotes/newlines
    addition = "".join(f"    {k}: {json.dumps(v, ensure_ascii=False)},\n" for k, v in keys.items())
    src = src[:end] + "\n" + addition.rstrip("\n") + src[end:]
    print(f"  {lang}: added {len(keys)} keys")

with io.open(PATH, "w", encoding="utf-8") as fh:
    fh.write(src)
print(f"Updated {PATH}")
