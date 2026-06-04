# Cloud Toolbox — Overview du projet

> Document de référence pour reprendre le projet.
> À jour après la migration du front vers Django templates.

---

## 1. Vision

**Cloud Toolbox** est un portail web d'outils d'infrastructure cloud : propre,
moderne, performant. Le backend est maintenant en **Django** et les pages sont
rendues avec les templates Django classiques. Le JavaScript restant sert
uniquement aux interactions locales simples.

Quatre outils sont livrés pour le moment, tous rangés dans
**Block Storage Tools** :

- **Gestionnaire de Volumes**, qui simule OpenStack Cinder côté volumes.
- **Gestionnaire de Quotas**, qui simule l'analyse et l'application de quotas
  Cinder par projet.
- **Recherche Account**, qui récupère les détails d'un account depuis un Project
  ID en réutilisant la logique de l'API account externe mockée.
- **Recherche WWN**, qui retrouve les volumes correspondant à un ou plusieurs WWN.

Le dashboard est organisé en familles pour préparer l'ajout d'une dizaine
d'outils :

- **Block Storage Tools**;
- **Object Storage Tools**;
- **Common Tools**.

Les données restent locales et déterministes : aucune API OpenStack réelle n'est
appelée pour l'instant.

Objectif à terme : ajouter d'autres outils (snapshots, instances, réseaux...) en
suivant le même patron Python + template.

---

## 2. Contraintes

- Pas de npm, pas de bundler, pas d'étape de build.
- Pas d'ES modules côté navigateur.
- Django sert les pages via `python manage.py runserver`.
- Les assets front sont des fichiers statiques classiques dans
  `static/cloud_toolbox/`.
- Le code doit rester très lisible pour pouvoir servir de référence pédagogique.

---

## 3. Ce qui est fait

### Socle Django

- Django 5 minimal.
- Routes principales :
  - `/` → dashboard.
  - `/tools/volumes/` → gestionnaire de volumes.
  - `/tools/quotas/` → gestionnaire de quotas.
  - `/tools/accounts/` → recherche account par Project ID.
  - `/tools/wwn/` → recherche volumes par WWN.
- Templates séparés :
  - `templates/portal/base.html`
  - `templates/portal/dashboard.html`
  - `templates/portal/volumes.html`
  - `templates/portal/quotas.html`
  - `templates/portal/accounts.html`
  - `templates/portal/wwn_lookup.html`
  - `templates/portal/partials/status_badge.html`
- Helpers template dans `portal/templatetags/ui.py`.
- Sessions Django en cookies signés pour mémoriser les volumes supprimés/reset.
- Régions OpenStack configurées dans `cloud_toolbox/settings.py` via
  `OPENSTACK_REGIONS`.
- Versions OpenStack configurées dans `cloud_toolbox/settings.py` via
  `OPENSTACK_VERSIONS`.
- Base locale `db.sqlite3` générée par `python manage.py migrate`; elle ne doit
  pas être commitée.

### Gestionnaire de volumes

- Recherche par région + IDs de volumes.
- Choix de la plateforme OpenStack (`v1` ou `v2`) dans le formulaire de
  recherche.
- Parsing Python des IDs séparés par virgules, espaces ou retours ligne.
- Déduplication en conservant l'ordre de saisie.
- Génération déterministe des volumes simulés dans `portal/services/cinder.py`.
- Filtres de statut rendus côté serveur avec liens GET.
- Tableau avec sélection, détails, badges de statut et actions.
- Détail "openstack volume show" rendu côté serveur.
- Le champ `os-vol-tenant-attr:tenant_id` est cliquable : il appelle
  `/api/accounts/<project_id>/` et affiche les champs utiles de l'account dans
  une popup.
- Reset vers `available` via POST.
- Suppression via POST avec confirmation navigateur.
- Actions par lots via formulaire POST.

### Gestionnaire de quotas

- Workflow en deux temps :
  1. l'utilisateur donne la version OpenStack, le project ID UUID et la région;
  2. le backend récupère le quota courant simulé;
  3. après lecture du quota actuel, l'opérateur décide ou non d'appliquer une
     augmentation.
- Validation Python du project ID et des nombres.
- Génération déterministe du quota courant.
- Quotas séparés par version OpenStack et région.
- Affichage des limites courantes.
- Blocage si la demande n'est pas une augmentation.
- Affichage des commandes simulées :
  `openstack quota show <project_id>`.
  `openstack quota set --volumes ... --gigabytes ... <project_id>`.
- Application simulée via POST, persistée dans la session Django.

### Recherche Account

- Formulaire Project ID.
- Validation UUID côté backend.
- Affichage des mêmes champs que l'API `/api/accounts/<project_id>/` :
  project name, domain, project id.
- Données mockées mais déterministes.

### Recherche WWN

- Recherche par un ou plusieurs WWN, séparés par virgules, espaces ou retours
  ligne.
- Déduplication des WWN en conservant l'ordre de saisie.
- Génération déterministe des volumes correspondants.
- Tableau avec WWN, volume id, région, backend, taille, statut et tenant.
- Le tenant reste cliquable et ouvre la popup account.

### JavaScript restant

`static/cloud_toolbox/js/app.js` gère seulement :

- injection des icônes SVG depuis `icons.js`;
- auto-resize du textarea;
- bouton Exemple;
- ouverture/fermeture des détails;
- appel `fetch()` vers l'API account externe mockée quand on clique un tenant id;
- sélection par lots;
- confirmations de suppression;
- disparition automatique des toasts.

---

## 4. Décisions prises

- Vue a été retiré pour passer sur du Django templates pur.
- Le front n'est plus un SPA hash-routing : les pages sont de vraies routes
  Django.
- La logique métier simulée Cinder vit en Python dans `portal/services/cinder.py`.
- Le JavaScript ne porte plus de logique métier.
- Suppression possible uniquement depuis `available`; les autres états passent
  d'abord par Reset.
- Bouton Reset = texte; bouton Supprimer = icône corbeille rouge.

---

## 5. Roadmap

- [ ] Ajouter d'autres outils sur le même patron :
  - snapshots;
  - instances;
  - réseaux.
- [ ] Créer un README / CONTRIBUTING pour expliquer le patron.
- [ ] Ajouter une vraie couche API quand les actions devront être dynamiques sans
  rechargement de page.
- [ ] Pagination du tableau.
- [ ] Tri des colonnes, export CSV, thème sombre, tests.
- [ ] Remplacer la simulation locale par des appels OpenStack réels quand le
  cadre d'exécution sera défini.

---

## 6. Passage aux appels OpenStack réels

Quand les mocks seront remplacés par de vrais appels OpenStack, supprimer la
mémoire de session qui simule les actions et remplacer les générateurs
déterministes par des clients réels.

### Volumes

Dans `portal/views.py`, supprimer :

- `session_set`;
- `mark_deleted`;
- `mark_reset`;
- les lectures `deleted_keys=session_set(...)` et `reset_keys=session_set(...)`;
- les écritures `request.session["deleted_volumes"]` et
  `request.session["reset_volumes"]`.

Dans `portal/services/cinder.py`, remplacer :

- `build_volumes(...)` par un appel réel de listing/recherche volumes;
- `build_volume(...)` par un appel réel à l'API volume show si nécessaire;
- `reset_volume(...)` par une vraie action OpenStack;
- la génération déterministe par `random`, `seed_for`, `random_uuid`,
  `random_hex`, etc.

Le futur service devrait exposer des fonctions proches de :

```python
list_volumes(openstack_version, region, ids)
delete_volume(openstack_version, region, volume_id)
reset_volume_status(openstack_version, region, volume_id, status)
```

La vue pourra rester proche de l'existant : elle appellera le service réel, puis
redirigera vers la recherche. Si OpenStack supprime vraiment un volume, il ne
sera plus retourné au prochain listing.

### Quotas

Dans `portal/views.py`, supprimer :

- `quota_overrides`;
- les lectures/écritures `request.session["quota_overrides"]`.

Dans `portal/services/quotas.py`, remplacer :

- `build_quota(...)` par un appel réel de récupération quota;
- `apply_request(...)` par un appel réel de modification quota;
- la génération déterministe par `random` et `seed_for`.

Le futur service devrait exposer des fonctions proches de :

```python
get_quota(openstack_version, region, project_id)
set_quota(openstack_version, region, project_id, volumes, gigabytes)
```

### Accounts

Dans `portal/services/accounts.py`, remplacer `fetch_external_account(...)` par
l'appel réel à l'API account externe. Le contrat attendu par le front reste :

```python
{
    "project_name": "...",
    "domain": "...",
    "project_id": "...",
}
```

### WWN

Dans `portal/services/wwn.py`, remplacer la génération déterministe par l'appel
réel qui retrouve les volumes à partir des WWN. La vue peut continuer à recevoir
une liste de résultats contenant le WWN, le volume, le backend, le pool et le
chemin hôte si ces informations existent dans la source réelle.

---

## 7. Architecture

```text
manage.py
requirements.txt

cloud_toolbox/
  settings.py
  urls.py
  wsgi.py

portal/
  views.py
  services/
    accounts.py
    cinder.py
    quotas.py
    wwn.py
  templatetags/
    ui.py

templates/
  portal/
    base.html
    dashboard.html
    volumes.html
    partials/
      status_badge.html

static/
  cloud_toolbox/
    css/
      tokens.css
      base.css
      components.css
      pages.css
    js/
      icons.js
      app.js
```

### API mockées

- `GET /api/accounts/<project_id>/`
  - Valide que `project_id` est un UUID.
  - Représente l'appel à l'API account externe.
  - Retourne uniquement les champs utilisés par l'application :
    `project_name`, `domain`, `project_id`.

---

## 8. Patron pour ajouter un outil

1. Ajouter la logique métier dans `portal/services/<outil>.py`.
2. Ajouter une vue Django dans `portal/views.py` ou un module de vues dédié.
3. Ajouter la route dans `cloud_toolbox/urls.py`.
4. Créer le template dans `templates/portal/<outil>.html`.
5. Ajouter la tuile dans le bon groupe de `TOOL_GROUPS` dans `portal/views.py`.
6. Ajouter seulement le JS strictement nécessaire dans `static/cloud_toolbox/js/app.js`
   ou dans un fichier dédié si l'outil devient conséquent.

---

## 9. Lancer et tester

```powershell
python -m pip install -r requirements.txt
python manage.py runserver 5180
```

Puis ouvrir : http://localhost:5180

Après chaque modification :

- lancer `python manage.py check`;
- vérifier la page dans le navigateur;
- vérifier qu'il n'y a aucune erreur console.
