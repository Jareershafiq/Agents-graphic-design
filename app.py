import io
import os
import random
import textwrap
import zipfile
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import streamlit as st

st.set_page_config(
    page_title="Agent Poster Studio Pro",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- Styling ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0b0e14; color: #f5f6f8; }
.block-container { max-width: 1220px; padding-top: 1.4rem; padding-bottom: 3rem; }
.hero { padding: 30px 30px 28px; border: 1px solid #2a2f3b; border-radius: 24px;
        background: radial-gradient(circle at 85% 10%, #29344b 0, #151b27 34%, #10131b 75%);
        margin-bottom: 22px; }
.eyebrow { color: #d6b66f; font-size: 12px; font-weight: 800; letter-spacing: 2.2px; text-transform: uppercase; }
.hero h1 { font-family: 'Manrope', sans-serif; font-size: clamp(32px, 4.3vw, 52px); line-height: 1.05;
           margin: 12px 0 12px; color: #fff; letter-spacing: -1.5px; }
.hero p { color: #b9c0ce; font-size: 16px; max-width: 680px; margin-bottom: 0; }
.pill { display:inline-block; padding: 7px 11px; border: 1px solid #41495a; border-radius: 999px;
        color: #d9deea; font-size: 12px; margin: 4px 5px 0 0; }
.section-title { font-family: 'Manrope', sans-serif; font-weight: 800; font-size: 22px; margin: 10px 0 5px; }
.subtle { color: #a9b1c0; font-size: 13px; }
div[data-testid="stForm"] { background: #121722; padding: 18px; border: 1px solid #292f3d; border-radius: 18px; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #2a3040 !important; }
.stButton button, .stDownloadButton button, div[data-testid="stFormSubmitButton"] button {
    border-radius: 12px; min-height: 44px; font-weight: 700; border: 1px solid #d6b66f;
}
.stButton button[kind="primary"], div[data-testid="stFormSubmitButton"] button {
    background: #d6b66f; color: #141414; border: none;
}
[data-testid="stMetric"] { background:#121722; border:1px solid #292f3d; padding:15px; border-radius:15px; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ---------- Fonts / drawing helpers ----------
def font_path(bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def get_font(size, bold=False):
    p = font_path(bold)
    try:
        return ImageFont.truetype(p, size) if p else ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()

THEMES = {
    "Midnight Gold": {"bg": (12, 16, 24), "accent": (218, 183, 106), "text": (255,255,255), "muted": (215,219,226)},
    "Modern Blue": {"bg": (12, 30, 52), "accent": (93, 176, 255), "text": (255,255,255), "muted": (220,231,244)},
    "Emerald Luxe": {"bg": (12, 39, 34), "accent": (109, 210, 165), "text": (255,255,255), "muted": (220,239,230)},
    "Minimal Ivory": {"bg": (245, 241, 231), "accent": (143, 104, 55), "text": (29, 31, 35), "muted": (78, 79, 81)},
    "Sunset Copper": {"bg": (43, 22, 24), "accent": (238, 143, 103), "text": (255,255,255), "muted": (239,220,212)},
}
LAYOUTS = ["Signature Split", "Luxury Editorial", "Bold Deal", "Clean Minimal", "Story Spotlight"]

def fit_crop(img, size, focal=(0.5, 0.5)):
    tw, th = size
    img = img.convert("RGB")
    scale = max(tw / img.width, th / img.height)
    nw, nh = int(img.width * scale), int(img.height * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, min(nw - tw, int((nw - tw) * focal[0])))
    top = max(0, min(nh - th, int((nh - th) * focal[1])))
    return img.crop((left, top, left + tw, top + th))

def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0]-1, size[1]-1), radius, fill=255)
    return mask

def draw_text_fit(draw, xy, text, max_width, size, fill, bold=False, min_size=16):
    current = size
    while current > min_size:
        f = get_font(current, bold)
        if draw.textbbox((0,0), text, font=f)[2] <= max_width:
            break
        current -= 2
    draw.text(xy, text, font=get_font(current, bold), fill=fill)
    return current

def wrapped_lines(draw, text, font, max_width):
    words = str(text).split()
    lines, line = [], ""
    for word in words:
        test = word if not line else line + " " + word
        if draw.textbbox((0,0), test, font=font)[2] <= max_width:
            line = test
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines

def add_brand(draw, x, y, width, theme, agent, phone, layout):
    accent, txt, muted = theme["accent"], theme["text"], theme["muted"]
    draw.line((x, y, x+width, y), fill=accent, width=3)
    draw.text((x, y+16), (agent.strip() or "YOUR NAME").upper()[:32], font=get_font(22, True), fill=txt)
    draw.text((x, y+46), (phone.strip() or "CONTACT FOR DETAILS")[:35], font=get_font(17), fill=muted)

def create_poster(photo, data, layout, theme_name, size):
    W, H = size
    t = THEMES[theme_name]
    bg, accent, txt, muted = t["bg"], t["accent"], t["text"], t["muted"]
    img = Image.new("RGB", (W,H), bg)
    draw = ImageDraw.Draw(img)
    margin = int(W * 0.065)
    title = (data["headline"].strip() or "YOUR NEXT PROPERTY").upper()
    community = (data["community"].strip() or "DUBAI, UAE")
    price = (data["price"].strip() or "PRICE ON REQUEST")
    beds = (data["bedrooms"].strip() or "Bedrooms on request")
    kind = data["listing_type"].upper()
    image_height = int(H * (0.55 if layout != "Story Spotlight" else 0.58))
    property_img = fit_crop(photo, (W - 2*margin, image_height))
    # layout-specific top visual and background
    if layout == "Signature Split":
        img.paste(property_img, (margin, margin))
        draw.rounded_rectangle((margin, margin, W-margin, margin+image_height), radius=20, outline=accent, width=max(2, W//500))
        y = margin + image_height + int(H*0.035)
        draw.text((margin, y), kind, font=get_font(max(16,int(W*.022)), True), fill=accent)
        draw_text_fit(draw, (margin, y+int(H*.045)), title, W-2*margin, int(W*.055), txt, True, int(W*.027))
        draw.text((margin, y+int(H*.12)), community, font=get_font(int(W*.027), True), fill=muted)
        draw.text((margin, y+int(H*.17)), price, font=get_font(int(W*.043), True), fill=accent)
        draw.text((margin, y+int(H*.225)), beds, font=get_font(int(W*.026)), fill=txt)
        add_brand(draw, margin, H-int(H*.105), W-2*margin, t, data["agent"], data["phone"], layout)
    elif layout == "Luxury Editorial":
        # dark overlay around image, then editorial typography
        draw.text((margin, int(H*.035)), "EXCLUSIVE PROPERTY", font=get_font(int(W*.023), True), fill=accent)
        img.paste(property_img, (margin, int(H*.085)))
        draw.rounded_rectangle((margin, int(H*.085), W-margin, int(H*.085)+image_height), radius=18, outline=accent, width=2)
        y = int(H*.085)+image_height+int(H*.035)
        draw_text_fit(draw, (margin,y), title, W-2*margin, int(W*.06), txt, True, int(W*.03))
        draw.text((margin,y+int(H*.07)), community, font=get_font(int(W*.027)), fill=muted)
        draw.text((margin,y+int(H*.12)), price, font=get_font(int(W*.045),True), fill=accent)
        draw.text((margin,y+int(H*.175)), f"{beds}  •  {kind}", font=get_font(int(W*.023)), fill=txt)
        add_brand(draw, margin, H-int(H*.105), W-2*margin, t, data["agent"], data["phone"], layout)
    elif layout == "Bold Deal":
        img.paste(property_img, (0,0))
        overlay = Image.new("RGBA", (W,H), (0,0,0,0))
        od = ImageDraw.Draw(overlay)
        od.rectangle((0, int(H*.43), W, H), fill=(7,10,15,235))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((margin, int(H*.04), margin+int(W*.28), int(H*.095)), radius=10, fill=accent)
        draw.text((margin+12,int(H*.052)), kind, font=get_font(int(W*.022),True), fill=bg)
        y=int(H*.49)
        draw_text_fit(draw, (margin,y), title, W-2*margin, int(W*.065), txt, True, int(W*.03))
        draw.text((margin,y+int(H*.08)), community, font=get_font(int(W*.028),True), fill=muted)
        draw.text((margin,y+int(H*.14)), price, font=get_font(int(W*.05),True), fill=accent)
        draw.text((margin,y+int(H*.205)), f"{beds}  •  {data['listing_type']}", font=get_font(int(W*.025)), fill=txt)
        add_brand(draw, margin, H-int(H*.105), W-2*margin, t, data["agent"], data["phone"], layout)
    elif layout == "Clean Minimal":
        # white-ish canvas with photo card and airy information
        img = Image.new("RGB", (W,H), bg)
        draw = ImageDraw.Draw(img)
        draw.text((margin, int(H*.035)), "PROPERTY COLLECTION", font=get_font(int(W*.022),True), fill=accent)
        img.paste(property_img, (margin, int(H*.09)))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((margin,int(H*.09),W-margin,int(H*.09)+image_height), radius=14, outline=accent, width=2)
        y=int(H*.09)+image_height+int(H*.04)
        draw_text_fit(draw,(margin,y),title,W-2*margin,int(W*.055),txt,True,int(W*.028))
        draw.text((margin,y+int(H*.065)),community,font=get_font(int(W*.026)),fill=muted)
        draw.text((margin,y+int(H*.12)),price,font=get_font(int(W*.046),True),fill=accent)
        draw.text((margin,y+int(H*.17)),f"{beds}  |  {kind}",font=get_font(int(W*.023)),fill=muted)
        add_brand(draw,margin,H-int(H*.105),W-2*margin,t,data["agent"],data["phone"],layout)
    else: # Story Spotlight
        img.paste(property_img, (0,0))
        overlay = Image.new("RGBA",(W,H),(0,0,0,0))
        od=ImageDraw.Draw(overlay)
        for yy in range(int(H*.34),H):
            alpha=int(30 + 205*((yy-H*.34)/(H*.66)))
            od.line((0,yy,W,yy),fill=(4,8,14,min(235,alpha)))
        img=Image.alpha_composite(img.convert("RGBA"),overlay).convert("RGB")
        draw=ImageDraw.Draw(img)
        draw.rounded_rectangle((margin,int(H*.04),margin+int(W*.27),int(H*.09)),radius=10,fill=accent)
        draw.text((margin+10,int(H*.052)),kind,font=get_font(int(W*.02),True),fill=bg)
        y=int(H*.60)
        draw_text_fit(draw,(margin,y),title,W-2*margin,int(W*.07),txt,True,int(W*.032))
        draw.text((margin,y+int(H*.09)),community,font=get_font(int(W*.03),True),fill=muted)
        draw.text((margin,y+int(H*.145)),price,font=get_font(int(W*.052),True),fill=accent)
        draw.text((margin,y+int(H*.205)),beds,font=get_font(int(W*.026)),fill=txt)
        add_brand(draw,margin,H-int(H*.105),W-2*margin,t,data["agent"],data["phone"],layout)

    # small corner accent mark
    draw = ImageDraw.Draw(img)
    return img

def image_bytes(img, fmt="PNG"):
    b = io.BytesIO()
    img.save(b, format=fmt, optimize=True)
    return b.getvalue()

def make_caption(d):
    title = d["headline"].strip() or "Your next property in Dubai"
    community = d["community"].strip() or "Dubai"
    price = d["price"].strip() or "Price on request"
    beds = d["bedrooms"].strip() or "Details on request"
    typ = d["listing_type"]
    agent = d["agent"].strip() or "Our team"
    phone = d["phone"].strip()
    return (f"🏙️ {title}\\n\\n📍 Location: {community}\\n💰 Price: {price}\\n🛏️ {beds}\\n🏷️ Type: {typ}\\n\\n"
            f"Interested? Contact {agent}{' at ' + phone if phone else ''} for details or to arrange a viewing.\\n\\n"
            "#DubaiRealEstate #DubaiProperty #DubaiHomes #PropertyForSale #UAERealEstate")

def make_zip(items, caption):
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,"w",zipfile.ZIP_DEFLATED) as z:
        for name, data in items:
            z.writestr(name,data)
        z.writestr("social_caption.txt",caption)
    return mem.getvalue()

# ---------- Header ----------
st.markdown("""
<div class="hero">
  <div class="eyebrow">Built for Dubai real estate agents</div>
  <h1>One property.<br>Multiple premium designs.</h1>
  <p>Create ready-to-post property marketing graphics in minutes. Add your listing details, choose a visual style, preview designs, and download your social media kit.</p>
  <div style="margin-top:17px">
    <span class="pill">1080 × 1350 Instagram Post</span>
    <span class="pill">1080 × 1920 Story / Status</span>
    <span class="pill">No prompt writing</span>
    <span class="pill">Download-ready PNG</span>
  </div>
</div>
""", unsafe_allow_html=True)

c1,c2,c3 = st.columns(3)
with c1: st.metric("Design styles", "5")
with c2: st.metric("Export formats", "2 sizes")
with c3: st.metric("Starter access", "Free demo")

left, right = st.columns([0.92, 1.08], gap="large")
with left:
    st.markdown('<div class="section-title">01 · Your property</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtle">Fill in the details once. They will be used across every design.</div>', unsafe_allow_html=True)
    with st.form("property_form"):
        uploaded = st.file_uploader("Property photo", type=["jpg","jpeg","png","webp"], help="Use a photo you have permission to market.")
        headline = st.text_input("Headline", placeholder="Luxury 4-Bedroom Villa")
        community = st.text_input("Community / location", placeholder="Damac Lagoons, Dubai")
        price = st.text_input("Price (AED)", placeholder="AED 2,750,000")
        a,b = st.columns(2)
        with a:
            bedrooms = st.selectbox("Bedrooms", ["Studio","1 Bedroom","2 Bedrooms","3 Bedrooms","4 Bedrooms","5 Bedrooms","6+ Bedrooms","N/A"])
        with b:
            listing_type = st.selectbox("Listing type", ["For Sale","For Rent","Off-Plan","Ready Property","Distress Deal","Investment Opportunity"])
        agent = st.text_input("Agent / company name", placeholder="Jareer Shafiq")
        phone = st.text_input("Contact number", placeholder="+971 5X XXX XXXX")
        theme_name = st.selectbox("Brand colour theme", list(THEMES.keys()))
        submitted = st.form_submit_button("Apply property details", type="primary", use_container_width=True)

    if submitted:
        st.session_state["poster_data"] = {
            "headline":headline, "community":community, "price":price, "bedrooms":bedrooms,
            "listing_type":listing_type, "agent":agent, "phone":phone, "theme":theme_name
        }
        st.session_state["applied"] = True

    st.markdown('<div class="section-title">02 · Choose your design</div>', unsafe_allow_html=True)
    layout = st.radio("Select a visual style", LAYOUTS, index=0, horizontal=False, label_visibility="collapsed")
    size_choice = st.radio("Output size", ["Instagram Post · 1080 × 1350", "Story / WhatsApp Status · 1080 × 1920"], horizontal=False)
    generate = st.button("✨ Generate my poster kit", type="primary", use_container_width=True)

with right:
    st.markdown('<div class="section-title">Live preview</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtle">Your chosen style is previewed here. Upload a property photo to generate.</div>', unsafe_allow_html=True)
    if uploaded:
        try:
            photo = Image.open(uploaded).convert("RGB")
            st.image(photo, caption="Uploaded property photo", use_container_width=True)
        except Exception:
            photo = None
            st.warning("Could not read that image. Please upload a JPG or PNG.")
    else:
        photo = None
        st.markdown("""
        <div style="height:320px;border:1px dashed #454c5d;border-radius:20px;display:flex;align-items:center;justify-content:center;text-align:center;background:#111722;padding:25px">
          <div><div style="font-size:46px">🏙️</div><div style="font-weight:700;font-size:18px;margin:10px">Your design preview appears here</div><div style="color:#a9b1c0;font-size:13px">Upload a property image and add the listing details to get started.</div></div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#121722;border:1px solid #292f3d;border-radius:16px;padding:16px;margin-top:15px">
      <div style="font-weight:700;margin-bottom:7px">Included in every kit</div>
      <div style="color:#b9c0ce;font-size:14px;line-height:1.8">✓ Property photo and listing details<br>✓ Agent branding and contact details<br>✓ Social media caption and hashtags<br>✓ PNG download in your selected size</div>
    </div>
    """, unsafe_allow_html=True)

if generate:
    data = st.session_state.get("poster_data")
    if not uploaded:
        st.error("Please upload a property photo first.")
    elif not data:
        st.error("First fill in the property details and click “Apply property details”.")
    else:
        try:
            photo = Image.open(uploaded).convert("RGB")
            dimensions = (1080,1350) if size_choice.startswith("Instagram") else (1080,1920)
            with st.spinner("Creating your designs..."):
                posters=[]
                # Generate all five distinct design variants in selected format
                for idx, lay in enumerate(LAYOUTS):
                    poster=create_poster(photo,data,lay,data["theme"],dimensions)
                    posters.append((lay,poster))
                caption=make_caption(data)
            st.session_state["generated_posters"] = [(name,image_bytes(img)) for name,img in posters]
            st.session_state["generated_caption"] = caption
            st.session_state["generated_data"] = data
            st.session_state["generated_size"] = size_choice
            st.success("Your 5-design kit is ready.")
        except Exception as e:
            st.error(f"Could not generate the poster kit. Try another image. Details: {e}")

if "generated_posters" in st.session_state:
    st.markdown("---")
    st.markdown('<div class="section-title">Your poster kit is ready</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtle">Compare all five layouts and download the one you like—or download the complete kit.</div>', unsafe_allow_html=True)
    posters=st.session_state["generated_posters"]
    cols=st.columns(3)
    for i,(name,bdata) in enumerate(posters):
        with cols[i%3]:
            st.markdown(f"**{i+1}. {name}**")
            st.image(bdata, use_container_width=True)
            st.download_button("Download PNG", data=bdata, file_name=f"poster_{i+1}_{name.lower().replace(' ','_')}.png",
                               mime="image/png", key=f"dl_{i}")
    caption=st.session_state.get("generated_caption","")
    st.markdown("### Ready-to-post caption")
    st.text_area("Copy your caption", value=caption, height=190)
    kit=make_zip([(f"poster_{i+1}_{name.lower().replace(' ','_')}.png", bdata) for i,(name,bdata) in enumerate(posters)],caption)
    st.download_button("⬇️ Download complete kit (5 PNGs + caption)", data=kit,
                       file_name="agent_poster_kit.zip", mime="application/zip", type="primary", use_container_width=True)

st.markdown("---")
st.markdown("""
<div style="text-align:center;padding:12px 0 5px">
  <div style="font-weight:800;font-size:19px">Agent Poster Studio Pro</div>
  <div style="color:#a9b1c0;font-size:13px;margin-top:5px">A faster way to create consistent property marketing graphics.</div>
  <div style="color:#7e8797;font-size:11px;margin-top:12px">Demo version · Template-based graphics · Always verify listing details before publishing</div>
</div>
""", unsafe_allow_html=True)
