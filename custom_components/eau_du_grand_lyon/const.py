DOMAIN = "eau_du_grand_lyon"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_CONTRAT_ID = "contrat_id"

DEFAULT_CONTRAT_ID = ""

# Pour login OAuth2
CONF_CLIENT_ID = "client_id"
DEFAULT_CLIENT_ID = "kwnOk0B_aqlOI6p_GVxrbf6"

BASE_URL = "https://agence.eaudugrandlyon.com"

# APIs conso
REST_MENSUEL = "/application/rest/produits/contrats/{contrat_id}/consommationsMensuelles"
REST_JOURNALIER = "/application/rest/produits/contrats/{contrat_id}/consommationsJournalieres"

# Fenêtre d'historique journalier demandée à l'API
DEFAULT_DAYS_BACK = 370

# OAuth endpoints
AUTH_AUTHENTIFICATION = "/application/auth/externe/authentification"
AUTH_AUTHORIZE = "/application/auth/authorize-internet"
AUTH_TOKEN = "/application/auth/tokenUtilisateurInternet"
REDIRECT_URI = "https://agence.eaudugrandlyon.com/autorisation-callback.html"
