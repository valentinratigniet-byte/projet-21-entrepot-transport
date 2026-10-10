"""Déploie le modèle TransVal et les 23 rapports dans un espace de travail Fabric / Power BI (fabric-cicd).

    python powerbi/deployer.py DEV        # ou PROD

Variables d'environnement : FABRIC_WORKSPACE_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
(principal de service autorisé sur l'espace de travail). Sans elles, les identifiants Azure CLI sont utilisés (az login).
"""
import os
import sys
from pathlib import Path

from azure.identity import AzureCliCredential, ClientSecretCredential
from fabric_cicd import FabricWorkspace, publish_all_items, unpublish_all_orphan_items

env = sys.argv[1] if len(sys.argv) > 1 else "DEV"
if all(os.getenv(v) for v in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")):
    cred = ClientSecretCredential(os.environ["AZURE_TENANT_ID"], os.environ["AZURE_CLIENT_ID"], os.environ["AZURE_CLIENT_SECRET"])
else:
    cred = AzureCliCredential()

ws = FabricWorkspace(
    workspace_id=os.environ["FABRIC_WORKSPACE_ID"],
    environment=env,  # clé de parameter.yml
    repository_directory=str(Path(__file__).parent),
    item_type_in_scope=["SemanticModel", "Report"],
    token_credential=cred,
)
publish_all_items(ws)
unpublish_all_orphan_items(ws)  # un rapport supprimé du dépôt disparaît aussi de l'espace de travail
