# MAS Internal Ticketing

Application web interne de gestion des demandes et incidents informatiques, conçue pour centraliser le cycle de vie des tickets, leur affectation, le suivi des SLA et la communication avec les utilisateurs.

> **Dépôt privé — projet professionnel MAS Group.** Le code, la documentation et les éléments métier de ce dépôt sont confidentiels. Les secrets, fichiers `.env`, certificats, sauvegardes et données de production sont exclus du versionnement.

## Présentation

La plateforme fournit un point d’entrée unique aux collaborateurs et à l’équipe informatique. Elle couvre la création d’une demande, sa qualification, son affectation, son traitement et sa clôture, avec traçabilité des actions et indicateurs de pilotage.

### Fonctionnalités principales

- authentification d’entreprise via LDAP, avec mécanisme local de secours configurable ;
- gestion des rôles `USER`, `IT_AGENT` et `ADMIN` ;
- création, consultation, affectation et suivi des tickets ;
- priorités, catégories, départements, commentaires et pièces jointes ;
- workflow contrôlé : `NEW`, `IN_PROGRESS`, `ON_HOLD`, `RESOLVED`, `CLOSED` ;
- tableaux de bord, suivi des SLA, performance par département et export CSV ;
- notifications par e-mail via Zimbra SMTP, traitées par un worker avec reprise sur erreur ;
- administration des utilisateurs et journalisation des actions sensibles.

## Architecture et technologies

| Couche | Technologies |
| --- | --- |
| Interface | React 18, TypeScript, Vite, React Router, TanStack Query |
| Validation et formulaires | React Hook Form, Zod |
| API | Python, FastAPI, Pydantic |
| Données | SQLAlchemy, Alembic, Microsoft SQL Server, pyodbc |
| Identité | LDAP, JWT, contrôle d’accès par rôle |
| Notifications | Zimbra SMTP, worker avec file de traitement |
| Déploiement | Nginx, systemd |
| Qualité | Pytest, compilation TypeScript, build Vite |

```text
Navigateur React
      │
      ▼
API REST FastAPI ───── LDAP
      │                 │
      ├──── SQL Server  └──── Identité d'entreprise
      │
      └──── Worker de notifications ──── Zimbra SMTP
```

## Structure du projet

```text
ticketing application/
├── backend/                 # API, modèles, migrations et worker
│   ├── alembic/             # Migrations de la base de données
│   ├── app/                 # Logique applicative FastAPI
│   ├── deploy/              # Services systemd et configuration Nginx
│   ├── sql/                 # Scripts SQL nécessaires au projet
│   └── tests/               # Tests automatisés
├── frontend/                # Application React/TypeScript
│   └── src/                 # Pages, composants, API et état applicatif
└── README.md
```

## Installation locale

### Prérequis

- Python 3.11 ou version compatible ;
- Node.js 20+ et npm ;
- Microsoft SQL Server et un pilote ODBC compatible ;
- accès à un annuaire LDAP et à un serveur SMTP pour tester les intégrations.

### Backend

```powershell
cd backend
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Dans un second terminal, lancer le traitement des notifications :

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.workers.notification_worker
```

### Frontend

```powershell
cd frontend
Copy-Item .env.example .env
npm ci
npm run dev
```

L’interface de développement est accessible à l’adresse affichée par Vite. L’URL de l’API se configure avec `VITE_API_BASE_URL`.

## Configuration

Les fichiers `.env.example` documentent les variables attendues sans contenir de secret réel. Les principaux groupes de paramètres concernent :

- la connexion SQL Server ;
- les clés et durées de validité JWT ;
- l’annuaire LDAP ;
- le serveur Zimbra SMTP ;
- les origines CORS ;
- les règles de notification et de clôture des tickets.

Ne jamais committer un fichier `.env` réel. Toute clé exposée doit être révoquée et remplacée.

## API

Les routes sont regroupées sous `/api/v1` :

- `/auth` : connexion, renouvellement de session et profil courant ;
- `/tickets` : cycle de vie des tickets, commentaires et pièces jointes ;
- `/reports` : indicateurs, SLA, performance et exports ;
- `/departments`, `/ticket-categories`, `/priorities` : référentiels ;
- `/users`, `/audit-logs`, `/admin/notifications` : administration et supervision.

La documentation interactive de FastAPI est disponible en environnement autorisé via `/docs`.

## Vérifications de qualité

```powershell
# Backend
cd backend
python -m compileall app
pytest -q

# Frontend
cd ..\frontend
npm run build
```

## Déploiement

Le dossier `backend/deploy` contient les modèles nécessaires au déploiement sous Linux : service API, service et timer du worker de notifications, ainsi que la configuration Nginx. Les secrets de production doivent être injectés par l’environnement du serveur et ne doivent jamais être stockés dans Git.

## Compétences démontrées

- conception d’une application métier full-stack et d’une API REST structurée ;
- intégration de services d’entreprise : SQL Server, LDAP et SMTP ;
- modélisation d’un workflow, gestion des rôles et traçabilité ;
- migrations de base de données, reporting et traitement différé ;
- préparation au déploiement avec Nginx et systemd ;
- pratiques de sécurité autour des secrets et des données internes.

## Confidentialité

Ce dépôt est destiné uniquement à une consultation privée et autorisée. Toute réutilisation, diffusion ou publication du code et des informations internes de MAS Group nécessite une autorisation préalable.
