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
        "Client": ["AGROSATH", "JOSUE"],
        "Type Vente": ["Œufs", "Œufs"],
        "Montant Dû (FCFA)": [350000, 125000],
        "Statut": ["En attente", "Retard"]
    })

if "historique_ferme" not in st.session_state:
    st.session_state["historique_ferme"] = pd.DataFrame({
        "Date": ["03/11/2026", "04/11/2026"],
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
        total_plateaux = sum(saisie_oeufs.values())
        nouvelle_entree = pd.DataFrame({
            "Date": [date_jour.strftime("%d/%m/%Y")],
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
        
        st.success(f"✅ Relevé du {date_jour.strftime('%d/%m/%Y')} enregistré dans la base centrale et transmis à Lomé !")
        pdf_report = generer_rapport_terrain()
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
    
    # Affichage de la date du dernier relevé reçu de Sokodé
    if not st.session_state["historique_ferme"].empty:
        derniere_ligne = st.session_state["historique_ferme"].iloc[-1]
        st.info(f"📅 **Dernier relevé reçu de Sokodé :** {derniere_ligne['Date']} — **{derniere_ligne['Bâtiment']}** ({derniere_ligne['Total Plateaux']} plateaux ramassés, {derniere_ligne['Mortalité']} mortalité(s), {derniere_ligne['Aliment (kg)']} kg d'aliment)")
    
    st.divider()
    
    # 1. MOTEUR D'ALERTES
    st.header("🚨 Moteur d'alertes et écarts (théorie vs réalité)")
    st.caption("Ce module compare les données saisies par la ferme avec les objectifs du business plan.")
    
    a1, a2, a3 = st.columns(3)
    a1.error("📉 ALERTE PONTE : Objectif 78% | Réel 71% (-7% d'écart constaté sur Kadjolo)")
    a2.warning("⚠️ ALERTE MORTALITÉ : Taux de 3.2% dépassé cette semaine sur Bande 02 (Chairs).")
    a3.error("⛽ ALERTE GASOIL : Stock inférieur à 50 Litres sur le site.")
    
    st.divider()
    
    # 2. VUE DÉTAILLÉE DU MAGASIN
    st.header("🏭 État du magasin et intrants (Nomenclature complète)")
    col_st1, col_st2, col_st3 = st.columns(3)
    col_st1.metric("Maïs", "12.5 Tonnes", "OK", delta_color="normal")
    col_st2.metric("Tourteaux de Soja", "1.2 Tonnes", "-100 kg (Critique)", delta_color="inverse")
    col_st3.metric("Son Cubé / Concentrés", "4.0 Tonnes", "OK", delta_color="normal")
    st.caption("Autres stocks suivis : Lysine, Aflabind, Coquillages, Produits Vétérinaires.")
    
    st.divider()
    
    # 3. MODULE FINANCIER CALIBRÉ
    st.header("💰 Module financier : valorisation de la production")
    st.write("Ce simulateur calcule le CA exact en fonction des calibres et du type de client (Grossiste vs Détaillant).")
    
    type_client = st.radio("Grille tarifaire à appliquer :", ["Grossiste", "Détaillant"], horizontal=True)
    grille_active = prix_grossiste if type_client == "Grossiste" else prix_detaillant
    
    st.subheader("Saisir les plateaux vendus par calibre :")
    cols_vente = st.columns(6)
    ventes = {}
    
    for i, cal in enumerate(calibres):
        with cols_vente[i]:
            val_defaut = 50 if cal == "Gros" or cal == "Moyens" else 0
            ventes[cal] = st.number_input(cal, value=val_defaut, min_value=0, step=5)
            st.caption(f"{grille_active[cal]} F/pl")
            
    ca_total = sum(ventes[cal] * grille_active[cal] for cal in calibres)
    
    st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>Chiffre d'Affaires estimé : {ca_total:,.0f} FCFA</h2>", unsafe_allow_html=True)
    
    st.divider()
    
    # 4. GESTION DES CRÉANCES
    st.header("📝 Gestion des créances et trésorerie")
    with st.form("formulaire_creance", clear_on_submit=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        date_op = col_f1.date_input("Date de l'opération", datetime.now())
        nouveau_client = col_f2.text_input("Nom du Client / Acheteur")
        nouveau_type = col_f3.selectbox("Type de vente", ["Œufs", "Poules Réforme", "Fiente/Engrais", "Poulets de chair"])
        
        col_f4, col_f5 = st.columns(2)
        nouveau_montant = col_f4.number_input("Montant Dû ou Payé (FCFA)", min_value=0, step=5000)
        nouveau_statut = col_f5.selectbox("Statut du paiement", ["En attente", "Retard", "Payé Cash"])
        
        if st.form_submit_button("➕ Ajouter l'opération financière"):
            if nouveau_client:
                nouvelle_ligne = pd.DataFrame({
                    "Date": [date_op.strftime("%d/%m/%Y")],
                    "Client": [nouveau_client.upper()],
                    "Type Vente": [nouveau_type],
                    "Montant Dû (FCFA)": [nouveau_montant],
                    "Statut": [nouveau_statut]
                })
                st.session_state["base_creances"] = pd.concat([st.session_state["base_creances"], nouvelle_ligne], ignore_index=True)
                st.success("Opération ajoutée.")
    
    if not st.session_state["base_creances"].empty:
        st.dataframe(st.session_state["base_creances"], use_container_width=True)
        
        def generer_pdf_creances(df):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 15)
            pdf.cell(190, 10, txt="Etat des Creances Clients - NGA Togo", ln=True, align='C')
            pdf.ln(8)
            
            largeurs = [30, 50, 40, 40, 30]
            colonnes = ["Date", "Client", "Type Vente", "Montant (FCFA)", "Statut"]
            pdf.set_font("Arial", "B", 10)
            for i, col in enumerate(colonnes):
                pdf.cell(largeurs[i], 10, col, border=1, align='C')
            pdf.ln()
            
            pdf.set_font("Arial", "", 10)
            for _, row in df.iterrows():
                txt_date = str(row['Date'])
                txt_client = str(row['Client'])[:22].encode('latin-1', 'replace').decode('latin-1')
                txt_type = str(row['Type Vente']).replace("Œ", "Oe").replace("é", "e")[:20]
                txt_montant = f"{int(row['Montant Dû (FCFA)']):,} F".replace(",", " ")
                txt_statut = str(row['Statut']).replace("é", "e")
                
                pdf.cell(largeurs[0], 9, txt_date, border=1, align='C')
                pdf.cell(largeurs[1], 9, txt_client, border=1)
                pdf.cell(largeurs[2], 9, txt_type, border=1)
                pdf.cell(largeurs[3], 9, txt_montant, border=1, align='R')
                pdf.cell(largeurs[4], 9, txt_statut, border=1, align='C')
                pdf.ln()
            return bytes(pdf.output(dest='S').encode('latin-1', 'replace'))

        pdf_creances = generer_pdf_creances(st.session_state["base_creances"])
        st.download_button(
            label="📄 Exporter l'état des créances (PDF)",
            data=pdf_creances,
            file_name=f"Etat_Creances_NGA_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )

    st.divider()

    # 5. NOUVEAU : BASE DE DONNÉES HISTORIQUE & ÉTATS RÉCAPITULATIFS
    st.header("🗄️ Base de données historique & États récapitulatifs (Sokodé)")
    st.write("Retrouvez ici l'historique complet et daté de toutes les saisies effectuées par la ferme pour tirer vos bilans.")

    df_hist = st.session_state["historique_ferme"]

    # Filtre par bâtiment pour tirer un état ciblé
    filtre_bat = st.selectbox("Filtrer l'état par bâtiment :", ["Tous les bâtiments", "Bande 01 (Kadjolo)", "Bande 02 (Djaguis)", "Bande 03"])
    if filtre_bat != "Tous les bâtiments":
        df_affiche = df_hist[df_hist["Bâtiment"] == filtre_bat]
    else:
        df_affiche = df_hist

    # Indicateurs de synthèse sur la période sélectionnée
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Plateaux produits", f"{int(df_affiche['Total Plateaux'].sum())} pl.")
    k2.metric("Total Cassés (Pertes)", f"{int(df_affiche['Cassés'].sum())} pl.")
    k3.metric("Mortalité cumulée", f"{int(df_affiche['Mortalité'].sum())} sujets")
    k4.metric("Aliment total consommé", f"{df_affiche['Aliment (kg)'].sum():,.1f} kg")

    # Tableau récapitulatif complet avec la date en première colonne
    st.dataframe(df_affiche, use_container_width=True)

    # Boutons pour tirer les états (Excel/CSV et PDF)
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        csv_hist = df_affiche.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 Tirer l'état complet pour Excel (CSV)",
            data=csv_hist,
            file_name=f"Historique_Production_NGA_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    with col_exp2:
        def generer_pdf_historique(df):
            pdf = FPDF(orientation='L') # Format Paysage pour afficher toutes les colonnes
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(275, 10, txt="Etat Recapitulatif de Production - NGA Togo", ln=True, align='C')
            pdf.ln(5)
            
            cols = ["Date", "Batiment", "PIWI", "Petits", "Moyens", "Gros", "S.Gros", "Casses", "Total Pl.", "Morts", "Alim(kg)", "Gasoil(L)"]
            largeurs = [25, 42, 16, 18, 20, 18, 20, 20, 22, 18, 28, 25]
            
            pdf.set_font("Arial", "B", 9)
            for i, c in enumerate(cols):
                pdf.cell(largeurs[i], 8, c, border=1, align='C')
            pdf.ln()
            
            pdf.set_font("Arial", "", 9)
            for _, row in df.iterrows():
                bat_clean = str(row['Bâtiment'])[:18].encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(largeurs[0], 8, str(row['Date']), border=1, align='C')
                pdf.cell(largeurs[1], 8, bat_clean, border=1)
                pdf.cell(largeurs[2], 8, str(row['PIWI']), border=1, align='C')
                pdf.cell(largeurs[3], 8, str(row['Petits']), border=1, align='C')
                pdf.cell(largeurs[4], 8, str(row['Moyens']), border=1, align='C')
                pdf.cell(largeurs[5], 8, str(row['Gros']), border=1, align='C')
                pdf.cell(largeurs[6], 8, str(row['Super Gros']), border=1, align='C')
                pdf.cell(largeurs[7], 8, str(row['Cassés']), border=1, align='C')
                pdf.cell(largeurs[8], 8, str(row['Total Plateaux']), border=1, align='C')
                pdf.cell(largeurs[9], 8, str(row['Mortalité']), border=1, align='C')
                pdf.cell(largeurs[10], 8, str(row['Aliment (kg)']), border=1, align='R')
                pdf.cell(largeurs[11], 8, str(row['Gasoil (L)']), border=1, align='R')
                pdf.ln()
                
            return bytes(pdf.output(dest='S').encode('latin-1', 'replace'))

        pdf_hist_data = generer_pdf_historique(df_affiche)
        st.download_button(
            label="📄 Tirer l'état récapitulatif officiel (PDF Paysage)",
            data=pdf_hist_data,
            file_name=f"Etat_Production_NGA_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
