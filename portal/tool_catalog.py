BLOCK_STORAGE_TOOLS = [
    {
        "id": "volumes",
        "route_name": "volumes",
        "title": "Gestionnaire de Volumes",
        "category": "Stockage",
        "icon_name": "HardDrive",
        "description": (
            "Recherchez, analysez, réinitialisez et supprimez vos volumes "
            "de stockage cloud."
        ),
    },
    {
        "id": "quotas",
        "route_name": "quotas",
        "title": "Gestionnaire de Quotas",
        "category": "Capacité",
        "icon_name": "Server",
        "description": (
            "Contrôlez les quotas Cinder d'un projet et préparez les "
            "augmentations demandées."
        ),
    },
    {
        "id": "accounts",
        "route_name": "accounts",
        "title": "Recherche Account",
        "category": "Identité",
        "icon_name": "Search",
        "description": "Récupérez les détails d'un account à partir d'un Project ID.",
    },
    {
        "id": "wwn",
        "route_name": "wwn_lookup",
        "title": "Recherche WWN",
        "category": "Stockage",
        "icon_name": "Link",
        "description": "Retrouvez les volumes correspondant à un ou plusieurs WWN.",
    },
]


OBJECT_STORAGE_TOOLS = [
    {
        "id": "bucket-policies",
        "route_name": "bucket_policies",
        "title": "Bucket IAM Policies",
        "category": "Object Storage",
        "icon_name": "Server",
        "description": (
            "Retrouvez les policies IAM qui touchent un bucket et inspectez "
            "leurs statements."
        ),
    },
]


COMMON_TOOLS = [
    {
        "id": "account-details",
        "route_name": "account_details",
        "title": "Détails Account IAM",
        "category": "Identité",
        "icon_name": "Server",
        "description": (
            "Affichez les détails d'un account et les policies IAM "
            "qui lui sont appliquées."
        ),
    },
]


TOOL_GROUPS = [
    {
        "id": "block-storage-tools",
        "title": "Block Storage Tools",
        "description": "Outils Cinder pour les volumes, quotas et recherches de stockage bloc.",
        "tools": BLOCK_STORAGE_TOOLS,
    },
    {
        "id": "object-storage-tools",
        "title": "Object Storage Tools",
        "description": "Outils Swift et stockage objet.",
        "tools": OBJECT_STORAGE_TOOLS,
    },
    {
        "id": "common-tools",
        "title": "Common Tools",
        "description": "Outils transverses partagés entre plusieurs plateformes.",
        "tools": COMMON_TOOLS,
    },
]
