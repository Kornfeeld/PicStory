import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
import io
import base64
import json
from openai import OpenAI

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="MemoryCollage", page_icon="🖼️", layout="wide")

# --- CUSTOM DESIGN (CSS - Base44 Style) ---
st.markdown("""
    <style>
    .main { background-color: #FAF8F5; }
    h1, h2, h3 { color: #2D2623 !important; font-family: -apple-system, sans-serif; }
    div.stButton > button {
        background-color: #C85A32 !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 0.6rem 1.4rem !important;
        font-weight: 600 !important;
    }
    div.stButton > button:hover { background-color: #B04C27 !important; color: white !important; }
    .stAlert { border-radius: 12px; }
    </style>
""", unsafe_allow_html=True)

# --- HELFER-FUNKTIONEN ---

def image_to_base64_thumbnail(pil_image, max_size=512):
    """Verkleinert ein Bild im Hintergrund für die sparsame KI-Analyse"""
    img_copy = pil_image.copy()
    img_copy.thumbnail((max_size, max_size))
    buffered = io.BytesIO()
    img_copy.save(buffered, format="JPEG", quality=70)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def apply_image_filter(img, filter_type):
    """Wendet fotografische Filter auf das HD-Originalbild an"""
    img = img.copy()
    if filter_type == "bw":
        img = ImageOps.grayscale(img).convert("RGB")
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
    elif filter_type == "vibrant":
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.35)
        enhancer_c = ImageEnhance.Contrast(img)
        img = enhancer_c.enhance(1.1)
    elif filter_type == "bright":
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.15)
    return img

def create_dynamic_collage(image_specs, original_images, canvas_size=2400, margin=20):
    """
    Baut die Collage völlig dynamisch basierend auf den KI-Koordinaten [xmin, ymin, xmax, ymax]
    im Einheitsquadrat (0.0 bis 1.0) zusammen.
    """
    collage = Image.new("RGB", (canvas_size, canvas_size), "white")
    
    for spec in image_specs:
        idx = spec.get("index", 0)
        box = spec.get("box", [0, 0, 1, 1])  # [xmin, ymin, xmax, ymax]
        filt = spec.get("filter", "normal")
        
        if idx >= len(original_images):
            continue
            
        xmin, ymin, xmax, ymax = box
        
        # Umrechnen von Prozent (0.0–1.0) in Pixel-Koordinaten inklusive Abstand/Rand
        px_xmin = int(xmin * canvas_size) + margin
        px_ymin = int(ymin * canvas_size) + margin
        px_xmax = int(xmax * canvas_size) - margin
        px_ymax = int(ymax * canvas_size) - margin
        
        w = px_xmax - px_xmin
        h = px_ymax - px_ymin
        
        # Sicherheitsprüfung für gültige Bildgrößen
        if w <= 20 or h <= 20:
            continue
            
        hd_img = original_images[idx]
        filtered_img = apply_image_filter(hd_img, filt)
        
        # Bild exakt auf die dynamisch berechnete Fläche zuschneiden und platzieren
        cropped = ImageOps.fit(filtered_img, (w, h), Image.Resampling.LANCZOS)
        collage.paste(cropped, (px_xmin, px_ymin))
        
    return collage

# --- APP UI ---
st.markdown("### 🖼️ **MemoryCollage**")
st.caption("Deine Urlaubsbilder, intelligent kuratiert")

st.title("Aus 300 Urlaubsbildern werden wunderschöne Collagen.")
st.write("Lade die Bilder eines Tages hoch. Die KI wählt die schönsten aus, entwirft dynamische Layouts, legt sanfte Filter drüber und baut hochauflösende Collagen.")

st.divider()

# Session State für Stil-Notizen initialisieren
if "style_notes" not in st.session_state:
    st.session_state["style_notes"] = "Ich mag übersichtliche Collagen mit einem dünnen weißen Rand zwischen den Bildern. Bevorzugt abwechslungsreiche Layouts (z. B. ein großes Hauptbild links oder oben und kleinere daneben/darunter). Manche Bilder gerne in Schwarz-Weiß, andere farbenfroh. Keinen Text auf den Bildern."

tab_album, tab_style = st.tabs(["📸 Neues Album erstellen", "✨ Stil einlernen"])

# TAB 1: ALBUM & DYNAMISCHE COLLAGEN
with tab_album:
    st.subheader("1. Album-Details")
    col1, col2 = st.columns(2)
    with col1:
        album_title = st.text_input("Titel des Albums", placeholder="z. B. Strandtag auf Sardinien")
    with col2:
        album_date = st.date_input("Datum")
        
    st.subheader("2. Einstellungen & Upload")
    num_collages = st.slider("Wie viele Collagen sollen erstellt werden?", min_value=1, max_value=10, value=3)
    
    vacation_files = st.file_uploader("Lade hier deine Urlaubsbilder hoch (100–300 Fotos möglich)", accept_multiple_files=True, type=["jpg", "jpeg", "png"])
    
    if st.button("🚀 Album & Collagen erstellen"):
        if not vacation_files:
            st.warning("Bitte lade zuerst deine Urlaubsbilder hoch.")
        else:
            api_key = st.secrets.get("OPENAI_API_KEY", None)
            if not api_key:
                st.error("Bitte hinterlege zuerst deinen OPENAI_API_KEY in den Streamlit Secrets.")
            else:
                client = OpenAI(api_key=api_key)
                st.info(f"{len(vacation_files)} Bilder geladen. Erstelle Vorschaubilder für die KI-Analyse...")
                
                # Bilder laden & verkleinerte Vorschaubilder erzeugen
                original_images = [Image.open(f).convert("RGB") for f in vacation_files]
                base64_thumbnails = [image_to_base64_thumbnail(img) for img in original_images]
                
                # Bis zu 30 Bilder gleichmäßig aus dem Stapel auswählen
                sample_step = max(1, len(base64_thumbnails) // 30)
                sampled_indices = list(range(0, len(base64_thumbnails), sample_step))[:30]
                
                st.info("GPT-4o mini analysiert Motive und entwirft individuelle, dynamische Layouts...")
                
                prompt_text = f"""
Du bist ein professioneller Foto-Kurator und Grafikdesigner. 
Analysiere die bereitgestellten Urlaubsbilder.

STIL-PRÄFERENZEN DES NUTZERS:
"{st.session_state['style_notes']}"

Erstelle einen Plan für exakt {num_collages} Collagen.
Entwirf für JEDE Collage ein dynamisches, maßgeschneidertes Layout auf einer quadratischen Fläche [0.0, 0.0, 1.0, 1.0] (Einheitsquadrat).

REGELN FÜR DAS DYNAMISCHE LAYOUT:
- Bilde Rechtecke mit der Formel [xmin, ymin, xmax, ymax], wobei alle Werte zwischen 0.0 und 1.0 liegen.
- Das Quadrat [0.0, 0.0, 1.0, 1.0] muss vollständig und ohne Lücken von den ausgewählten Bildern abgedeckt werden.
- Die Felder dürfen sich NICHT überlappen.
- Nutze abwechslungsreiche Layouts, z.B.:
  * Hero Left (1 großes Bild links [0.0, 0.0, 0.5, 1.0] + 2-4 kleinere rechts)
  * Hero Top (1 großes Panorama oben [0.0, 0.0, 1.0, 0.5] + 3 kleine unten)
  * 3x2 Raster (6 Bilder)
  * Asymmetrisches 3er- oder 5er-Raster

Antworte AUSSCHLIESSLICH im folgenden JSON-Format:
{{
  "collages": [
    {{
      "selected_images": [
        {{"index": 0, "box": [0.0, 0.0, 0.5, 1.0], "filter": "vibrant"}},
        {{"index": 2, "box": [0.5, 0.0, 1.0, 0.5], "filter": "bw"}},
        {{"index": 5, "box": [0.5, 0.5, 1.0, 1.0], "filter": "normal"}}
      ]
    }}
  ]
}}

Mögliche Filter: "normal", "vibrant", "bw", "bright".
Nutze als 'index' nur Indizes aus dieser Liste: {sampled_indices}
"""
                
                messages_content = [{"type": "text", "text": prompt_text}]
                for idx in sampled_indices:
                    messages_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_thumbnails[idx]}"}
                    })
                
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": messages_content}],
                        max_tokens=1500,
                        response_format={"type": "json_object"}
                    )
                    
                    ki_plan = json.loads(response.choices[0].message.content)
                    st.success("KI-Layouts erfolgreich entworfen! Rendere HD-Collagen...")
                    
                    # Rendern der dynamischen Collagen
                    for i, collage_info in enumerate(ki_plan.get("collages", [])):
                        img_specs = collage_info.get("selected_images", [])
                        
                        if img_specs:
                            final_collage = create_dynamic_collage(img_specs, original_images)
                            
                            st.subheader(f"Collage {i+1}")
                            st.image(final_collage, use_column_width=True)
                            
                            # Download Button
                            buf = io.BytesIO()
                            final_collage.save(buf, format="JPEG", quality=95)
                            st.download_button(f"💾 Collage {i+1} herunterladen (HD)", data=buf.getvalue(), file_name=f"collage_{i+1}.jpg", mime="image/jpeg")
                            
                except Exception as e:
                    st.error(f"Fehler bei der Kommunikation mit OpenAI: {e}")

# TAB 2: STIL EINLERNEN
with tab_style:
    st.subheader("Deinen Stil einlernen")
    st.write("Gib der KI direkte Anweisungen, wie sie deine Collagen arrangieren und bearbeiten soll.")
    
    style_files = st.file_uploader("Beispiel-Collagen hochladen (Optional)", accept_multiple_files=True, type=["jpg", "jpeg", "png"], key="style_upload")
    
    user_notes = st.text_area(
        "Notiz an die KI", 
        value=st.session_state["style_notes"],
        height=140
    )
    
    if st.button("✨ Stil-Profil speichern"):
        st.session_state["style_notes"] = user_notes
        st.success("Dein Stil-Profil wurde gespeichert! Die KI nutzt diese Anweisungen nun dynamisch für jedes neue Album.")
