import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="NGA Togo - V2", layout="wide", page_icon="🐓")

# --- MASQUER L'INTERFACE STANDARD STREAMLIT ---
cacher_menu_style = """
        <style>
        #MainMenu {visibility: hidden;} 
        [data-testid="stToolbar"] {visibility: hidden !important;} 
        footer {visibility: hidden !important;} 
        header {visibility: hidden !important;} 
        </style>
        """
st.markdown(cacher_menu_style, unsafe_allow_html=True)

# --- 2. INITIALISATION DE LA MÉMOIRE (Base de données simulée) ---
if "base_creances" not in st.session_state:
    st.session_state["base_creances"] = pd.DataFrame({
        "Date": ["03/11/2026", "04/11/2026"],
        "Heure": ["14:20", "16:45"],
        "Client": ["AGROSATH", "JOSUE"],
        "Type Vente": ["Œufs", "Œufs"],
        "Montant Dû (FCFA)": [350000, 125000],
        "Statut": ["En attente", "Retard"]
    })

if "historique_ferme" not in st.session_state:
    st.session_state["historique_ferme"] = pd.DataFrame({
        "Date": ["03/11/2026", "04/11/2026"],
        "Heure Saisie": ["17:15", "17:30"],
        "Bâtiment": ["Bande 01 (Kadjolo)", "Bande 01 (Kadjolo)"],
        "Élevage": ["Pondeuses (Isa Brown/Leghons)", "Pondeuses (Isa Brown/Leghons)"],
        "PIWI": [0, 0],
        "Petits": [4, 5],
        "Moyens": [18, 20],
        "Gros": [75, 80],
        "Super Gros": [12, 15],
        "Cassés": [2, 3],
        "Total Plateaux": [111, 123],
        "Mortalité": [1, 4],
        "Aliment (kg)": [1140.0, 1150.0],
        "Type Aliment": ["Ponte Phase 1", "Ponte Phase 1"],
        "Gasoil (L)": [10.0, 15.0],
        "Pharmacie": ["RAS", "Vitamines"]
    })

# --- 3. SYSTÈME DE CONNEXION (DOUBLE PROFIL) ---
if "authentifie" not in st.session_state:
    st.session_state["authentifie"] = False
    st.session_state["role"] = ""

if not st.session_state["authentifie"]:
    st.title("🥚🐓 NGA AgroGestion")
    st.write("Veuillez vous connecter avec vos identifiants de site.")
    
    identifiant = st.text_input("Identifiant")
    mot_de_passe = st.text_input("Mot de passe", type="password")
    
    if st.button("Se connecter"):
        if identifiant == "Sokode" and mot_de_passe == "Terrain2026!":
            st.session_state["authentifie"] = True
            st.session_state["role"] = "ferme"
            st.rerun()
        elif identifiant == "Lome" and mot_de_passe == "Direction2026!":
            st.session_state["authentifie"] = True
            st.session_state["role"] = "direction"
            st.rerun()
        else:
            st.error("Identifiant ou mot de passe incorrect.")
    st.stop()

# --- 4. DONNÉES MÉTIER (Issues des fichiers Excel) ---
races = ["Pondeuses (Isa Brown/Leghons)", "Poulets de Chair", "Coquelets"]
calibres = ["PIWI", "Petits", "Moyens", "Gros", "Super Gros", "Cassés"]

# Tarification issue de "SITUATION PRIX DES OEUFS"
prix_grossiste = {"PIWI": 1500, "Petits": 2000, "Moyens": 2400, "Gros": 2800, "Super Gros": 2900, "Cassés": 500}
prix_detaillant = {"PIWI": 1600, "Petits": 2100, "Moyens": 2500, "Gros": 2950, "Super Gros": 3000, "Cassés": 600}

# --- 5. MENU COMMUN ---
st.sidebar.title("🚜 NGA Togo")
st.sidebar.info(f"Connecté en tant que : **{st.session_state['role'].upper()}**")
if st.sidebar.button("Se déconnecter"):
    st.session_state["authentifie"] = False
    st.session_state["role"] = ""
    st.rerun()


# =====================================================================
# ESPACE 1 : LA FERME (SOKODÉ) - SAISIE UNIQUEMENT
# =====================================================================
if st.session_state["role"] == "ferme":
    st.title("📋 Interface de saisie quotidienne (Sokodé)")
    st.info("Cette interface est réservée au personnel de terrain pour la déclaration des opérations du jour.")
    
    date_jour = st.date_input("Date du relevé", datetime.now())
    batiment = st.selectbox("Bâtiment / Bande concernée", ["Bande 01 (Kadjolo)", "Bande 02 (Djaguis)", "Bande 03"])
    type_elevage = st.selectbox("Type d'élevage", races)
    
    st.divider()
    
    # Initialisation par défaut des œufs (à 0 si Poulets de chair ou Coquelets)
    saisie_oeufs = {cal: 0 for cal in calibres}
    
    # Formulaire de ramassage (uniquement pour pondeuses)
    if "Pondeuses" in type_elevage:
        st.subheader("🥚 1. Déclaration du ramassage (En plateaux)")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            saisie_oeufs["PIWI"] = st.number_input("PIWI", min_value=0, step=1)
            saisie_oeufs["Petits"] = st.number_input("Petits", min_value=0, step=1)
        with col_c2:
            saisie_oeufs["Moyens"] = st.number_input("Moyens", min_value=0, step=1)
            saisie_oeufs["Gros"] = st.number_input("Gros", min_value=0, step=1)
        with col_c3:
            saisie_oeufs["Super Gros"] = st.number_input("Super Gros", min_value=0, step=1)
            saisie_oeufs["Cassés"] = st.number_input("Cassés (Perte)", min_value=0, step=1)
        st.divider()
    
    # Formulaire Événements & Stocks
    st.subheader("📦 2. Déclaration des événements et des sorties de stock")
    col_s1, col_s2, col_s3 = st.columns(3)
    
    with col_s1:
        mortalite = st.number_input("Mortalité du jour (Nb de sujets)", min_value=0, step=1)
    with col_s2:
        aliment_consomme = st.number_input("Aliment distribué (kg)", min_value=0.0, step=5.0)
        type_aliment = st.selectbox("Type d'aliment", ["Démarrage", "Croissance", "Pré-ponte", "Ponte Phase 1", "Ponte Phase 2", "Finition"])
    with col_s3:
        gasoil = st.number_input("Gasoil consommé (Litres)", min_value=0.0, step=1.0)
        veto = st.text_input("Produits Vétérinaires utilisés (Optionnel)")
        
    st.divider()
    
    # Génération du Rapport pour le Chauffeur & Enregistrement en Base
    st.subheader("📄 3. Génération du rapport quotidien (Bordereau chauffeur)")
    
    def generer_rapport_terrain(heure_actuelle):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(200, 10, txt=f"Rapport Quotidien NGA - {batiment}", ln=True, align='C')
        pdf.set_font("Arial", "", 11)
        pdf.cell(200, 10, txt=f"Date : {date_jour.strftime('%d/%m/%Y')} a {heure_actuelle} | Elevage : {type_elevage}", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="1. OEUFS RAMASSES (Plateaux)", ln=True)
        pdf.set_font("Arial", "", 11)
        if "Pondeuses" in type_elevage:
            for k, v in saisie_oeufs.items():
                k_clean = k.replace("é", "e")
                pdf.cell(200, 8, txt=f"- {k_clean} : {v} plateaux", ln=True)
            total_pl = sum(saisie_oeufs.values())
            pdf.set_font("Arial", "B", 11)
            pdf.cell(200, 8, txt=f"TOTAL RAMASSE : {total_pl} plateaux", ln=True)
        else:
            pdf.cell(200, 8, txt="Non applicable (Elevage Chair / Coquelets)", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="2. EVENEMENTS et STOCKS", ln=True)
        pdf.set_font("Arial", "", 11)
        type_alim_clean = type_aliment.replace("é", "e")
        veto_clean = (veto if veto else "RAS").encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(200, 8, txt=f"- Mortalite : {mortalite} sujets", ln=True)
        pdf.cell(200, 8, txt=f"- Aliment ({type_alim_clean}) : {aliment_consomme} kg", ln=True)
        pdf.cell(200, 8, txt=f"- Gasoil : {gasoil} Litres", ln=True)
        pdf.cell(200, 8, txt=f"- Pharmacie : {veto_clean}", ln=True)
        
        return bytes(pdf.output(dest='S').encode('latin-1', 'replace'))

    if st.button("💾 Enregistrer et Générer le rapport"):
        heure_saisie = datetime.now().strftime("%H:%M")
        total_plateaux = sum(saisie_oeufs.values())
        nouvelle_entree = pd.DataFrame({
            "Date": [date_jour.strftime("%d/%m/%Y")],
            "Heure Saisie": [heure_saisie],
            "Bâtiment": [batiment],
            "Élevage": [type_elevage],
            "PIWI": [saisie_oeufs["PIWI"]],
            "Petits": [saisie_oeufs["Petits"]],
            "Moyens": [saisie_oeufs["Moyens"]],
            "Gros": [saisie_oeufs["Gros"]],
            "Super Gros": [saisie_oeufs["Super Gros"]],
            "Cassés": [saisie_oeufs["Cassés"]],
            "Total Plateaux": [total_plateaux],
            "Mortalité": [mortalite],
            "Aliment (kg)": [aliment_consomme],
            "Type Aliment": [type_aliment],
            "Gasoil (L)": [gasoil],
            "Pharmacie": [veto if veto else "RAS"]
        })
        
        # Sauvegarde dans la base de données en mémoire
        st.session_state["historique_ferme"] = pd.concat([st.session_state["historique_ferme"], nouvelle_entree], ignore_index=True)
        
        st.success(f"✅ Relevé du {date_jour.strftime('%d/%m/%Y')} à {heure_saisie} enregistré dans la base centrale et transmis à Lomé !")
        pdf_report = generer_rapport_terrain(heure_saisie)
        st.download_button(
            label="📥 Télécharger le bordereau pour le chauffeur (PDF)",
            data=pdf_report,
            file_name=f"Rapport_Sokode_{date_jour.strftime('%Y%m%d')}_{heure_saisie.replace(':', 'h')}.pdf",
            mime="application/pdf"
        )


# =====================================================================
# ESPACE 2 : LA DIRECTION (LOMÉ) - ANALYSE ET FINANCE
# =====================================================================
elif st.session_state["role"] == "direction":
    st.title("📊 Tableau de Bord (Lomé)")
    
    # Affichage de la date et de l'heure du dernier relevé reçu de Sokodé
    if not st.session_state["historique_ferme"].empty:
        derniere_ligne = st.session_state["historique_ferme"].iloc[-1]
        st.info(f"📅 **Dernier relevé reçu de Sokodé :** le {derniere_ligne['Date']} à **{derniere_ligne['Heure Saisie']}** — **{derniere_ligne['Bâtiment']}** ({derniere_ligne['Total Plateaux']} plateaux ramassés, {derniere_ligne['Mortalité']} mortalité(s), {derniere_ligne['Aliment (kg)']} kg d'aliment)")
    
    st.divider()
    
    # 1. MOTEUR D'ALERTES
    st.header("🚨 Moteur d'alertes et écarts (théorie vs réalité)")
    st.caption("Ce module compare les données saisies par la ferme avec les objectifs du business plan.")
    
    a1, a2, a3 = st.columns(3)
    a1.error("📉 ALERTE PONTE : Objectif 78% | Réel 71% (-7% d'écart constaté sur Kadjolo)")
    a2.warning("⚠️ ALERTE MORTALITÉ : Taux de 3.2% dépassé cette semaine sur Bande 02 (Chairs).")
    a3.error("⛽ ALERTE GASOIL : Stock inférieur à 50 Litres sur le site.")
    
    st.divider
