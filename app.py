import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="NGA Togo - Production", layout="wide", page_icon="🐓")

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

# --- 2. CONNEXION À LA BASE DE DONNÉES GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def charger_donnees(onglet, colonnes_defaut):
    try:
        df = conn.read(worksheet=onglet, ttl=0)
        df = df.dropna(how="all")
        if df.empty:
            return pd.DataFrame(columns=colonnes_defaut)
        return df
    except Exception:
        return pd.DataFrame(columns=colonnes_defaut)

cols_ferme = [
    "Date", "Heure Saisie", "Bâtiment", "Élevage", "PIWI", "Petits", 
    "Moyens", "Gros", "Super Gros", "Cassés", "Surplus (Œufs vrac)", 
    "Total Plateaux", "Taux de Ponte (%)", "Mortalité", "Aliment (kg)", 
    "Type Aliment", "Gasoil (L)", "Pharmacie"
]
cols_creances = ["Date", "Heure", "Client", "Type Vente", "Montant Dû (FCFA)", "Statut"]

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

# --- 4. DONNÉES MÉTIER ---
races = ["Pondeuses (Isa Brown/Leghons)", "Poulets de Chair", "Coquelets"]
calibres = ["PIWI", "Petits", "Moyens", "Gros", "Super Gros", "Cassés"]
liste_bandes = [f"Bande 0{i} (Kadjolo/Djaguis)" if i <= 2 else f"Bande 0{i}" for i in range(1, 7)]

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
    st.info("Les données validées ici sont enregistrées directement dans la base centrale Google Sheets.")
    
    date_jour = st.date_input("Date du relevé", datetime.now())
    batiment = st.selectbox("Bâtiment / Bande concernée", liste_bandes)
    type_elevage = st.selectbox("Type d'élevage", races)
    
    st.divider()
    
    saisie_oeufs = {cal: 0 for cal in calibres}
    effectif_poules = 5000
    taux_ponte_calc = 0.0
    surplus_oeufs = 0
    
    if "Pondeuses" in type_elevage:
        st.subheader("🥚 1. Déclaration du ramassage & Calcul du Taux de Ponte")
        effectif_poules = st.number_input("Effectif total des sujets vivants dans la bande", min_value=1, value=5000, step=100)
        
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            saisie_oeufs["PIWI"] = st.number_input("PIWI (Plateaux)", min_value=0, step=1)
            saisie_oeufs["Petits"] = st.number_input("Petits (Plateaux)", min_value=0, step=1)
        with col_c2:
            saisie_oeufs["Moyens"] = st.number_input("Moyens (Plateaux)", min_value=0, step=1)
            saisie_oeufs["Gros"] = st.number_input("Gros (Plateaux)", min_value=0, step=1)
        with col_c3:
            saisie_oeufs["Super Gros"] = st.number_input("Super Gros (Plateaux)", min_value=0, step=1)
            saisie_oeufs["Cassés"] = st.number_input("Cassés / Pertes (Plateaux)", min_value=0, step=1)
            
        surplus_oeufs = st.number_input("Surplus (Nombre d'œufs en vrac / hors plateaux)", min_value=0, step=1)

        total_plateaux = sum(saisie_oeufs.values())
        total_oeufs_vrac = (total_plateaux * 30) + surplus_oeufs
        taux_ponte_calc = (total_oeufs_vrac / effectif_poules) * 100 if effectif_poules > 0 else 0.0
        
        st.markdown(f"### 📈 Taux de ponte calculé : **{taux_ponte_calc:.1f}%** ({total_oeufs_vrac} œufs ramassés pour {effectif_poules} poules)")
        st.divider()
    
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
        pdf.cell(200, 10, txt="1. OEUFS RAMASSES & PERFORMANCE", ln=True)
        pdf.set_font("Arial", "", 11)
        if "Pondeuses" in type_elevage:
            for k, v in saisie_oeufs.items():
                k_clean = k.replace("é", "e")
                pdf.cell(200, 8, txt=f"- {k_clean} : {v} plateaux", ln=True)
            pdf.cell(200, 8, txt=f"- Surplus en vrac : {surplus_oeufs} oeufs", ln=True)
            total_pl = sum(saisie_oeufs.values())
            pdf.set_font("Arial", "B", 11)
            pdf.cell(200, 8, txt=f"TOTAL : {total_pl} plateaux et {surplus_oeufs} oeufs | Taux de ponte : {taux_ponte_calc:.1f}%", ln=True)
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

    if st.button("💾 Enregistrer dans la base centrale et Générer le rapport"):
        with st.spinner("Enregistrement sécurisé sur Google Sheets en cours..."):
            heure_saisie = datetime.now().strftime("%H:%M")
            total_plateaux = sum(saisie_oeufs.values())
            
            df_existant = charger_donnees("Historique_Ferme", cols_ferme)
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
                "Surplus (Œufs vrac)": [surplus_oeufs],
                "Total Plateaux": [total_plateaux],
                "Taux de Ponte (%)": [f"{taux_ponte_calc:.1f}%"],
                "Mortalité": [mortalite],
                "Aliment (kg)": [aliment_consomme],
                "Type Aliment": [type_aliment],
                "Gasoil (L)": [gasoil],
                "Pharmacie": [veto if veto else "RAS"]
            })
            
            df_mis_a_jour = pd.concat([df_existant, nouvelle_entree], ignore_index=True)
            conn.update(worksheet="Historique_Ferme", data=df_mis_a_jour)
            
        st.success(f"✅ Relevé du {date_jour.strftime('%d/%m/%Y')} à {heure_saisie} sauvegardé définitivement et transmis à Lomé !")
        pdf_report = generer_rapport_terrain(heure_saisie)
        st.download_button(
            label="📥 Télécharger le bordereau pour le chauffeur (PDF)",
            data=pdf_report,
            file_name=f"Rapport_Sokode_{date_jour.strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )


# =====================================================================
# ESPACE 2 : LA DIRECTION (LOMÉ) - ANALYSE ET FINANCE
# =====================================================================
elif st.session_state["role"] == "direction":
    st.title("📊 Tableau de Bord (Lomé)")
    
    df_hist = charger_donnees("Historique_Ferme", cols_ferme)
    df_creances = charger_donnees("Creances", cols_creances)
    
    if not df_hist.empty:
        derniere_ligne = df_hist.iloc[-1]
        st.info(f"📅 **Dernier relevé reçu de Sokodé :** le {derniere_ligne['Date']} à **{derniere_ligne['Heure Saisie']}** — **{derniere_ligne['Bâtiment']}** ({derniere_ligne['Total Plateaux']} plateaux, Taux de ponte : {derniere_ligne['Taux de Ponte (%)']}, {derniere_ligne['Mortalité']} mort(s))")
    else:
        st.warning("Aucun relevé n'a encore été enregistré dans la base Google Sheets.")
        
    st.divider()
    
    # 1. MOTEUR D'ALERTES
    st.header("🚨 Moteur d'alertes et écarts (théorie vs réalité)")
    col_a1, col_a2, col_a3 = st.columns(3)
    col_a1.error("📉 ALERTE PONTE : Objectif 78% | Réel 71% (-7% d'écart sur Kadjolo)")
    col_a2.warning("⚠️ ALERTE MORTALITÉ : Taux de 3.2% dépassé sur Bande 02.")
    col_a3.error("⛽ ALERTE GASOIL : Stock inférieur à 50 Litres sur le site.")
    
    st.divider()
    
    # 2. VUE DÉTAILLÉE DU MAGASIN
    st.header("🏭 État du magasin et intrants")
    col_st1, col_st2, col_st3 = st.columns(3)
    col_st1.metric("Maïs", "12.5 Tonnes", "OK")
    col_st2.metric("Tourteaux de Soja", "1.2 Tonnes", "-100 kg (Critique)", delta_color="inverse")
    col_st3.metric("Son Cubé / Concentrés", "4.0 Tonnes", "OK")
    
    st.divider()
    
    # 3. MODULE FINANCIER & MULTI-CLIENTS
    st.header("💰 Module financier & Ventes multi-clients")
    type_client = st.radio("Grille tarifaire de référence :", ["Grossiste", "Détaillant"], horizontal=True)
    grille_active = prix_grossiste if type_client == "Grossiste" else prix_detaillant
    
    clients_disponibles = ["Client 01 - AGROSATH", "Client 02 - JOSUE", "Client 03 - BOUTIQUE CENTRALE", "Client 04 - MARCHE CENTRAL", "Client 05 - PASSAGER 1", "Client 06 - PASSAGER 2"]
    client_actif = st.selectbox("Sélectionner le client pour cette saisie de vente :", clients_disponibles)
    
    st.subheader(f"Plateaux vendus pour {client_actif} :")
    cols_vente = st.columns(6)
    ventes = {}
    
    for i, cal in enumerate(calibres):
        with cols_vente[i]:
            val_def = 20 if cal == "Gros" else 0
            ventes[cal] = st.number_input(f"{cal}", value=val_def, min_value=0, step=5, key=f"v_{cal}")
            st.caption(f"{grille_active[cal]} F/pl")
            
    ca_client = sum(ventes[cal] * grille_active[cal] for cal in calibres)
    st.markdown(f"<h3 style='color: #4CAF50;'>Chiffre d'Affaires pour {client_actif} : {ca_client:,.0f} FCFA</h3>", unsafe_allow_html=True)
    
    st.divider()
    
    # 4. GESTION DES CRÉANCES
    st.header("📝 Gestion des créances et trésorerie")
    with st.form("formulaire_creance", clear_on_submit=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        date_op = col_f1.date_input("Date de l'opération", datetime.now())
        nouveau_client = col_f2.selectbox("Acheteur / Client", clients_disponibles)
        nouveau_type = col_f3.selectbox("Type de vente", ["Œufs", "Poules Réforme", "Fiente/Engrais", "Poulets de chair"])
        
        col_f4, col_f5 = st.columns(2)
        nouveau_montant = col_f4.number_input("Montant Dû ou Payé (FCFA)", min_value=0, step=5000)
        nouveau_statut = col_f5.selectbox("Statut du paiement", ["En attente", "Retard", "Payé Cash"])
        
        if st.form_submit_button("➕ Enregistrer l'opération sur Google Sheets"):
            with st.spinner("Sauvegarde de l'opération financière..."):
                heure_op = datetime.now().strftime("%H:%M")
                nouvelle_ligne = pd.DataFrame({
                    "Date": [date_op.strftime("%d/%m/%Y")],
                    "Heure": [heure_op],
                    "Client": [nouveau_client],
                    "Type Vente": [nouveau_type],
                    "Montant Dû (FCFA)": [nouveau_montant],
                    "Statut": [nouveau_statut]
                })
                df_creances_maj = pd.concat([df_creances, nouvelle_ligne], ignore_index=True)
                conn.update(worksheet="Creances", data=df_creances_maj)
            st.success("Opération enregistrée dans la base de données !")
            st.rerun()
    
    if not df_creances.empty:
        st.dataframe(df_creances, use_container_width=True)

    st.divider()

    # 5. BASE DE DONNÉES HISTORIQUE & ÉTATS RÉCAPITULATIFS
    st.header("🗄️ Base de données historique & États récapitulatifs (Sokodé)")

    if not df_hist.empty:
        # Conversion sécurisée en numérique pour les calculs de totaux
        for col_num in ["Total Plateaux", "Cassés", "Mortalité", "Aliment (kg)"]:
            df_hist[col_num] = pd.to_numeric(df_hist[col_num], errors="coerce").fillna(0)

        filtre_bat = st.selectbox("Filtrer l'état par bâtiment :", ["Tous les bâtiments"] + liste_bandes)
        if filtre_bat != "Tous les bâtiments":
            df_affiche = df_hist[df_hist["Bâtiment"] == filtre_bat]
        else:
            df_affiche = df_hist

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Plateaux produits", f"{int(df_affiche['Total Plateaux'].sum())} pl.")
        k2.metric("Total Cassés (Pertes)", f"{int(df_affiche['Cassés'].sum())} pl.")
        k3.metric("Mortalité cumulée", f"{int(df_affiche['Mortalité'].sum())} sujets")
        k4.metric("Aliment total consommé", f"{df_affiche['Aliment (kg)'].sum():,.1f} kg")

        st.dataframe(df_affiche, use_container_width=True)

        csv_hist = df_affiche.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 Tirer l'état complet pour Excel (CSV)",
            data=csv_hist,
            file_name=f"Historique_Production_NGA_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("L'historique s'affichera ici dès que Sokodé aura effectué sa première saisie.")
