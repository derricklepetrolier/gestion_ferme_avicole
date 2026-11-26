import streamlit as st
import time
import hmac
import hashlib
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="NGA AgroGestion", layout="wide", page_icon="🐓")

# --- MASQUER L'INTERFACE, LES MENUS ET LES LOGOS EN BAS A DROITE ---
cacher_menu_style = """
        <style>
        #MainMenu {visibility: hidden;} 
        [data-testid="stToolbar"] {visibility: hidden !important;} 
        footer {visibility: hidden !important;} 
        header {visibility: hidden !important;} 
        [data-testid="stDecoration"] {display: none;} 
        .stAppDeployButton {display: none !important;} 
        footer {display: none !important;} 
        iframe {display: none !important;} 
        </style>
        """
st.markdown(cacher_menu_style, unsafe_allow_html=True)

# --- 2. CONNEXION A LA BASE DE DONNEES ---
conn = st.connection("gsheets", type=GSheetsConnection)

def charger_donnees(onglet, colonnes_defaut):
    try:
        df = conn.read(worksheet=onglet, ttl=60)
        df = df.dropna(how="all")
        if df.empty:
            return pd.DataFrame(columns=colonnes_defaut)
        return df
    except Exception as e:
        st.error(f"Erreur de lecture sur l'onglet {onglet} (patientez quelques secondes et actualisez) : {e}")
        return pd.DataFrame(columns=colonnes_defaut)

def parse_float(val, defaut=0.0):
    try:
        return float(str(val).replace("%", "").replace(",", ".").replace(" ", "").strip())
    except Exception:
        return defaut

def format_fcfa(montant):
    return f"{int(round(montant)):,}".replace(",", " ") + " FCFA"

cols_ferme = [
    "Date", "Heure Saisie", "Bâtiment", "Élevage", "PIWI", "Petits", 
    "Moyens", "Gros", "Super Gros", "Cassés", "Surplus (Œufs vrac)", 
    "Total Plateaux", "Taux de Ponte (%)", "Mortalité", "Aliment (kg)", 
    "Type Aliment", "Gasoil (L)", "Pharmacie"
]
cols_creances = ["Date", "Heure", "Client", "Type Vente", "Montant Dû (FCFA)", "Statut"]
cols_stock = ["Intrant", "Quantité", "Unité", "Seuil Alerte"]
cols_params = ["Paramètre", "Valeur"]

# --- 3. GESTION PERSISTANTE ET SECURISEE DE LA CONNEXION (AVEC EXPIRATION) ---
DUREE_INACTIVITE_MINUTES = 60  # Modifiez cette valeur selon vos besoins (ex: 30, 60, 120)
CLE_SECRETE_SESSION = "NGA_Togo_2026_Cle_Secrete_91f2c7"

def generer_jeton(role, timestamp=None):
    ts = int(timestamp if timestamp is not None else time.time())
    message = f"{role}.{ts}".encode("utf-8")
    signature = hmac.new(CLE_SECRETE_SESSION.encode("utf-8"), message, hashlib.sha256).hexdigest()[:16]
    return f"{role}.{ts}.{signature}"

def verifier_jeton(jeton):
    try:
        role, ts_str, sig_recue = jeton.split(".")
        if role not in ["ferme", "direction"]:
            return None, False
        ts = int(ts_str)
        message = f"{role}.{ts}".encode("utf-8")
        sig_attendue = hmac.new(CLE_SECRETE_SESSION.encode("utf-8"), message, hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(sig_recue, sig_attendue):
            return None, False
        if (time.time() - ts) > (DUREE_INACTIVITE_MINUTES * 60):
            return None, True  # Jeton expiré
        return role, False
    except Exception:
        return None, False

params = st.query_params
session_token = params.get("session", "")
session_expiree = False

if session_token:
    role_valide, est_expire = verifier_jeton(session_token)
    if role_valide:
        st.session_state["authentifie"] = True
        st.session_state["role"] = role_valide
        # Réinitialise le compteur d'inactivité à chaque interaction
        st.query_params["session"] = generer_jeton(role_valide)
    else:
        st.session_state["authentifie"] = False
        st.session_state["role"] = ""
        st.query_params.clear()
        if est_expire:
            session_expiree = True
else:
    st.session_state["authentifie"] = False
    st.session_state["role"] = ""

if not st.session_state["authentifie"]:
    st.title("🥚🐓 NGA AgroGestion")
    if session_expiree:
        st.warning(f"⏱️ Votre session a expiré après {DUREE_INACTIVITE_MINUTES} minutes d'inactivité. Veuillez vous reconnecter.")
    st.write("Veuillez vous connecter avec vos identifiants de site.")
    
    identifiant = st.text_input("Identifiant")
    mot_de_passe = st.text_input("Mot de passe", type="password")
    
    if st.button("Se connecter"):
        if identifiant == "Sokode" and mot_de_passe == "Terrain2026!":
            st.session_state["authentifie"] = True
            st.session_state["role"] = "ferme"
            st.query_params["session"] = generer_jeton("ferme")
            st.rerun()
        elif identifiant == "Lome" and mot_de_passe == "Direction2026!":
            st.session_state["authentifie"] = True
            st.session_state["role"] = "direction"
            st.query_params["session"] = generer_jeton("direction")
            st.rerun()
        else:
            st.error("Identifiant ou mot de passe incorrect.")
    st.stop()

# --- 4. DONNEES METIER ---
races = ["Pondeuses (Isa Brown)", "Poulets de chair", "Coquelets"]
calibres = ["PIWI", "Petits", "Moyens", "Gros", "Super Gros", "Cassés"]
liste_bandes = [f"Bande 0{i} (Kadjolo)" if i <= 2 else f"Bande 0{i}" for i in range(1, 7)]
liste_aliments = ["Démarrage", "Croissance", "Pré ponte", "Ponte phase 1", "Ponte phase 2", "Finition"]

prix_grossiste = {"PIWI": 1500, "Petits": 2000, "Moyens": 2400, "Gros": 2800, "Super Gros": 2900, "Cassés": 500}
prix_detaillant = {"PIWI": 1600, "Petits": 2100, "Moyens": 2500, "Gros": 2950, "Super Gros": 3000, "Cassés": 600}

# --- 5. MENU COMMUN ---
st.sidebar.title("🥚🐓 NGA Togo")
st.sidebar.info(f"Connecté en tant que : **{st.session_state['role'].upper()}**")
if st.sidebar.button("🔄 Actualiser les données"):
    st.cache_data.clear()
    st.rerun()
if st.sidebar.button("Se déconnecter"):
    st.session_state["authentifie"] = False
    st.session_state["role"] = ""
    st.query_params.clear()
    st.rerun()


# =====================================================================
# ESPACE 1 : LA FERME (SOKODE)
# =====================================================================
if st.session_state["role"] == "ferme":
    st.title("📋 Interface de saisie quotidienne (Sokodé)")
    st.info("Les données validées ici sont transmises en temps réel à la direction.")
    
    date_jour = st.date_input("Date du relevé", datetime.now(), max_value=datetime.now().date())
    batiment = st.selectbox("Bâtiment ou bande concernée", liste_bandes)
    type_elevage = st.selectbox("Type d'élevage", races)

    # Vérification anti-doublon pour la date et le bâtiment sélectionnés
    df_hist_verif = charger_donnees("Historique_Ferme", cols_ferme)
    date_str = date_jour.strftime("%d/%m/%Y")
    doublon_existe = False
    if not df_hist_verif.empty and "Date" in df_hist_verif.columns and "Bâtiment" in df_hist_verif.columns:
        masque_doublon = (
            (df_hist_verif["Date"].astype(str).str.strip() == date_str) &
            (df_hist_verif["Bâtiment"].astype(str).str.strip() == batiment)
        )
        doublon_existe = masque_doublon.any()

    if doublon_existe:
        st.warning(f"⚠️ Un relevé a déjà été enregistré pour **{batiment}** à la date du **{date_str}**.")
    
    st.divider()
    
    saisie_oeufs = {cal: 0 for cal in calibres}
    effectif_poules = 0
    taux_ponte_calc = 0.0
    surplus_oeufs = 0
    total_plateaux = 0
    
    if "Pondeuses" in type_elevage:
        st.subheader("🥚 1. Déclaration du ramassage et calcul du taux de ponte")
        effectif_poules = st.number_input("Effectif total des sujets vivants dans la bande", min_value=0, value=0, step=100)
        
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            saisie_oeufs["PIWI"] = st.number_input("PIWI (plateaux)", min_value=0, step=1)
            saisie_oeufs["Petits"] = st.number_input("Petits (plateaux)", min_value=0, step=1)
        with col_c2:
            saisie_oeufs["Moyens"] = st.number_input("Moyens (plateaux)", min_value=0, step=1)
            saisie_oeufs["Gros"] = st.number_input("Gros (plateaux)", min_value=0, step=1)
        with col_c3:
            saisie_oeufs["Super Gros"] = st.number_input("Super Gros (plateaux)", min_value=0, step=1)
            saisie_oeufs["Cassés"] = st.number_input("Cassés ou pertes (plateaux)", min_value=0, step=1)
            
        surplus_oeufs = st.number_input("Surplus (nombre d'œufs en vrac hors plateaux)", min_value=0, step=1)

        total_plateaux = sum(saisie_oeufs.values())
        plateaux_vendables = total_plateaux - saisie_oeufs["Cassés"]
        total_oeufs_vrac = (total_plateaux * 30) + surplus_oeufs
        taux_ponte_calc = (total_oeufs_vrac / effectif_poules) * 100 if effectif_poules > 0 else 0.0
        
        if effectif_poules > 0:
            st.markdown(
                f"### 📈 Taux de ponte calculé : **{taux_ponte_calc:.1f}%** "
                f"({total_oeufs_vrac} œufs ramassés pour {effectif_poules} poules | "
                f"**{plateaux_vendables} plateaux vendables**, {saisie_oeufs['Cassés']} cassés)"
            )
        else:
            st.info("Saisissez l'effectif réel des sujets vivants pour afficher le taux de ponte.")
        st.divider()
    
    num_etape_stock = 2 if "Pondeuses" in type_elevage else 1
    num_etape_pdf = 3 if "Pondeuses" in type_elevage else 2

    st.subheader(f"📦 {num_etape_stock}. Déclaration des événements et des sorties de stock")
    col_s1, col_s2, col_s3 = st.columns(3)
    
    with col_s1:
        mortalite = st.number_input("Mortalité du jour (nombre de sujets)", min_value=0, step=1)
    with col_s2:
        aliment_consomme = st.number_input("Aliment distribué (kg)", min_value=0.0, step=5.0)
        index_alim_defaut = liste_aliments.index("Ponte phase 1") if "Pondeuses" in type_elevage else 0
        type_aliment = st.selectbox("Type d'aliment", liste_aliments, index=index_alim_defaut, key=f"alim_{type_elevage}")
    with col_s3:
        gasoil = st.number_input("Gasoil consommé (litres)", min_value=0.0, step=1.0)
        veto = st.text_input("Produits vétérinaires utilisés (optionnel)")
        
    st.divider()
    st.subheader(f"📄 {num_etape_pdf}. Génération du rapport quotidien (bordereau chauffeur)")
    
    def generer_rapport_terrain(heure_actuelle):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(200, 10, txt=f"Rapport Quotidien NGA - {batiment}", ln=True, align='C')
        pdf.set_font("Arial", "", 11)
        pdf.cell(200, 10, txt=f"Date : {date_str} a {heure_actuelle} | Elevage : {type_elevage}", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="1. OEUFS RAMASSES ET PERFORMANCE", ln=True)
        pdf.set_font("Arial", "", 11)
        if "Pondeuses" in type_elevage:
            for k, v in saisie_oeufs.items():
                k_clean = k.replace("é", "e")
                pdf.cell(200, 8, txt=f"- {k_clean} : {v} plateaux", ln=True)
            pdf.cell(200, 8, txt=f"- Surplus en vrac : {surplus_oeufs} oeufs", ln=True)
            total_pl = sum(saisie_oeufs.values())
            pl_vendables = total_pl - saisie_oeufs["Cassés"]
            pdf.ln(2)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(200, 8, txt=f"PLATEAUX VENDABLES (hors casses) : {pl_vendables} plateaux", ln=True)
            pdf.cell(200, 8, txt=f"TOTAL RAMASSE : {total_pl} plateaux et {surplus_oeufs} oeufs | Taux de ponte : {taux_ponte_calc:.1f}%", ln=True)
        else:
            pdf.cell(200, 8, txt="Non applicable", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="2. EVENEMENTS ET STOCKS", ln=True)
        pdf.set_font("Arial", "", 11)
        type_alim_clean = type_aliment.replace("é", "e")
        veto_clean = (veto if veto else "RAS").encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(200, 8, txt=f"- Mortalite : {mortalite} sujets", ln=True)
        pdf.cell(200, 8, txt=f"- Aliment ({type_alim_clean}) : {aliment_consomme} kg", ln=True)
        pdf.cell(200, 8, txt=f"- Gasoil : {gasoil} litres", ln=True)
        pdf.cell(200, 8, txt=f"- Pharmacie : {veto_clean}", ln=True)
        
        return bytes(pdf.output(dest='S').encode('latin-1', 'replace'))

    confirmer_doublon = True
    if doublon_existe:
        confirmer_doublon = st.checkbox("Confirmer l'ajout d'un second relevé pour ce bâtiment à cette même date")

    if st.button("💾 Enregistrer et générer le rapport"):
        releve_vide = (
            total_plateaux == 0 and surplus_oeufs == 0 and mortalite == 0
            and aliment_consomme == 0 and gasoil == 0 and not veto.strip()
        )

        if "Pondeuses" in type_elevage and effectif_poules <= 0:
            st.error("Veuillez saisir l'effectif total des sujets vivants dans la bande avant d'enregistrer.")
        elif releve_vide:
            st.error("Le relevé est vide. Veuillez saisir au moins une donnée avant d'enregistrer.")
        elif doublon_existe and not confirmer_doublon:
            st.error("Cochez la case de confirmation ci-dessus pour valider ce second relevé.")
        else:
            with st.spinner("Enregistrement en cours..."):
                heure_saisie = datetime.now().strftime("%H:%M")
                df_existant = charger_donnees("Historique_Ferme", cols_ferme)
                nouvelle_entree = pd.DataFrame({
                    "Date": [date_str],
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
                    "Pharmacie": [veto.strip() if veto.strip() else "RAS"]
                })
                
                df_mis_a_jour = pd.concat([df_existant, nouvelle_entree], ignore_index=True)
                conn.update(worksheet="Historique_Ferme", data=df_mis_a_jour)

                # Déduction automatique du gasoil dans le stock du magasin
                if gasoil > 0:
                    df_stock_ferme = charger_donnees("Stock", cols_stock)
                    if not df_stock_ferme.empty and "Intrant" in df_stock_ferme.columns:
                        masque_gasoil = df_stock_ferme["Intrant"].astype(str).str.lower().str.contains("gasoil", na=False)
                        if masque_gasoil.any():
                            idx_g = df_stock_ferme[masque_gasoil].index[0]
                            qte_actuelle = parse_float(df_stock_ferme.at[idx_g, "Quantité"], 0.0)
                            df_stock_ferme.at[idx_g, "Quantité"] = max(0.0, round(qte_actuelle - gasoil, 2))
                            conn.update(worksheet="Stock", data=df_stock_ferme)

                st.cache_data.clear()
                
            st.success(f"✅ Relevé du {date_str} à {heure_saisie} enregistré et transmis à Lomé.")
            pdf_report = generer_rapport_terrain(heure_saisie)
            st.download_button(
                label="📥 Télécharger le bordereau pour le chauffeur (PDF)",
                data=pdf_report,
                file_name=f"Rapport_Sokode_{date_jour.strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )


# =====================================================================
# ESPACE 2 : LA DIRECTION (LOME)
# =====================================================================
elif st.session_state["role"] == "direction":
    st.title("📊 Tableau de bord (Lomé)")
    
    df_hist = charger_donnees("Historique_Ferme", cols_ferme)
    df_creances = charger_donnees("Creances", cols_creances)
    df_stock = charger_donnees("Stock", cols_stock)
    df_params = charger_donnees("Parametres", cols_params)

    # Valeurs par défaut du magasin si l'onglet Stock est vide
    if df_stock.empty:
        df_stock = pd.DataFrame({
            "Intrant": ["Maïs", "Tourteaux de soja", "Son cubé", "Gasoil"],
            "Quantité": [12.5, 1.2, 4.0, 45.0],
            "Unité": ["Tonnes", "Tonnes", "Tonnes", "Litres"],
            "Seuil Alerte": [5.0, 1.5, 1.0, 50.0]
        })

    # Lecture des seuils d'alerte de production (base centrale ou valeurs par défaut)
    params_dict = {}
    if not df_params.empty and "Paramètre" in df_params.columns and "Valeur" in df_params.columns:
        params_dict = dict(zip(df_params["Paramètre"], df_params["Valeur"]))

    objectif_ponte = parse_float(params_dict.get("Objectif_Ponte", st.session_state.get("objectif_ponte", 78.0)), 78.0)
    seuil_mortalite = int(parse_float(params_dict.get("Seuil_Mortalite", st.session_state.get("seuil_mortalite", 10)), 10.0))

    if not df_hist.empty:
        derniere_ligne = df_hist.iloc[-1]
        dernier_pl = int(parse_float(derniere_ligne["Total Plateaux"], 0))
        dernier_mort = int(parse_float(derniere_ligne["Mortalité"], 0))
        st.info(
            f"📅 **Dernier relevé reçu de Sokodé :** le {derniere_ligne['Date']} à **{derniere_ligne['Heure Saisie']}** "
            f"sur **{derniere_ligne['Bâtiment']}** ({dernier_pl} plateaux, taux de ponte : {derniere_ligne['Taux de Ponte (%)']}, {dernier_mort} mort)"
        )
    else:
        st.warning("Aucun relevé n'a encore été enregistré dans la base centrale.")
        
    st.divider()
    
    # --- MOTEUR D'ALERTES DYNAMIQUE ---
    st.header("🚨 Moteur d'alertes et écarts")
    col_a1, col_a2, col_a3 = st.columns(3)

    # 1. Alerte ponte (dernier relevé pondeuses)
    if not df_hist.empty and "Élevage" in df_hist.columns:
        df_pondeuses = df_hist[df_hist["Élevage"].astype(str).str.contains("Pondeuses", case=False, na=False)]
        if not df_pondeuses.empty:
            dernier_ponte = df_pondeuses.iloc[-1]
            taux_reel = parse_float(dernier_ponte["Taux de Ponte (%)"], 0.0)
            ecart_ponte = taux_reel - objectif_ponte
            bat_ponte = dernier_ponte["Bâtiment"]
            if taux_reel < objectif_ponte:
                col_a1.error(f"📉 Alerte ponte : objectif {objectif_ponte:.1f} %, réel {taux_reel:.1f} % ({ecart_ponte:+.1f} % sur {bat_ponte})")
            else:
                col_a1.success(f"📈 Ponte conforme : réel {taux_reel:.1f} % (objectif {objectif_ponte:.1f} % sur {bat_ponte})")
        else:
            col_a1.info("📉 Ponte : aucun relevé pondeuses enregistré.")
    else:
        col_a1.info("📉 Ponte : en attente d'un relevé de Sokodé.")

    # 2. Alerte mortalité (dernier relevé)
    if not df_hist.empty:
        mort_reelle = int(parse_float(df_hist.iloc[-1]["Mortalité"], 0.0))
        bat_mort = df_hist.iloc[-1]["Bâtiment"]
        if mort_reelle > seuil_mortalite:
            col_a2.warning(f"⚠️ Alerte mortalité : {mort_reelle} sujets sur {bat_mort} (seuil max : {seuil_mortalite})")
        else:
            col_a2.success(f"✅ Mortalité normale : {mort_reelle} sujet(s) sur {bat_mort} (seuil max : {seuil_mortalite})")
    else:
        col_a2.info("⚠️ Mortalité : en attente d'un relevé de Sokodé.")

    # 3. Alerte stocks (intrants sous seuil critique)
    alertes_stock = []
    for _, row in df_stock.iterrows():
        qte = parse_float(row["Quantité"], 0.0)
        seuil = parse_float(row["Seuil Alerte"], 0.0)
        if qte <= seuil:
            alertes_stock.append(f"{row['Intrant']} ({qte} {row['Unité']})")

    if alertes_stock:
        col_a3.error("⛽ Alerte stock bas : " + ", ".join(alertes_stock))
    else:
        col_a3.success("✅ Stocks conformes : tous les intrants sont au dessus du seuil.")

    with st.expander("⚙️ Régler les seuils d'alerte"):
        with st.form("form_update_seuils"):
            st.write("Seuils de production (Sokodé) :")
            c_p1, c_p2 = st.columns(2)
            new_obj_ponte = c_p1.number_input("Objectif taux de ponte (%)", min_value=0.0, max_value=100.0, value=float(objectif_ponte), step=1.0)
            new_seuil_mort = c_p2.number_input("Seuil alerte mortalité (sujets par relevé)", min_value=0, value=int(seuil_mortalite), step=1)

            st.write("Seuils critiques du magasin :")
            cols_seuil_stk = st.columns(len(df_stock))
            stock_seuils_maj = []
            for idx, row in df_stock.iterrows():
                with cols_seuil_stk[idx % len(cols_seuil_stk)]:
                    s_mod = st.number_input(
                        f"Seuil {row['Intrant']} ({row['Unité']})",
                        min_value=0.0,
                        value=parse_float(row["Seuil Alerte"], 0.0),
                        step=0.5,
                        key=f"seuil_stk_{idx}"
                    )
                    stock_seuils_maj.append({
                        "Intrant": row["Intrant"],
                        "Quantité": parse_float(row["Quantité"], 0.0),
                        "Unité": row["Unité"],
                        "Seuil Alerte": s_mod
                    })

            if st.form_submit_button("💾 Enregistrer les seuils d'alerte"):
                st.session_state["objectif_ponte"] = new_obj_ponte
                st.session_state["seuil_mortalite"] = new_seuil_mort

                df_stock_seuils = pd.DataFrame(stock_seuils_maj)
                conn.update(worksheet="Stock", data=df_stock_seuils)

                df_params_nouveau = pd.DataFrame({
                    "Paramètre": ["Objectif_Ponte", "Seuil_Mortalite"],
                    "Valeur": [new_obj_ponte, new_seuil_mort]
                })
                try:
                    conn.update(worksheet="Parametres", data=df_params_nouveau)
                    st.cache_data.clear()
                    st.success("Seuils d'alerte mis à jour avec succès.")
                except Exception:
                    st.cache_data.clear()
                    st.warning("Seuils du magasin enregistrés. Créez l'onglet Parametres dans la base centrale pour sauvegarder durablement les seuils de ponte et de mortalité.")
                st.rerun()
    
    st.divider()
    
    # --- ETAT DU MAGASIN ---
    st.header("🏭 État du magasin et gestion des stocks")

    cols_met = st.columns(len(df_stock))
    for idx, row in df_stock.iterrows():
        with cols_met[idx % len(cols_met)]:
            qte_val = parse_float(row["Quantité"], 0.0)
            seuil_val = parse_float(row["Seuil Alerte"], 0.0)
            delta_val = "OK" if qte_val > seuil_val else "Critique"
            delta_col = "normal" if qte_val > seuil_val else "inverse"
            cols_met[idx % len(cols_met)].metric(row["Intrant"], f"{qte_val} {row['Unité']}", delta_val, delta_color=delta_col)

    with st.expander("⚙️ Modifier ou réapprovisionner le stock"):
        with st.form("form_update_stock"):
            st.write("Mettez à jour les quantités disponibles en stock :")
            updated_rows = []
            for idx, row in df_stock.iterrows():
                q_mod = st.number_input(f"Quantité pour {row['Intrant']} ({row['Unité']})", value=parse_float(row["Quantité"], 0.0), step=0.5, key=f"stk_{idx}")
                updated_rows.append({"Intrant": row["Intrant"], "Quantité": q_mod, "Unité": row["Unité"], "Seuil Alerte": parse_float(row["Seuil Alerte"], 0.0)})
            
            if st.form_submit_button("💾 Enregistrer les modifications du stock"):
                df_stock_nouveau = pd.DataFrame(updated_rows)
                conn.update(worksheet="Stock", data=df_stock_nouveau)
                st.cache_data.clear()
                st.success("Stocks mis à jour avec succès.")
                st.rerun()

    st.divider()

    # --- TABLEAU DE BORD FINANCIER ---
    st.header("📈 États financiers et suivi de trésorerie")

    if not df_creances.empty:
        df_fin = df_creances.copy()
        df_fin["_montant"] = df_fin["Montant Dû (FCFA)"].apply(lambda x: parse_float(x, 0.0))
        df_fin["_date"] = pd.to_datetime(df_fin["Date"], format="%d/%m/%Y", errors="coerce")
        df_fin["_statut_norm"] = df_fin["Statut"].astype(str).str.strip().str.lower()

        periode = st.radio(
            "Période d'analyse :",
            ["Tout l'historique", "Ce mois-ci", "Aujourd'hui"],
            horizontal=True
        )

        maintenant = datetime.now()
        if periode == "Aujourd'hui":
            df_fin_filtre = df_fin[df_fin["_date"].dt.date == maintenant.date()]
        elif periode == "Ce mois-ci":
            df_fin_filtre = df_fin[
                (df_fin["_date"].dt.year == maintenant.year) &
                (df_fin["_date"].dt.month == maintenant.month)
            ]
        else:
            df_fin_filtre = df_fin

        ca_total = df_fin_filtre["_montant"].sum()
        ca_encaisse = df_fin_filtre.loc[df_fin_filtre["_statut_norm"].str.contains("pay", na=False), "_montant"].sum()
        ca_retard = df_fin_filtre.loc[df_fin_filtre["_statut_norm"].str.contains("retard", na=False), "_montant"].sum()
        ca_creances = ca_total - ca_encaisse
        taux_recouvrement = (ca_encaisse / ca_total * 100) if ca_total > 0 else 0.0

        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Chiffre d'affaires facturé", format_fcfa(ca_total))
        f2.metric("Trésorerie encaissée", format_fcfa(ca_encaisse))
        delta_retard = f"Dont {format_fcfa(ca_retard)} en retard" if ca_retard > 0 else "Aucun retard"
        f3.metric("Créances clients", format_fcfa(ca_creances), delta_retard, delta_color="inverse" if ca_retard > 0 else "normal")
        f4.metric("Taux de recouvrement", f"{taux_recouvrement:.1f} %")

        if not df_fin_filtre.empty:
            col_v1, col_v2 = st.columns(2)

            with col_v1:
                st.subheader("Ventilation par client")
                df_par_client = (
                    df_fin_filtre.groupby("Client", as_index=False)
                    .agg(
                        CA_Total=("_montant", "sum"),
                        Encaisse=("_montant", lambda s: s[df_fin_filtre.loc[s.index, "_statut_norm"].str.contains("pay", na=False)].sum())
                    )
                )
                df_par_client["Reste à recouvrer"] = df_par_client["CA_Total"] - df_par_client["Encaisse"]
                df_par_client = df_par_client.sort_values("CA_Total", ascending=False)
                df_par_client = df_par_client.rename(columns={"CA_Total": "CA facturé (FCFA)", "Encaisse": "Encaissé (FCFA)"})
                st.dataframe(df_par_client, use_container_width=True, hide_index=True)

            with col_v2:
                st.subheader("Répartition par type de vente")
                df_par_type = (
                    df_fin_filtre.groupby("Type Vente", as_index=False)
                    .agg(CA=("_montant", "sum"))
                    .sort_values("CA", ascending=False)
                )
                df_par_type["Part (%)"] = df_par_type["CA"].apply(lambda x: f"{(x / ca_total * 100):.1f} %" if ca_total > 0 else "0.0 %")
                df_par_type = df_par_type.rename(columns={"CA": "Montant (FCFA)"})
                st.dataframe(df_par_type, use_container_width=True, hide_index=True)

            csv_fin = df_fin_filtre[cols_creances].to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📊 Exporter l'état financier pour Excel (CSV)",
                data=csv_fin,
                file_name=f"Etat_Financier_NGA_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info(f"Aucune opération financière enregistrée pour la période sélectionnée ({periode}).")
    else:
        st.info("Les indicateurs financiers s'afficheront ici dès la première vente enregistrée.")

    st.divider()
    
    # --- MODULE FINANCIER / CALCULATEUR DE VENTE ---
    st.header("💰 Module financier et ventes clients")
    type_client = st.radio("Grille tarifaire de référence :", ["Grossiste", "Détaillant"], horizontal=True)
    grille_active = prix_grossiste if type_client == "Grossiste" else prix_detaillant
    
    clients_disponibles = ["Client 01 AGROSATH", "Client 02 JOSUE", "Client 03 BOUTIQUE CENTRALE", "Client 04 MARCHE CENTRAL", "Client 05 PASSAGER 1", "Client 06 PASSAGER 2"]
    client_actif = st.selectbox("Sélectionner le client pour cette saisie de vente :", clients_disponibles)
    
    st.subheader(f"Plateaux vendus pour {client_actif} :")
    cols_vente = st.columns(6)
    ventes = {}
    
    for i, cal in enumerate(calibres):
        with cols_vente[i]:
            ventes[cal] = st.number_input(f"{cal}", value=0, min_value=0, step=5, key=f"v_{cal}")
            st.caption(f"{grille_active[cal]} F/pl")
            
    ca_client = sum(ventes[cal] * grille_active[cal] for cal in calibres)
    st.markdown(f"<h3 style='color: #4CAF50;'>Chiffre d'affaires pour {client_actif} : {format_fcfa(ca_client)}</h3>", unsafe_allow_html=True)
    
    st.divider()
    
    # --- GEST
