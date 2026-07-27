import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
import io
import base64
import json
import os
from datetime import datetime

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

# SAFELY IMPORT OPENAI
try:
    from openai import OpenAI
    openai_installed = True
except ImportError:
    openai_installed = False

# --- ORDNER & SPEICHER-SETUP ---
ALBUMS_DIR = "saved_albums"
STYLE_FILE = "style_settings.json"

if not os.path.exists(ALBUMS_DIR):
    try:
        os.makedirs(ALBUMS_DIR, exist_ok=True)
    except Exception:
        pass

# --- HELFER-FUNKTIONEN FÜR SPEICHERUNG ---
def load_style_notes():
    default_notes = "Ich mag übersichtliche Collagen mit einem dünnen weißen Rand zwischen den Bildern. Bevorzugt abwechslungsreiche Layouts (z. B. ein großes Hauptbild links oder oben und kleinere daneben/darunter). Keinen Text auf den Bildern."
    if os.path.exists(STYLE_FILE):
        try:
            with open(STYLE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("notes", default_notes)
        except Exception:
            return default_notes
    return default_notes

def save_style_notes(notes):
    try:
        with open(STYLE_FILE, "w", encoding="utf-8") as f:
            json.dump({"notes": notes}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Fehler beim Speichern der Einstellungen: {e}")

def save_album_to_disk(title, date_str, collage_images):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip() or "Unbenanntes_Album"
    folder_name = f"{timestamp}_{clean_title}"
    album_path = os.path.join(ALBUMS_DIR, folder_name)
    
    try:
        os.makedirs(album_path, exist_ok=True)
        meta = {
            "title": title or "Unbenanntes Album",
            "date": str(date_str),
            "created_at": datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        with open(os.path.join(album_path, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
            
        for idx, img in enumerate(collage_images):
            file_path = os.path.join(album_path, f"collage_{idx+1}.jpg")
            img.save(file_path, format="JPEG", quality=95)
    except Exception as e:
        st.warning(f"Album konnte nicht auf der Festplatte gespeichert werden: {e}")

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

st.divider()

if not openai_installed:
    st.error("⚠️ Das Paket 'openai' ist nicht installiert. Bitte füge 'openai' zu deiner 'requirements.txt' Datei auf GitHub hinzu.")

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
        elif not openai_installed:
            st.error("OpenAI-Bibliothek fehlt. Bitte erneuere die requirements.txt.")
        else:
            api_key = st.secrets.get("OPENAI_API_KEY", None)
            if not api_key:
                st.error("Bitte hinterlege zuerst deinen OPENAI_API_KEY in den Streamlit Secrets.")
            else:
                try:
                    client = OpenAI(api_key=api_key)
                    st.info(f"{len(vacation_files)} Bilder geladen. Erstelle Vorschaubilder...")
                    
                    original_images = [Image.open(f).convert("RGB") for f in vacation_files]
                    base64_thumbnails = [image_to_base64_thumbnail(img) for img in original_images]
                    
                    sample_step = max(1, len(base64_thumbnails) // 30)
                    sampled_indices = list(range(0, len(base64_thumbnails), sample_step))[:30]
                    
                    st.info("GPT-4o mini analysiert Motive & entwirft individuelle Layouts...")
                    
                    prompt_text = f"""
Du bist ein professioneller Foto-Kurator. Analysiere die Urlaubsbilder.
STIL-PRÄFERENZEN DES NUTZERS: "{st.session_state['style_notes']}"

Erstelle einen Plan für exakt {num_collages} Collagen auf einer Fläche [0.0, 0.0, 1.0, 1.0].
Bilde Rechtecke [xmin, ymin, xmax, ymax]. Keine Lücken, keine Überlappungen.

Falls der Nutzer Beispiel-Collagen als Stil-Referenz hochgeladen hat, orientiere dich am Stil und der Anordnung dieser Vorlagen.

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
                    
                    # Falls Stil-Beispielbilder hochgeladen wurden, hängen wir sie als Referenz an
                    if "style_example_b64s" in st.session_state and st.session_state["style_example_b64s"]:
                        messages_content.append({"type": "text", "text": "HIER SIND BEISPIEL-COLLAGEN FÜR DEN GEWÜNSCHTEN STIL:"})
                        for b64_img in st.session_state["style_example_b64s"]:
                            messages_content.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                            })
                        messages_content.append({"type": "text", "text": "HIER SIND DIE NEUEN URLAUBSFOTOS FÜR DIE COLLAGEN:"})

                    for idx in sampled_indices:
                        messages_content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_thumbnails[idx]}"}
                        })
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": messages_content}],
                        max_tokens=1500,
                        response_format={"type": "json_object"}
                    )
                    
                    ki_plan = json.loads(response.choices[0].message.content)
                    st.success("KI-Layouts entworfen! Rendere HD-Collagen...")
                    
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
                            st.download_button(f"💾 Collage {i+1} herunterladen (HD)", data=buf.getvalue(), file_name=f"collage_{i+1}.jpg", mime="image/jpeg", key=f"btn_dl_{i}")
                    
                    if generated_collages:
                        save_album_to_disk(album_title, album_date, generated_collages)
                        st.success("🎉 Album wurde erfolgreich gespeichert!")
                                
                except Exception as e:
                    st.error(f"Fehler bei der Ausführung: {e}")

# TAB 2: GALERIE GESPEICHERTER ALBEN
with tab_gallery:
    st.subheader("📚 Gespeicherte Alben")
    
    if os.path.exists(ALBUMS_DIR):
        album_folders = sorted(os.listdir(ALBUMS_DIR), reverse=True)
        valid_albums = [f for f in album_folders if os.path.isdir(os.path.join(ALBUMS_DIR, f))]
    else:
        valid_albums = []
    
    if not valid_albums:
        st.info("Noch keine Alben gespeichert.")
    else:
        for folder in valid_albums:
            album_path = os.path.join(ALBUMS_DIR, folder)
            meta_file = os.path.join(album_path, "meta.json")
            
            title = folder
            created_at = ""
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta_data = json.load(f)
                        title = meta_data.get("title", title)
                        created_at = meta_data.get("created_at", "")
                except Exception:
                    pass
            
            with st.expander(f"📁 {title} ({created_at})"):
                images_in_album = [f for f in os.listdir(album_path) if f.endswith(".jpg")]
                cols = st.columns(min(3, max(1, len(images_in_album))))
                for idx, img_name in enumerate(sorted(images_in_album)):
                    img_file_path = os.path.join(album_path, img_name)
                    img = Image.open(img_file_path)
                    with cols[idx % len(cols)]:
                        st.image(img, caption=img_name, use_column_width=True)

# TAB 3: STIL EINLERNEN
with tab_style:
    st.subheader("Deinen Stil einlernen")
    st.write("Lade Beispiel-Collagen hoch, die dir besonders gut gefallen, oder beschreibe der KI deinen Wunschstil.")
    
    style_files = st.file_uploader("Beispiel-Collagen als Stilvorlage hochladen", accept_multiple_files=True, type=["jpg", "jpeg", "png"], key="style_upload")
    
    user_notes = st.text_area(
        "Notiz an die KI", 
        value=st.session_state["style_notes"],
        height=140
    )
    
    if st.button("✨ Stil-Profil speichern"):
        st.session_state["style_notes"] = user_notes
        save_style_notes(user_notes)
        
        # Falls Beispiel-Bilder hochgeladen wurden, verkleinern und im Session-State merken
        if style_files:
            b64_list = []
            for f in style_files:
                img = Image.open(f).convert("RGB")
                b64_list.append(image_to_base64_thumbnail(img))
            st.session_state["style_example_b64s"] = b64_list
            st.success(f"Stil-Profil mit {len(style_files)} Beispiel-Bild(ern) gespeichert! Die KI nutzt diese Vorlagen nun als Referenz.")
        else:
            st.session_state["style_example_b64s"] = []
            st.success("Stil-Notiz gespeichert!")
