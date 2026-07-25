import streamlit as st

st.set_page_config(page_title="Meine Foto-Collagen KI", layout="wide")

st.title("📸 KI Foto-Selektor & Collagen-Generator")
st.write("Willkommen! Hier kannst du deine Urlaubsbilder intelligent filtern und zu Collagen zusammenbauen lassen.")

# Zwei Reiter für die App
tab1, tab2 = st.tabs(["1. KI-Geschmack trainieren", "2. Urlaubsbilder & Collagen"])

with tab1:
    st.header("🧠 Zeig der KI, was dir gefällt (Einmalig)")
    st.write("Lade hier deine Beispiel-Collagen hoch (z.B. deine 70 Stück). Die KI analysiert deinen Stil und merkt sich diesen.")
    
    reference_images = st.file_uploader("Beispiel-Collagen hochladen", accept_multiple_files=True, type=["jpg", "png", "jpeg"], key="ref_upload")
    
    if st.button("Mein Profil analysieren"):
        if reference_images:
            st.success("Profil-Erstellung simuliert! (Die OpenAI-Anbindung bauen wir im nächsten Schritt ein).")
        else:
            st.error("Bitte lade zuerst Bilder hoch.")

with tab2:
    st.header("🖼️ Neue Collagen erstellen")
    
    # Hier ist deine gewünschte Auswahlfunktion!
    num_collages = st.slider("Wie viele Collagen sollen erstellt werden?", min_value=1, max_value=20, value=3)
    
    vacation_images = st.file_uploader("Lade 100-300 Urlaubsbilder hoch", accept_multiple_files=True, type=["jpg", "png", "jpeg"], key="vacation_upload")
    
    if st.button("Bilder auswählen & Collagen erstellen"):
        if vacation_images:
            st.info(f"Bereite die Erstellung von {num_collages} Collagen aus {len(vacation_images)} Bildern vor...")
            st.write("Schritt 1: Bilder verkleinern (läuft später lokal, spart Kosten)")
            st.write("Schritt 2: GPT-4o mini wählt die besten Bilder nach deinem Geschmack aus")
            st.write("Schritt 3: Bilder werden verschönert und Collagen generiert")
            st.success("Fertig! (Das 'Gehirn' dafür fügen wir im nächsten Schritt hinzu).")
        else:
            st.error("Bitte lade deine Urlaubsbilder hoch.")
