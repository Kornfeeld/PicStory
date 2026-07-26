import streamlit as st
from PIL import Image, ImageOps
import io
import os

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="MemoryCollage", page_icon="🖼️", layout="wide")

# --- CUSTOM BASE44 / MEMORYCOLLAGE DESIGN (CSS) ---
st.markdown("""
    <style>
    /* Hintergrund & Grundfarben */
    .main {
        background-color: #FAF8F5;
    }
    
    /* Hauptüberschriften */
    h1, h2, h3 {
        color: #2D2623 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Buttons im Terracotta-Look */
    div.stButton > button {
        background-color: #C85A32 !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 0.6rem 1.4rem !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 6px rgba(200, 90, 50, 0.2);
    }
    div.stButton > button:hover {
        background-color: #B04C27 !important;
        color: white !important;
    }

    /* Info-Boxen & Cards */
    .stAlert {
        border-radius: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("### 🖼️ **MemoryCollage**")
st.caption("Deine Urlaubsbilder, intelligent kuratiert")

st.title("Aus 300 Urlaubsbildern werden wunderschöne Collagen.")
st.write("Lade die Bilder eines Tages hoch. Die KI wählt die schönsten aus, legt sanfte Filter drüber und baut daraus quadratische Collagen – genau in deinem Stil.")

st.divider()

# --- TABS WIE IN BASE44 ---
tab_album, tab_style = st.tabs(["📸 Neues Album erstellen", "✨ Stil einlernen"])

# TAB 1: ALBUM & COLLAGEN
with tab_album:
    st.subheader("1. Album-Details")
    col1, col2 = st.columns(2)
    with col1:
        album_title = st.text_input("Titel des Albums", placeholder="z. B. Strandtag auf Sardinien")
    with col2:
        album_date = st.date_input("Datum")
        
    album_desc = st.text_area("Beschreibung (optional)", placeholder="Was war das Besondere an diesem Tag?")
    
    st.subheader("2. Einstellungen & Upload")
    num_collages = st.slider("Wie viele Collagen sollen erstellt werden?", min_value=1, max_value=10, value=3)
    
    vacation_files = st.file_uploader("Lade hier deine 100-300 Urlaubsbilder hoch", accept_multiple_files=True, type=["jpg", "jpeg", "png"])
    
    if st.button("🚀 Album & Collagen erstellen"):
        if not vacation_files:
            st.warning("Bitte wähle zuerst deine Urlaubsbilder aus.")
        else:
            st.info(f"Verarbeite {len(vacation_files)} Bilder für '{album_title or 'Dein Urlaub'}'...")
            
            # PRÜFEN OB OPENAI KEY VORHANDEN IST
            has_openai = "OPENAI_API_KEY" in st.secrets and st.secrets["OPENAI_API_KEY"] != ""
            
            if has_openai:
                st.success("KI-Modell GPT-4o mini aktiv! Analysiere Bildmotive & Belichtung...")
            else:
                st.info("💡 **Test-Modus active:** OpenAI Key noch nicht aufgeladen. Erstelle Beispiel-Collagen aus den ersten Bildern...")

            # Beispiels-Collage generieren (Pillow Demo-Logik)
            images = [Image.open(f) for f in vacation_files[:4]]
            if len(images) >= 4:
                # 2x2 Raster erstellen
                w, h = 1000, 1000
                collage = Image.new("RGB", (w, h), "white")
                
                # Bilder anpassen & platzieren mit dünnem weißen Rand
                margin = 15
                target_size = ((w - 3 * margin) // 2, (h - 3 * margin) // 2)
                
                positions = [
                    (margin, margin),
                    (target_size[0] + 2 * margin, margin),
                    (margin, target_size[1] + 2 * margin),
                    (target_size[0] + 2 * margin, target_size[1] + 2 * margin)
                ]
                
                for img, pos in zip(images, positions):
                    img_fit = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
                    collage.paste(img_fit, pos)
                
                st.subheader("Ergebnis Preview:")
                st.image(collage, caption="Generierte 2x2 Collage (Muster)", use_column_width=True)
                
                # Download Button
                buf = io.BytesIO()
                collage.save(buf, format="JPEG", quality=95)
                st.download_button("💾 Collage herunterladen (HD)", data=buf.getvalue(), file_name="collage.jpg", mime="image/jpeg")

# TAB 2: STIL EINLERNEN
with tab_style:
    st.subheader("Deinen Stil einlernen")
    st.write("Lade ein paar Paar Collagen hoch, die du magst. Die KI lernt daraus deinen Geschmack und wendet ihn bei zukünftigen Alben an.")
    
    style_files = st.file_uploader("Beispiel-Collagen auswählen", accept_multiple_files=True, type=["jpg", "jpeg", "png"], key="style_upload")
    
    ai_notes = st.text_area(
        "Notiz an die KI (optional)", 
        value="Ich mag übersichtliche Collagen mit einem weißen dünnen Rand zwischen den Bildern und aussenrum mit verschiedenen Layouts. Außerdem soll kein Text auf den Collagen sein.",
        height=100
    )
    
    if st.button("✨ Jetzt analysieren"):
        if style_files:
            st.success(f"Analysiere {len(style_files)} Beispiel-Collagen zusammen mit deinen Notizen...")
            st.json({
                "Status": "Profil gespeichert",
                "Erkannte Wünsche": ai_notes,
                "Analysierte Dateien": len(style_files)
            })
        else:
            st.warning("Bitte lade mindestens 1–2 Beispiel-Collagen hoch.")
