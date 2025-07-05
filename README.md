# Microsoft Entra App Registration Credential Expiry Checker

[![PyPI version](https://badge.fury.io/py/entra-expiry-checker.svg)](https://badge.fury.io/py/entra-expiry-checker)
[![Python versions](https://img.shields.io/pypi/pyversions/entra-expiry-checker.svg)](https://pypi.org/project/entra-expiry-checker/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python package for monitoring and alerting on expiring secrets and certificates in Microsoft Entra ID (formerly Azure AD) App Registrations. This tool helps you stay ahead of credential expiry issues by automatically checking your App Registrations and sending email notifications when secrets/certificates are nearing expiration.

## Features

- 🔍 **Flexible Discovery**: Check all App Registrations in your tenant or specify via Azure Table Storage
- 📧 **Email Notifications**: Send alerts via SendGrid when credentials are nearing expiration
- 🔐 **Secure Authentication**: Uses Azure CLI or Managed Identity authentication for secure access
- 📊 **Detailed Reporting**: Comprehensive logs and summary of findings
- 🚀 **Easy Deployment**: Works locally, with GitHub Actions, Azure DevOps, or any CI/CD platform

## Installation

### From PyPI (Recommended)

```bash
pip install entra-expiry-checker
```

## Quick Start

### 1. Set up Authentication

First, ensure you have the Azure CLI installed in your environment and that you are authenticated with Azure:

```bash
az login
```

> **Note**: For Azure hosted or CI/CD deployments, Azure Managed Identity can also be used (where supported by the CI/CD platform).

#### Required Permissions

The identity being used (Azure CLI logged in user or Managed Identity) must have the ability to read Applications and Users from the directory.  The following Microsoft Graph API permissions can be applied to an Managed Identity to achieve this.

- **Application.Read.All** - Required to read App Registration details
- **User.ReadBasic.All** - Required to read user information for app owners

### 2. Configure Environment Variables

Set up your SendGrid API key and other required variables:

```bash
export SG_API_KEY="SG.your_sendgrid_api_key"
export FROM_EMAIL="noreply@yourdomain.com"
```

### 3. Run the Checker

```bash
entra-expiry-checker
```

Or run directly with Python:

```bash
python -m entra_expiry_checker.main
```

## Configuration

### Environment Variables

| Variable         | Required | Description                            | Default  |
| ---------------- | -------- | -------------------------------------- | -------- |
| `SG_API_KEY`     | Yes      | SendGrid API key                       | -        |
| `FROM_EMAIL`     | Yes      | Sender email address                   | -        |
| `MODE`           | No       | Operation mode (`tenant` or `storage`) | `tenant` |
| `DAYS_THRESHOLD` | No       | Days before expiry to alert            | `30`     |
| `VERIFY_SSL`     | No       | Enable/disable SSL verification        | `true`   |

#### Tenant Mode Variables

| Variable                     | Required | Description                           |
| ---------------------------- | -------- | ------------------------------------- |
| `DEFAULT_NOTIFICATION_EMAIL` | No       | Default email for apps without owners |

#### Storage Mode Variables

| Variable              | Required | Description                   |
| --------------------- | -------- | ----------------------------- |
| `STG_ACCT_NAME`       | Yes      | Azure Storage account name    |
| `STG_ACCT_TABLE_NAME` | Yes      | Table name in storage account |

### Operation Modes

#### Tenant Mode

Checks all App Registrations in your Entra ID tenant.

##### How It Works

1. **Discovery**: Reads all App Registrations from the authenticated Entra tenant
2. **Validation**: Fetches App Registration details from Microsoft Graph API
3. **Checking**: Examines secrets and certificates for each app
4. **Notification**: Sends email alerts to the app owners (if set) + email configured in `DEFAULT_NOTIFICATION_EMAIL` environment variable (if set)
5. **Reporting**: Provides summary of processed applications

#### Storage Mode

Reads onboarded App Registrations from Azure Table Storage. This mode is useful when you want to check specific App Registrations rather than all apps in your tenant.

##### Storage Mode Prerequisites

1. **Azure Storage Account**: You need an Azure Storage account with Table Storage enabled
2. **Table Structure**: Create a table with the following schema:
   - **PartitionKey**: Email address of the person or distribution list to notify
   - **RowKey**: Object ID of the app registration

##### Table Schema Example

| PartitionKey      | RowKey                               |
| ----------------- | ------------------------------------ |
| admin@company.com | 12345678-1234-1234-1234-123456789012 |
| dev@company.com   | 87654321-4321-4321-4321-210987654321 |

##### How It Works

1. **Discovery**: Reads all entities from the specified Azure Table
2. **Validation**: Fetches app registration details from Microsoft Graph API
3. **Checking**: Examines secrets and certificates for each app
4. **Notification**: Sends email alerts to the email addresses specified in PartitionKey
5. **Reporting**: Provides summary of processed applications

> **Note**: In Storage Mode, notifications are sent only to the email addresses specified in the Azure Table Storage (PartitionKey), not to the actual owners of the App Registrations. This allows you to control who receives notifications regardless of the app's ownership in Entra ID.

##### Benefits

- **Targeted Monitoring**: Only check specific App Registrations
- **Flexible Notifications**: Different people can be notified for different apps
- **Audit Trail**: Track which apps are being monitored
- **Cost Effective**: Avoid checking unnecessary applications

## CI/CD Integration

### GitHub Actions

```yaml
name: Check Credential Expiry
on:
  schedule:
    - cron: "0 9 * * *" # Daily at 9 AM UTC

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: "3.13"
      - run: pip install entra-expiry-checker
      - run: entra-expiry-checker
        env:
          SG_API_KEY: ${{ secrets.SG_API_KEY }}
          FROM_EMAIL: ${{ vars.FROM_EMAIL }}
          MODE: ${{ vars.MODE }}
```

### Azure DevOps

```yaml
trigger: none
schedules:
  - cron: "0 9 * * *"
    displayName: Daily credential check

pool:
  vmImage: "ubuntu-latest"

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: "3.13"
  - script: pip install entra-expiry-checker
  - script: entra-expiry-checker
    env:
      SG_API_KEY: $(SG_API_KEY)
      FROM_EMAIL: $(FROM_EMAIL)
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](https://github.com/brgsstm/entra-expiry-checker#readme)
- 🐛 [Bug Reports](https://github.com/brgsstm/entra-expiry-checker/issues)
- 💡 [Feature Requests](https://github.com/brgsstm/entra-expiry-checker/issues)

## Changelog

### 1.0.0 (2025-06-05)

- Initial release
- Support for tenant and storage modes
- SendGrid email notifications
- Azure CLI + Managed Identity authentication
- Comprehensive configuration validation
