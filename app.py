import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
import io
import base64
import json
import os
from datetime import datetime
from openai import OpenAI

# --- ORDNER & SPEICHER-SETUP ---
ALBUMS_DIR = "saved_albums"
STYLE_FILE = "style_settings.json"

if not os.path.exists(ALBUMS_DIR):
    os.makedirs(ALBUMS_DIR)

# --- HELFER-FUNKTIONEN FÜR SPEICHERUNG ---
def load_style_notes():
    """Lädt gespeicherte Stil-Notizen aus der JSON-Datei"""
    default_notes = "Ich mag übersichtliche Collagen mit einem dünnen weißen Rand zwischen den Bildern. Bevorzugt abwechslungsreiche Layouts (z. B. ein großes Hauptbild links oder oben und kleinere daneben/darunter). Manche Bilder gerne in Schwarz-Weiß, andere farbenfroh. Keinen Text auf den Bildern."
    if os.path.exists(STYLE_FILE):
        try:
            with open(STYLE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("notes", default_notes)
        except Exception:
            return default_notes
    return default_notes

def save_style_notes(notes):
    """Speichert die Stil-Notizen dauerhaft auf dem Server"""
    with open(STYLE_FILE, "w", encoding="utf-8") as f:
        json.dump({"notes": notes}, f, ensure_ascii=False, indent=2)

def save_album_to_disk(title, date_str, collage_images):
    """Speichert ein neues Album mit allen Collagen auf der Festplatte"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip() or "Unbenanntes_Album"
    folder_name = f"{timestamp}_{clean_title}"
    album_path = os.path.join(ALBUMS_DIR, folder_name)
    
    os.makedirs(album_path, exist_ok=True)
    
    # Meta-Infos speichern
    meta = {
        "title": title or "Unbenanntes Album",
        "date": str(date_str),
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    with open(os.path.join(album_path, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        
    # Collagen als JPG speichern
    for idx, img in enumerate(collage_images):
        file_path = os.path.join(album_path, f"collage_{idx+1}.jpg")
        img.save(file_path, format="JPEG", quality=95)

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="MemoryCollage", page_icon="🖼️", layout="wide")

# Custom CSS
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

# --- BILD-VERARBEITUNG ---
def image_to_base64_thumbnail(pil_image, max_size=512):
    img_copy = pil_image.copy()
    img_copy.thumbnail((max_size, max_size))
    buffered = io.BytesIO()
    img_copy.save(buffered, format="JPEG", quality=70)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def apply_image_filter(img, filter_type):
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
    collage = Image.new("RGB", (canvas_size, canvas_size), "white")
    for spec in image_specs:
        idx = spec.get("index", 0)
        box = spec.get("box", [0, 0, 1, 1])
        filt = spec.get("filter", "normal")
        
        if idx >= len(original_images):
            continue
            
        xmin, ymin, xmax, ymax = box
        px_xmin = int(xmin * canvas_size) + margin
        px_ymin = int(ymin * canvas_size) + margin
        px_xmax = int(xmax * canvas_size) - margin
        px_ymax = int(ymax * canvas_size) - margin
        
        w = px_xmax - px_xmin
        h = px_ymax - px_ymin
        
        if w <= 20 or h <= 20:
            continue
            
        hd_img = original_images[idx]
        filtered_img = apply_image_filter(hd_img, filt)
        cropped = ImageOps.fit(filtered_img, (w, h), Image.Resampling.LANCZOS)
        collage.paste(cropped, (px_xmin, px_ymin))
        
    return collage

# --- HEADER ---
st.markdown("### 🖼️ **MemoryCollage**")
st.caption("Deine Urlaubsbilder, intelligent kuratiert")

st.title("Aus 300 Urlaubsbildern werden wunderschöne Collagen.")
st.write("Lade die Bilder eines Tages hoch. Die KI wählt die schönsten aus, entwirft dynamische Layouts und baut hochauflösende Collagen.")

st.divider()

# Session State & Stil laden
if "style_notes" not in st.session_state:
    st.session_state["style_notes"] = load_style_notes()

tab_album, tab_gallery, tab_style = st.tabs(["📸 Neues Album erstellen", "📚 Meine Alben", "✨ Stil einlernen"])

# TAB 1: ALBUM ERSTELLEN
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
                st.info(f"{len(vacation_files)} Bilder geladen. Erstelle Vorschaubilder...")
                
                original_images = [Image.open(f).convert("RGB") for f in vacation_files]
                base64_thumbnails = [image_to_base64_thumbnail(img) for img in original_images]
                
                sample_step = max(1, len(base64_thumbnails) // 30)
                sampled_indices = list(range(0, len(base64_thumbnails), sample_step))[:30]
                
                st.info("GPT-4o mini entwirft individuelle Layouts...")
                
                prompt_text = f"""
Du bist ein professioneller Foto-Kurator. Analysiere die Urlaubsbilder.
STIL-PRÄFERENZEN: "{st.session_state['style_notes']}"

Erstelle einen Plan für exakt {num_collages} Collagen auf einer Fläche [0.0, 0.0, 1.0, 1.0].
Bilde Rechtecke [xmin, ymin, xmax, ymax]. Keine Lücken, keine Überlappungen.
Layouts abwechslungsreich gestalten (Hero Left, Hero Top, 3x2, etc.).

Antworte NUR in JSON:
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
Filter-Optionen: "normal", "vibrant", "bw", "bright".
Indizes: {sampled_indices}
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
                    st.success("KI-Layouts entworfen! Rendere und speichere HD-Collagen...")
                    
                    generated_collages = []
                    for i, collage_info in enumerate(ki_plan.get("collages", [])):
                        img_specs = collage_info.get("selected_images", [])
                        if img_specs:
                            final_collage = create_dynamic_collage(img_specs, original_images)
                            generated_collages.append(final_collage)
                            
                            st.subheader(f"Collage {i+1}")
                            st.image(final_collage, use_column_width=True)
                            
                            buf = io.BytesIO()
                            final_collage.save(buf, format="JPEG", quality=95)
                            st.download_button(f"💾 Collage {i+1} herunterladen (HD)", data=buf.getvalue(), file_name=f"collage_{i+1}.jpg", mime="image/jpeg")
                    
                    # ALBUM AUF FESTPLATTE SPEICHERN
                    if generated_collages:
                        save_album_to_disk(album_title, album_date, generated_collages)
                        st.success("🎉 Album wurde erfolgreich in deinen gespeicherten Alben archiviert!")
                            
                except Exception as e:
                    st.error(f"Fehler bei der Kommunikation mit OpenAI: {e}")

# TAB 2: GALERIE GESPEICHERTER ALBEN
with tab_gallery:
    st.subheader("📚 Gespeicherte Alben")
    
    album_folders = sorted(os.listdir(ALBUMS_DIR), reverse=True) if os.path.exists(ALBUMS_DIR) else []
    valid_albums = [f for f in album_folders if os.path.isdir(os.path.join(ALBUMS_DIR, f))]
    
    if not valid_albums:
        st.info("Noch keine Alben gespeichert. Erstelle dein erstes Album im Reiter 'Neues Album erstellen'!")
    else:
        for folder in valid_albums:
            album_path = os.path.join(ALBUMS_DIR, folder)
            meta_file = os.path.join(album_path, "meta.json")
            
            title = folder
            created_at = ""
            if os.path.exists(meta_file):
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                    title = meta_data.get("title", title)
                    created_at = meta_data.get("created_at", "")
            
            with st.expander(f"📁 {title} ({created_at})"):
                images_in_album = [f for f in os.listdir(album_path) if f.endswith(".jpg")]
                cols = st.columns(min(3, max(1, len(images_in_album))))
                for idx, img_name in enumerate(sorted(images_in_album)):
                    img_file_path = os.path.join(album_path, img_name)
                    img = Image.open(img_file_path)
                    with cols[idx % len(cols)]:
                        st.image(img, caption=img_name, use_column_width=True)
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=95)
                        st.download_button(f"💾 {img_name}", data=buf.getvalue(), file_name=img_name, key=f"{folder}_{img_name}")

# TAB 3: STIL EINLERNEN
with tab_style:
    st.subheader("Deinen Stil einlernen")
    st.write("Ändere deine Anweisungen an die KI. Deine Notiz wird automatisch gespeichert.")
    
    user_notes = st.text_area(
        "Notiz an die KI", 
        value=st.session_state["style_notes"],
        height=140
    )
    
    if st.button("✨ Stil-Profil speichern"):
        st.session_state["style_notes"] = user_notes
        save_style_notes(user_notes)
        st.success("Dein Stil-Profil wurde dauerhaft gespeichert! Die KI nutzt diese Anweisungen nun für jedes neue Album.")
