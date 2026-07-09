# Cloud Toolbox - Project Overview

Document de reprise rapide pour humain ou agent IA.

Le projet doit rester simple, explicite et lisible. La priorité est le style
PEP20 côté backend, et son équivalent côté front : peu de magie, noms clairs,
responsabilités séparées, pas de code décoratif inutile.

---

## 1. Etat Actuel

Cloud Toolbox est un portail Django pour des outils d'infrastructure cloud.
Le front est rendu avec des templates Django classiques. Le JavaScript ne gère
que les interactions locales simples.

Il n'y a pas encore d'appel réel OpenStack. Les données sont mockées de manière
déterministe dans les services Python.

Familles d'outils du dashboard :

- `Block Storage Tools`
- `Object Storage Tools`
- `Common Tools`

Outils existants dans `Block Storage Tools` :

- `Gestionnaire de Volumes`
- `Gestionnaire de Quotas`
- `Recherche Account`
- `Recherche WWN`

Outils existants dans `Object Storage Tools` :

- `Bucket IAM Policies`

Outils existants dans `Common Tools` :

- `Détails Account IAM`

Routes principales :

```text
/                       Dashboard
/login/                 Login Django
/logout/                Logout Django
/tools/volumes/         Recherche et actions volumes
/tools/quotas/          Recherche et application quotas
/tools/accounts/        Recherche account par Project ID
/tools/account-details/ Détails account et policies IAM appliquées
/tools/bucket-policies/ Recherche policies IAM par bucket Object Storage
/tools/wwn/             Recherche volumes par WWN
/api/accounts/<uuid>/   API account mockée, utilisée par la popup
```

---

## 2. Lancer Le Projet

Installation :

```powershell
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 5180
```

Créer un compte admin local de dev :

```powershell
python manage.py createsuperuser
```

Ou recréer le compte de test local :

```powershell
python manage.py shell --command "from django.contrib.auth.models import User; u, _ = User.objects.get_or_create(username='admin'); u.set_password('admin'); u.is_staff=True; u.is_superuser=True; u.save()"
```

Identifiants de dev si le compte ci-dessus existe :

```text
admin / admin
```

Validation rapide :

```powershell
python manage.py check
```

La base `db.sqlite3` est locale et ignorée par Git. Elle est créée par
`python manage.py migrate`.

---

## 3. Configuration

Les variables d'environnement sont lues dans `cloud_toolbox/settings.py`.

```text
OPENSTACK_REGIONS          ex: us-east-1,us-west-2,eu-west-1
OPENSTACK_VERSIONS         ex: v1,v2
OBJECT_STORAGE_RINGS       ex: OBJRNGPARMARTIG01,OBJRNGPARMAR01
LDAP_DOMAIN                ex: INTERNAL
LDAP_AUTHORIZED_GROUPS     ex: cloud-toolbox-users,cloud-toolbox-admins
```

Exemple PowerShell :

```powershell
$env:OPENSTACK_REGIONS="us-east-1,us-west-2"
$env:OPENSTACK_VERSIONS="v1,v2"
$env:OBJECT_STORAGE_RINGS="OBJRNGPARMARTIG01,OBJRNGPARMAR01"
$env:LDAP_DOMAIN="INTERNAL"
$env:LDAP_AUTHORIZED_GROUPS="cloud-toolbox-users,cloud-toolbox-admins"
```

Les listes de valeurs sont des chaînes séparées par des virgules. La forme
attendue est :

```text
v1,v2
```

---

## 4. Architecture

```text
manage.py
requirements.txt
OVERVIEW.md

cloud_toolbox/
  settings.py
  urls.py
  wsgi.py

portal/
  views.py
  authentication.py
  mock_state.py
  presenters.py
  quota_forms.py
  tool_catalog.py
  view_helpers.py
  services/
    accounts.py
    cinder.py
    ldap_auth.py
    object_storage.py
    quotas.py
    wwn.py
  templatetags/
    ui.py

templates/
  portal/
    base.html
    dashboard.html
    login.html
    volumes.html
    quotas.html
    accounts.html
    account_details.html
    bucket_policies.html
    wwn_lookup.html
    partials/
      status_badge.html

static/
  cloud_toolbox/
    css/
      tokens.css
      base.css
      components.css
      pages.css
      account_details.css
      bucket_policies.css
    js/
      accounts.js
      account_details.js
      bucket_policies.js
      common.js
      icons.js
      quotas.js
      volumes.js
```

Responsabilités :

- `cloud_toolbox/settings.py` : configuration Django, régions, versions
  OpenStack, auth.
- `cloud_toolbox/urls.py` : routes.
- `portal/views.py` : vues Django, orchestration formulaire/service/template.
- `portal/mock_state.py` : état de session utilisé seulement par les mocks.
- `portal/presenters.py` : données préparées pour les templates.
- `portal/quota_forms.py` : lecture et validation légère des champs quota.
- `portal/tool_catalog.py` : groupes et tuiles visibles sur l'accueil.
- `portal/view_helpers.py` : helpers courts pour settings, sélection et session.
- `portal/services/*.py` : logique métier et mocks backend.
- `templates/portal/*.html` : rendu HTML Django.
- `static/cloud_toolbox/css/*.css` : design system et pages.
- `static/cloud_toolbox/icons/*.svg` : icônes SVG statiques.
- `static/cloud_toolbox/js/icons.js` : charge les SVG depuis le dossier `icons`.
- `static/cloud_toolbox/js/common.js` : comportements communs simples.
- `static/cloud_toolbox/js/accounts.js` : popup et API account.
- `static/cloud_toolbox/js/account_details.js` : exemple, dépliage et copie JSON
  des policies IAM d'un account.
- `static/cloud_toolbox/js/bucket_policies.js` : exemple, dépliage et copie JSON
  des policies IAM.
- `static/cloud_toolbox/js/volumes.js` : filtres, détails et actions volumes.
- `static/cloud_toolbox/js/quotas.js` : comportements du formulaire quotas.

---

## 5. Règles De Code

Backend :

- Appliquer PEP20 : explicite, simple, lisible.
- Ne pas générer de HTML dans les services Python.
- Ne pas mettre de texte UI dans les services si la vue/template peut le faire.
- Ne pas ajouter de micro-abstractions inutiles.
- Les services retournent des objets/dicts de données, pas du rendu.
- Les vues préparent le contexte template.
- Les templates affichent.
- Le JavaScript ne porte pas la logique métier.

Front :

- Interface utilitaire, dense mais lisible.
- Pas de landing page décorative.
- Pas de cartes imbriquées.
- Contrôles standards : toggles, selects, buttons, tables.
- Les boutons et labels doivent être lisibles sur mobile et desktop.
- Les toggles `v1/v2` sont des radios accessibles stylées en segmented control.
- Eviter les effets gratuits. Garder les états utiles : hover, focus, selected.

Git :

- Ne pas committer `db.sqlite3`.
- Ne pas committer `.idea/`.
- Ne pas committer `__pycache__/`.

---

## 6. Authentification

Django gère la session web.

Backend d'auth :

```text
portal/authentication.py
```

Le backend appelle :

```text
portal/services/ldap_auth.py
```

`ldap_auth(...)` tente d'utiliser :

```python
from MYLibrary import users
```

Si la lib n'est pas présente en local, l'auth LDAP retourne `False`, sans casser
le serveur. Le fallback `ModelBackend` permet d'utiliser un user Django local
en dev.

Le vrai flow attendu :

1. L'utilisateur saisit username/password.
2. Django appelle `InternalLdapBackend`.
3. `ldap_auth(domain, username, password, authorized_groups)` retourne `True`
   ou `False`.
4. Si `True`, Django crée/récupère un `User` local et ouvre la session.

---

## 7. Outils Actuels

### Volumes

Fichiers :

```text
portal/services/cinder.py
templates/portal/volumes.html
```

Fonctionnement :

- Recherche par `openstack_version`, `region`, IDs de volumes.
- Parsing des IDs côté Python.
- Mock déterministe par `volume_id + openstack_version + region`.
- Les filtres de statut sont appliqués côté navigateur après la recherche.
  Ils ne doivent pas rappeler le backend.
- Détails type `openstack volume show`.
- Tenant ID cliquable, ouvre la popup account.
- Reset/delete sont simulés avec une mémoire de session.

Clés de session utilisées tant que le backend est mocké :

```text
deleted_volumes
reset_volumes
```

### Quotas

Fichiers :

```text
portal/services/quotas.py
templates/portal/quotas.html
```

Fonctionnement :

- Recherche par `openstack_version`, `project_id`, `region`.
- Le backend récupère le quota courant mocké.
- L'opérateur saisit une augmentation.
- Les diminutions sont refusées.
- Il n'y a pas d'information `used/utilisé`.
- Les overrides sont simulés en session.

Clé de session utilisée tant que le backend est mocké :

```text
quota_overrides
```

### Accounts

Fichiers :

```text
portal/services/accounts.py
templates/portal/accounts.html
templates/portal/account_details.html
static/cloud_toolbox/css/account_details.css
static/cloud_toolbox/js/account_details.js
```

Fonctionnement :

- `/tools/accounts/` valide un Project ID en UUID.
- `/tools/account-details/` valide un Account ID / owner et retourne un rapport
  account avec policies IAM mockées.
- Le lookup Project ID retourne uniquement :

```python
{
    "project_name": "...",
    "domain": "...",
    "project_id": "...",
}
```

La même logique est utilisée par :

```text
GET /api/accounts/<project_id>/
```

Le rapport `Détails Account IAM` retourne :

```text
account_id
project_name
domain
project_id
owner_display_name
iam_policy_versions
```

Les policies IAM utilisent les mêmes objets que l'outil bucket :
`IamPolicyVersion` et `IamPolicyStatement`.

### Bucket IAM Policies

Fichiers :

```text
portal/services/object_storage.py
templates/portal/bucket_policies.html
static/cloud_toolbox/css/bucket_policies.css
static/cloud_toolbox/js/bucket_policies.js
```

Fonctionnement :

- Recherche par `ring` et `bucket_name`.
- Le backend retourne un rapport mocké avec les versions de policies IAM.
- Chaque policy expose `allowed_actions` et `touched_buckets`.
- Les statements affichent `Effect`, `Action` et `Resource`.
- Le JS de page gère seulement exemple, dépliage/repliage et copie JSON.

### WWN

Fichiers :

```text
portal/services/wwn.py
templates/portal/wwn_lookup.html
```

Fonctionnement :

- Recherche un ou plusieurs WWN.
- Déduplication en conservant l'ordre.
- Retour mocké vers des volumes Cinder.
- Tenant ID cliquable comme dans l'outil volumes.

---

## 8. Ajouter Un Nouvel Outil

1. Créer la logique dans `portal/services/<outil>.py`.
2. Ajouter la vue dans `portal/views.py` ou créer un module dédié si le fichier
   recommence à mélanger trop de responsabilités.
3. Ajouter la route dans `cloud_toolbox/urls.py`.
4. Créer le template dans `templates/portal/<outil>.html`.
5. Ajouter la tuile dans le bon groupe de `TOOL_GROUPS` dans `portal/tool_catalog.py`.
6. Ajouter du JS seulement si nécessaire, dans le fichier de page concerné.
7. Lancer `python manage.py check`.

Groupes existants :

```python
TOOL_GROUPS = [
    Block Storage Tools,
    Object Storage Tools,
    Common Tools,
]
```

Si un groupe est vide, le dashboard affiche un placeholder.

---

## 9. Passage Aux Appels OpenStack Réels

Quand on ne mockera plus, supprimer les mémoires de session qui simulent les
actions. Les vrais appels OpenStack devront devenir la source de vérité.

### Volumes

Dans `portal/mock_state.py` et `portal/view_helpers.py`, supprimer :

- `session_set`;
- `mark_deleted`;
- `mark_reset`;
- les lectures `deleted_keys=session_set(...)`;
- les lectures `reset_keys=session_set(...)`;
- les écritures `request.session["deleted_volumes"]`;
- les écritures `request.session["reset_volumes"]`.

Dans `portal/services/cinder.py`, remplacer :

- `build_volumes(...)`;
- `build_volume(...)`;
- `reset_volume(...)`;
- `seed_for(...)`;
- `random_uuid(...)`;
- `random_hex(...)`;
- toute génération `random`.

Futures fonctions attendues :

```python
list_volumes(openstack_version, region, ids)
delete_volume(openstack_version, region, volume_id)
reset_volume_status(openstack_version, region, volume_id, status)
```

### Quotas

Dans `portal/views.py`, supprimer :

- `quota_overrides`;
- les lectures/écritures `request.session["quota_overrides"]`.

Dans `portal/services/quotas.py`, remplacer :

- `build_quota(...)`;
- `apply_request(...)`;
- `seed_for(...)`;
- toute génération `random`.

Futures fonctions attendues :

```python
get_quota(openstack_version, region, project_id)
set_quota(openstack_version, region, project_id, volumes, gigabytes)
```

### Accounts

Dans `portal/services/accounts.py`, remplacer :

```python
fetch_external_account(...)
```

par l'appel réel à l'API account externe.

Garder le contrat de sortie :

```python
{
    "project_name": "...",
    "domain": "...",
    "project_id": "...",
}
```

### Object Storage

Dans `portal/services/object_storage.py`, remplacer :

- `get_bucket_policy_report(...)`;
- `build_policy_versions(...)`;
- `build_read_policy(...)`;
- `build_replication_policy(...)`;
- toute génération déterministe (`seed_for`, `stable_uuid`, `random`).

Le contrat utile pour le template est :

```text
BucketDetails
  ring
  name
  owner
  owner_display_name
  creation_date
  location_constraint
  replication_direction  # none, outbound, inbound, bidirectional
  replication_destination
  replication_peer
  replication_source
  replication_target
  iam_policy_versions

IamPolicyVersion
  policy_name
  policy_arn
  version_id
  is_default_version
  create_date
  allowed_actions
  touched_buckets
  statements
```

### WWN

Dans `portal/services/wwn.py`, remplacer :

- `build_match(...)`;
- `seed_for(...)`;
- toute génération `random`.

La vue peut continuer à recevoir une liste de résultats avec :

```text
wwn
volume
backend
pool
host_path
```

si ces informations existent dans la source réelle.

---

## 10. Validation Avant De Rendre La Main

Toujours faire au minimum :

```powershell
python manage.py check
```

Pour une modification de rendu :

- vérifier la page dans le navigateur;
- vérifier que les formulaires GET/POST gardent les paramètres utiles;
- vérifier que les boutons/toggles restent lisibles;
- vérifier qu'aucune erreur console n'apparaît.

Pour une modification backend :

- tester la route avec le client Django ou le navigateur;
- vérifier les redirects POST;
- vérifier les messages utilisateur;
- vérifier que `db.sqlite3` n'est pas ajouté à Git.

---

## 11. Etat Git

Remote :

```text
git@github.com:sirpapy/scripts.git
```

Branche principale :

```text
main
```

Premier commit :

```text
743dcc6 Initial cloud toolbox version
```
