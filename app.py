import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="AgroGestion Togo - Pilote", layout="wide", page_icon="🐓")

# --- SYSTEME DE CONNEXION ---
if "authentifie" not in st.session_state:
    st.session_state["authentifie"] = False

if not st.session_state["authentifie"]:
    st.title("🔒 Accès Sécurisé - AgroGestion")
    st.write("Veuillez vous connecter pour accéder au tableau de bord.")
    
    identifiant = st.text_input("Identifiant")
    mot_de_passe = st.text_input("Mot de passe", type="password")
    
    if st.button("Se connecter"):
        # Remplacer par les identifiants souhaités
        if identifiant == "Direction" and mot_de_passe == "Togo2026!":
            st.session_state["authentifie"] = True
            st.rerun() # Rafraîchit la page pour enlever le formulaire
        else:
            st.error("Identifiant ou mot de passe incorrect.")
    
    st.stop() # Empêche le reste du code de s'exécuter si non connecté

# --- 2. DONNÉES RÉELLES (Issues de la Fiche de Collecte V2) ---
# Ratios de consommation (kg/jour/sujet)
ratios = {
    "Poussin (Démarrage)": 0.033,  # 33g
    "Poulette (Croissance)": 0.050, # 50g
    "Pré-Ponte (Transition)": 0.105, # 105g
    "Ponte (Production)": 0.115     # 115g
}

# Durées des phases (en jours)
durees = {
    "Poussin (Démarrage)": 56,      # 8 semaines
    "Poulette (Croissance)": 75,    # 2.5 mois
    "Pré-Ponte (Transition)": 14,   # 2 semaines
    "Ponte (Production)": 435       # 14.5 mois
}

# Objectifs de ponte par race
objectifs_ponte = {
    "Leghons": 80,
    "Isa Brown": 78
}

# Tarifs moyens (FCFA)
tarifs = {
    "Plateau - Grossiste": 2067,
    "Plateau - Détaillant": 2142,
    "Poule Réforme": 2750 # Moyenne de 2500-3000
}

# --- 3. DONNÉES SIMULÉES (En attente des vrais paramètres) ---
seuil_securite_kg = 2000 # Test : Alerte rouge à 2 Tonnes
# Simulation d'une formule pour l'aliment ponte
formule_test = {"Maïs": 0.60, "Tourteaux de soja": 0.25, "Concentré ponte": 0.15}

# --- 4. BARRE LATÉRALE ---
st.sidebar.title("🚜 Menu de Gestion")
st.sidebar.info("Conseiller : Londres 🇬🇧")
race_choisie = st.sidebar.selectbox("Race de la bande", list(objectifs_ponte.keys()))
date_arrivee = st.sidebar.date_input("Date d'arrivée des poussins", datetime.now())
st.sidebar.divider()
st.sidebar.warning("Statut : Pilote V1 (Données Mixtes)")

# --- 5. EN-TÊTE ---
st.title("🌾 Complexe Agroalimentaire - Pilote V1")
st.markdown(f"### Suivi d'exploitation - Objectif cible ({race_choisie}) : {objectifs_ponte[race_choisie]}%")
st.divider()

# --- 6. MODULE STOCKS & ALIMENTATION ---
st.header("📦 État des Stocks & Alertes (Global)")
col1, col2, col3 = st.columns(3)

with col1:
    nb_sujets = st.number_input("Effectif de la bande", value=10000, step=500)
with col2:
    phase_actuelle = st.selectbox("Phase actuelle", list(ratios.keys()))
with col3:
    stock_kg = st.number_input("Stock d'aliment restant (kg)", value=5000)

conso_jour = nb_sujets * ratios[phase_actuelle]
autonomie = stock_kg / conso_jour if conso_jour > 0 else 0

m1, m2, m3 = st.columns(3)
if stock_kg <= seuil_securite_kg:
    m1.error(f"🚨 ALERTE ROUGE : Stock sous le seuil critique ({seuil_securite_kg} kg) !")
elif autonomie < 5:
    m1.warning(f"⚠️ Attention : {autonomie:.1f} jours d'autonomie")
else:
    m1.success(f"✅ Autonomie confortable : {autonomie:.1f} jours")

m2.metric("Besoin quotidien", f"{conso_jour:.1f} kg")
m3.metric("Besoin hebdo (7j)", f"{conso_jour * 7:.1f} kg")

# Simulation de l'impact sur les ingrédients
st.caption("🔍 *Simulation d'impact sur ingrédients (Basé sur une recette test)*")
c_mais, c_soja, c_conc = st.columns(3)
c_mais.write(f"- **Maïs (60%)** : {conso_jour * 0.60:.1f} kg/jour")
c_soja.write(f"- **Tourteaux de soja (25%)** : {conso_jour * 0.25:.1f} kg/jour")
c_conc.write(f"- **Concentré (15%)** : {conso_jour * 0.15:.1f} kg/jour")

st.divider()

# --- 7. MODULE CALENDRIER PRÉVISIONNEL ---
st.header("📅 Calendrier Prévisionnel du Lot")
date_fin_poussin = date_arrivee + timedelta(days=durees["Poussin (Démarrage)"])
date_debut_preponte = date_fin_poussin + timedelta(days=durees["Poulette (Croissance)"])
date_debut_ponte = date_debut_preponte + timedelta(days=durees["Pré-Ponte (Transition)"])
date_reforme = date_debut_ponte + timedelta(days=durees["Ponte (Production)"])

c1, c2, c3 = st.columns(3)
c1.info(f"**Fin phase Poussin :** \n\n {date_fin_poussin.strftime('%d/%m/%Y')}")
c2.warning(f"**Début Pré-Ponte :** \n\n {date_debut_preponte.strftime('%d/%m/%Y')}")
c3.error(f"**Date de Réforme prévue :** \n\n {date_reforme.strftime('%d/%m/%Y')}")

st.divider()

# --- 8. MODULE FINANCE (GRM) & VENTES ---
st.header("💰 Simulateur de Revenus & Carnet de Créances")

col_v1, col_v2 = st.columns(2)
with col_v1:
    type_vente = st.radio("Type de tarification applicable", ["Grossiste (2067 FCFA/pl)", "Détaillant (2142 FCFA/pl)"])
    prix_actuel = tarifs["Plateau - Grossiste"] if "Grossiste" in type_vente else tarifs["Plateau - Détaillant"]
with col_v2:
    plateaux_vendus = st.number_input("Nombre de plateaux vendus (Simulation)", value=100)
    revenu_jour = plateaux_vendus * prix_actuel
    st.metric("Chiffre d'Affaires Brut Estimé", f"{revenu_jour:,.0f} FCFA".replace(",", " "))

st.subheader("Suivi des clients débiteurs (GRM)")
data_finance = {
    "Client": ["AGROSATH", "JOSUE", "Client Passager"],
    "Type Vente": ["Œufs (Grossiste)", "Œufs (Détaillant)", "Poules Réforme"],
    "Montant Dû (FCFA)": [350000, 125000, 0],
    "Statut": ["En attente", "Retard", "Payé Cash"]
}
df_fin = pd.DataFrame(data_finance)
st.table(df_fin)

csv = df_fin.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Exporter le carnet de créances (CSV)",
    data=csv,
    file_name='creances_clients_togo.csv',
    mime='text/csv',
)
