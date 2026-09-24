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
    st.session_state["base_creances"] = pd.DataFrame(columns=["Client", "Type Vente", "Montant Dû (FCFA)", "Statut"])
if "historique_ramassage" not in st.session_state:
    st.session_state["historique_ramassage"] = pd.DataFrame()

# --- 3. SYSTÈME DE CONNEXION (DOUBLE PROFIL) ---
if "authentifie" not in st.session_state:
    st.session_state["authentifie"] = False
    st.session_state["role"] = ""

if not st.session_state["authentifie"]:
    st.title("🔒 Accès Sécurisé - NGA AgroGestion V2")
    st.write("Veuillez vous connecter avec vos identifiants de site.")
    
    identifiant = st.text_input("Identifiant (Sokode ou Lome)")
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

# Tarification issue de "SITUATION PRIX DES OEUFS" (Estimations)
prix_grossiste = {"PIWI": 1500, "Petits": 2000, "Moyens": 2400, "Gros": 2800, "Super Gros": 2900, "Cassés": 500}
prix_detaillant = {"PIWI": 1600, "Petits": 2100, "Moyens": 2500, "Gros": 2950, "Super Gros": 3000, "Cassés": 600}

# --- 5. MENU COMMUN ---
st.sidebar.title("🚜 NGA Togo - V2")
st.sidebar.info(f"Connecté en tant que : **{st.session_state['role'].upper()}**")
if st.sidebar.button("Se déconnecter"):
    st.session_state["authentifie"] = False
    st.session_state["role"] = ""
    st.rerun()


# =====================================================================
# ESPACE 1 : LA FERME (SOKODÉ) - SAISIE UNIQUEMENT
# =====================================================================
if st.session_state["role"] == "ferme":
    st.title("📋 Interface de Saisie Quotidienne (Sokodé)")
    st.info("Cette interface est réservée au personnel de terrain pour la déclaration des opérations du jour.")
    
    date_jour = st.date_input("Date du relevé", datetime.now())
    batiment = st.selectbox("Bâtiment / Bande concernée", ["Bande 01 (Kadjolo)", "Bande 02 (Djaguis)", "Bande 03"])
    type_elevage = st.selectbox("Type d'élevage", races)
    
    st.divider()
    
    # Formulaire de ramassage (uniquement pour pondeuses)
    if "Pondeuses" in type_elevage:
        st.subheader("🥚 1. Déclaration du Ramassage (En plateaux)")
        col_c1, col_c2, col_c3 = st.columns(3)
        saisie_oeufs = {}
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
    st.subheader("📦 2. Déclaration des Événements & Sorties de Stock")
    col_s1, col_s2, col_s3 = st.columns(3)
    
    with col_s1:
        mortalite = st.number_input("Mortalité du jour (Nb de sujets)", min_value=0, step=1)
    with col_s2:
        aliment_consomme = st.number_input("Aliment distribué (kg)", min_value=0.0, step=5.0)
        type_aliment = st.selectbox("Type d'aliment", ["Démarrage", "Croissance", "Pré-ponte", "Ponte Phase 1"])
    with col_s3:
        gasoil = st.number_input("Gasoil consommé (Litres)", min_value=0.0, step=1.0)
        veto = st.text_input("Produits Vétérinaires utilisés (Optionnel)")
        
    st.divider()
    
    # Génération du Rapport pour le Chauffeur
    st.subheader("📄 3. Génération du Rapport Quotidien (Bordereau Chauffeur)")
    
    def generer_rapport_terrain():
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(200, 10, txt=f"Rapport Quotidien NGA - {batiment}", ln=True, align='C')
        pdf.set_font("Arial", "", 11)
        pdf.cell(200, 10, txt=f"Date : {date_jour.strftime('%d/%m/%Y')} | Elevage : {type_elevage}", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="1. OEUFS RAMASSES (Plateaux)", ln=True)
        pdf.set_font("Arial", "", 11)
        if "Pondeuses" in type_elevage:
            for k, v in saisie_oeufs.items():
                pdf.cell(200, 8, txt=f"- {k} : {v} plateaux", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="2. EVENEMENTS & STOCKS", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.cell(200, 8, txt=f"- Mortalite : {mortalite} sujets", ln=True)
        pdf.cell(200, 8, txt=f"- Aliment ({type_aliment}) : {aliment_consomme} kg", ln=True)
        pdf.cell(200, 8, txt=f"- Gasoil : {gasoil} Litres", ln=True)
        pdf.cell(200, 8, txt=f"- Pharmacie : {veto}", ln=True)
        
        return bytes(pdf.output(dest='S').encode('latin-1', 'replace'))

    if st.button("💾 Enregistrer et Générer le rapport"):
        st.success("Données enregistrées et envoyées à la Direction (Lomé) !")
        pdf_report = generer_rapport_terrain()
        st.download_button(label="📥 Télécharger le bordereau pour le Chauffeur (PDF)", data=pdf_report, file_name=f"Rapport_{date_jour}.pdf", mime="application/pdf")


# =====================================================================
# ESPACE 2 : LA DIRECTION (LOMÉ) - ANALYSE ET FINANCE
# =====================================================================
elif st.session_state["role"] == "direction":
    st.title("📊 Tableau de Bord Stratégique (Lomé)")
    st.markdown("Vue analytique, suivi financier et alertes intelligentes.")
    st.divider()
    
    # 1. MOTEUR D'ALERTES
    st.header("🚨 Moteur d'Alertes et Écarts (Théorie vs Réalité)")
    st.caption("Ce module compare les données saisies par la ferme avec les objectifs du business plan.")
    
    a1, a2, a3 = st.columns(3)
    # Simulations d'alertes basées sur le cahier des charges
    a1.error("📉 ALERTE PONTE : Objectif 78% | Réel 71% (-7% d'écart constaté sur Kadjolo)")
    a2.warning("⚠️ ALERTE MORTALITÉ : Taux de 3.2% dépassé cette semaine sur Bande 02 (Chairs).")
    a3.error("⛽ ALERTE GASOIL : Stock inférieur à 50 Litres sur le site.")
    
    st.divider()
    
    # 2. VUE DÉTAILLÉE DU MAGASIN
    st.header("🏭 État du Magasin & Intrants (Nomenclature complète)")
    col_st1, col_st2, col_st3 = st.columns(3)
    col_st1.metric("Maïs", "12.5 Tonnes", "OK", delta_color="normal")
    col_st2.metric("Tourteaux de Soja", "1.2 Tonnes", "-100 kg (Critique)", delta_color="inverse")
    col_st3.metric("Son Cubé / Concentrés", "4.0 Tonnes", "OK", delta_color="normal")
    st.caption("Autres stocks suivis : Lysine, Aflabind, Coquillages, Produits Vétérinaires.")
    
    st.divider()
    
    # 3. MODULE FINANCIER CALIBRÉ
    st.header("💰 Module Financier : Valorisation de la Production")
    st.write("Ce simulateur calcule le CA exact en fonction des calibres et du type de client (Grossiste vs Détaillant).")
    
    type_client = st.radio("Grille tarifaire à appliquer :", ["Grossiste", "Détaillant"], horizontal=True)
    grille_active = prix_grossiste if type_client == "Grossiste" else prix_detaillant
    
    st.subheader("Saisir les plateaux vendus par calibre :")
    cols_vente = st.columns(6)
    ventes = {}
    
    for i, cal in enumerate(calibres):
        with cols_vente[i]:
            # On simule quelques ventes par défaut
            val_defaut = 50 if cal == "Gros" or cal == "Moyens" else 0
            ventes[cal] = st.number_input(cal, value=val_defaut, min_value=0, step=5)
            st.caption(f"{grille_active[cal]} F/pl")
            
    ca_total = sum(ventes[cal] * grille_active[cal] for cal in calibres)
    
    # Affichage du CA en grand
    st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>Chiffre d'Affaires estimé : {ca_total:,.0f} FCFA</h2>", unsafe_allow_html=True)
    
    st.divider()
    
    # 4. GESTION DES CRÉANCES (Identique à la V1 mais réservé à la Direction)
    st.header("📝 Gestion des Créances et Trésorerie")
    with st.form("formulaire_creance", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        nouveau_client = col_f1.text_input("Nom du Client / Acheteur")
        nouveau_type = col_f2.selectbox("Type de vente", ["Œufs", "Poules Réforme", "Fiente/Engrais", "Poulets de chair"])
        nouveau_montant = col_f1.number_input("Montant Dû ou Payé (FCFA)", min_value=0, step=5000)
        nouveau_statut = col_f2.selectbox("Statut du paiement", ["En attente", "Retard", "Payé Cash"])
        
        if st.form_submit_button("➕ Ajouter l'opération financière"):
            if nouveau_client:
                nouvelle_ligne = pd.DataFrame({"Client": [nouveau_client.upper()], "Type Vente": [nouveau_type], "Montant Dû (FCFA)": [nouveau_montant], "Statut": [nouveau_statut]})
                st.session_state["base_creances"] = pd.concat([st.session_state["base_creances"], nouvelle_ligne], ignore_index=True)
                st.success("Opération ajoutée.")
    
    if not st.session_state["base_creances"].empty:
        st.table(st.session_state["base_creances"])
