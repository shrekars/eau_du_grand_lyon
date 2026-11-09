# Eau du Grand Lyon - Intégration Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![Validate with hassfest](https://github.com/home-assistant/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/home-assistant/actions/workflows/hassfest.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Intégration Home Assistant personnalisée permettant de récupérer automatiquement vos consommations d'eau quotidiennes et mensuelles depuis l'espace client en ligne **[Eau du Grand Lyon](https://agence.eaudugrandlyon.com)** (Métropole de Lyon / Veolia).

L'intégration injecte nativement les données historiques dans le **tableau de bord Énergie (Energy Dashboard)** de Home Assistant sans décalage et sans pic artificiel.

---

## ✨ Fonctionnalités

* 💧 **Intégration native au tableau de bord Énergie** : injection via les statistiques à long terme (`async_add_external_statistics`), rattachées rigoureusement à chaque jour de consommation réel.
* 🔐 **Authentification sécurisée & robuste** : support de l'authentification OAuth2 PKCE avec mise en cache locale du jeton (`Store`) pour éviter tout dépassement du quota de connexions simultanées du serveur.
* 🔄 **Découverte dynamique du contrat** : l'identifiant chiffré du contrat est automatiquement détecté au fil des sessions, aucune configuration manuelle complexe n'est requise.
* 🚨 **Détection de fuites** : exposition des attributs `debit_min` (débit nocturne) et `volume_estime_fuite` fournis par la télé-relève Téléo.
* 📊 **Suivi mensuel & historique** : capteurs de consommation mensuelle M-0 à M-11 et attribut `history_12_months` directement utilisable dans vos cartes Lovelace.

---

## 📦 Installation via HACS

1. Ouvrez **HACS** dans votre instance Home Assistant.
2. Cliquez sur les **3 petits points** en haut à droite > **Dépôts personnalisés** (*Custom repositories*).
3. Ajoutez l'URL de votre dépôt GitHub avec la catégorie **Intégration**.
4. Recherchez **Eau du Grand Lyon** et cliquez sur **Télécharger**.
5. Redémarrez Home Assistant.

---

## ⚙️ Configuration

1. Rendez-vous dans **Paramètres > Appareils et services > Ajouter une intégration**.
2. Recherchez **Eau du Grand Lyon**.
3. Renseignez simplement :
   * **Adresse email** de votre compte en ligne
   * **Mot de passe**
4. Validez : l'intégration se connecte, détecte votre contrat actif et crée l'appareil ainsi que ses 16 capteurs.

---

## 🚰 Intégration dans le Tableau de Bord Énergie

1. Allez dans **Paramètres > Tableaux de bord > Énergie**.
2. Dans la section **Consommation d'eau**, cliquez sur **Ajouter une source d'eau**.
3. Deux options s'offrent à vous :
   * **Recommandé (Précision historique)** : Sélectionnez la statistique externe **Eau du Grand Lyon (Consommation)** (`eau_du_grand_lyon:water_consumption`). Les données télérelevées passées (J-1 / J-2) sont injectées rétroactivement à leur date et heure exactes, évitant tout décalage temporel ou pic artificiel le lundi.
   * **Alternative (Entité d'index direct)** : Sélectionnez le capteur **Eau (index)** (`sensor.eau_index`).
4. Définissez le coût de l'eau :
   * **3,44 € / m³** : coût réel de chaque m³ consommé (Tranche 2 en vigueur).
   * ou **3,65 € / m³** : coût moyen incluant l'amortissement de l'abonnement annuel fixe.
5. Enregistrez. L'historique sera visible pour chaque journée télé-relevée.

---

## 📱 Entités créées

Toutes les entités sont automatiquement regroupées sous l'appareil **Eau du Grand Lyon (Compteur Téléo)** :

| Entité | Nom | Description |
|---|---|---|
| `sensor.eau_index` | Eau (index) | Index relevé du compteur (en Litres, `total_increasing`) |
| `sensor.eau_dernier_jour` | Eau (dernier jour) | Volume en litres du dernier jour télé-relevé (avec date, débit min et fuite) |
| `sensor.eau_date_du_dernier_releve` | Eau (date du dernier relevé) | Date calendaire du dernier télérelevé disponible (`device_class: date`) |
| `sensor.eau_annee_en_cours` | Eau (année en cours) | Cumul des consommations de l'année civile en cours en m³ |
| `binary_sensor.eau_alerte_fuite` | Eau (alerte fuite) | Alerte binaire immédiate si une fuite d'eau est suspectée par Téléo (`device_class: problem`) |
| `sensor.eau_total` | Eau (total) | Cumul total des consommations en m³ (avec attribut `history_12_months`) |
| `sensor.conso_mois_dernier` | Conso mois dernier | Volume consommé le mois précédent en m³ |
| `sensor.conso_m_0` à `sensor.conso_m_11` | Conso M-0 à M-11 | Consommations mensuelles sur les 12 derniers mois glissants |

---

## 🎨 Exemple de carte Lovelace (Historique 12 mois)

```yaml
type: markdown
title: Consommation des 12 derniers mois
content: >-
  {% set history = state_attr('sensor.eau_total', 'history_12_months') | default([], true) %}
  {% if history %}
    {% for item in history %}
  - **{{ item.label }}** : {{ item.conso_m3 }} m³ *(~{{ (item.conso_m3 * 3.44) | round(2) }} €)*
    {% endfor %}
  {% else %}
  *Synchronisation en cours...*
  {% endif %}
```

---

## 🛡️ Sécurité & Confidentialité

* Vos identifiants ne sont jamais transmis à des tiers et transitent exclusivement entre votre Home Assistant et les serveurs officiels d'Eau du Grand Lyon.
* Les jetons d'authentification sont stockés localement dans le stockage protégé de Home Assistant (`.storage`).
* Aucun mot de passe ou jeton sensible n'apparaît dans les journaux d'erreurs.

---

## 📄 Licence

Ce projet est sous licence [MIT](LICENSE).
Ce composant est un projet communautaire open source indépendant et n'est ni affilié ni sponsorisé par la Métropole de Lyon ou la société Veolia.

