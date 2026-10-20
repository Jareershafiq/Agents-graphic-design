# Agent Poster Studio Pro

A Streamlit MVP for Dubai real estate agents to generate a five-design property poster kit and ready-to-post caption.

## Features
- Property image upload
- Headline, community, price, bedrooms, listing type, agent name and contact
- Five distinct poster layouts and five colour themes
- Instagram Post (1080×1350) and Story/WhatsApp Status (1080×1920) exports
- Individual PNG downloads and a ZIP containing all five posters plus caption
- No paid AI API required; designs are generated with Pillow templates

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy for free with Streamlit Community Cloud
1. Create a GitHub account and a new public repository.
2. Upload `app.py` and `requirements.txt` to the repository root.
3. Open https://share.streamlit.io/ and sign in with GitHub.
4. Select **Create app**, choose the repository, branch, and `app.py`.
5. Click **Deploy**. Wait for the app to build, then test it on your phone.
6. Keep the GitHub repository public if you are using the free deployment route.

## Important before taking paying customers
This is an MVP/demo. It does not include user accounts, subscription billing, payment verification, customer-specific storage, or a commercial usage limit. Generated files are held in the user's active Streamlit session and may not persist. Do not promise account-based unlimited access or collect sensitive information until those systems are added. Review Streamlit Community Cloud usage/terms and app performance before commercial launch.

## Pricing validation
AED 50/month is a proposed price, not validated. First show the live demo to 5–10 agents and ask whether they would pay for it. This version creates five template-based variants from one uploaded image; it does not use generative AI to invent property imagery.
