"""
Microsoft Graph API client for interacting with Azure AD app registrations.
"""

import sys
from typing import Any, Dict, List

try:
    import requests
    from azure.core.exceptions import (ClientAuthenticationError,
                                       ResourceNotFoundError)
    from azure.identity import DefaultAzureCredential
except ImportError as e:
    print(f"Missing required dependency: {e}")
    sys.exit(1)


class MicrosoftGraphClient:
    """Client for interacting with Microsoft Graph API."""

    def __init__(self):
        """Initialize the Microsoft Graph client using DefaultAzureCredential."""
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.credential = DefaultAzureCredential()

    def get_access_token(self) -> str:
        """Get access token for Microsoft Graph API."""
        try:
            token = self.credential.get_token(
                "https://graph.microsoft.com/.default")
            return token.token
        except ClientAuthenticationError as e:
            print(f"Authentication failed: {e}")
            print(
                "Please ensure you are logged in with 'az login' or have appropriate credentials configured."
            )
            sys.exit(1)

    def make_request(self, endpoint: str, method: str = "GET") -> Dict[str, Any]:
        """
        Make a request to Microsoft Graph API.

        Args:
            endpoint: API endpoint (without base URL)
            method: HTTP method

        Returns:
            Response data as dictionary

        Raises:
            ResourceNotFoundError: If the resource is not found (404 or specific 400 errors)
            requests.exceptions.HTTPError: For other HTTP errors
            requests.exceptions.RequestException: For network/connection errors
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.request(method, url, headers=headers)

            # Handle specific error cases
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    error_code = error_data.get("error", {}).get("code", "")
                    error_message = error_data.get(
                        "error", {}).get("message", "")

                    if (
                        "Request_BadRequest" in error_code
                        and "Invalid object identifier" in error_message
                    ):
                        raise ResourceNotFoundError(
                            f"App registration not found: {error_message}"
                        )
                except ValueError:
                    # If response is not JSON, continue with normal error handling
                    pass

            # Handle other specific status codes
            if response.status_code == 401:
                raise requests.exceptions.HTTPError(
                    "Unauthorized - check your credentials and permissions"
                )
            elif response.status_code == 403:
                raise requests.exceptions.HTTPError(
                    "Forbidden - insufficient permissions to access this resource"
                )
            elif response.status_code == 404:
                raise ResourceNotFoundError("Resource not found")
            elif response.status_code == 429:
                raise requests.exceptions.HTTPError(
                    "Rate limited - too many requests")
            elif response.status_code >= 500:
                raise requests.exceptions.HTTPError(
                    f"Server error: {response.status_code}"
                )

            # Raise for any other HTTP errors
            response.raise_for_status()
            return response.json()

        except (ResourceNotFoundError, requests.exceptions.HTTPError):
            # Re-raise these specific exceptions for proper handling
            raise
        except requests.exceptions.RequestException as e:
            # For network/connection errors, provide more context
            raise requests.exceptions.RequestException(
                f"Network error making request to {endpoint}: {e}"
            )
        except Exception as e:
            # Catch any other unexpected errors
            raise Exception(
                f"Unexpected error making request to {endpoint}: {e}")

    def get_all_applications(self) -> List[Dict[str, Any]]:
        """
        Get all applications in the tenant.

        Returns:
            List of all applications with their basic information
        """
        applications = []
        endpoint = "/applications"

        while endpoint:
            try:
                response = self.make_request(endpoint)
                applications.extend(response.get("value", []))

                # Check for next page
                endpoint = response.get("@odata.nextLink")
                if endpoint:
                    # Remove the base URL to get just the endpoint
                    endpoint = endpoint.replace(self.base_url, "")

            except Exception as e:
                print(f"❌ Error fetching applications: {e}")
                break

        print(f"✅ Retrieved {len(applications)} applications from tenant")
        return applications
