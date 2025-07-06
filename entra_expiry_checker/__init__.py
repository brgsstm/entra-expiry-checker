"""
Microsoft Entra App Registration Credential Expiry Checker

A Python package for monitoring and alerting on expiring secrets and certificates
in Azure AD/Entra ID app registrations.
"""

__version__ = "1.0.2"
__author__ = "Tom Burgess"
__email__ = "tom@tburgess.co.uk"
__description__ = "Microsoft Entra App Registration Credential Expiry Checker"

from .clients.graph_client import MicrosoftGraphClient
from .clients.table_client import TableStorageClient
from .config import Settings
from .orchestrator import SecretExpiryOrchestrator
from .services.email_service import EmailService

__all__ = [
    "Settings",
    "SecretExpiryOrchestrator",
    "MicrosoftGraphClient",
    "TableStorageClient",
    "EmailService",
]
