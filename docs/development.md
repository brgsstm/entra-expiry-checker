# Development Guide

This guide covers the development workflow for building and publishing the Microsoft Entra App Registration Credential Expiry Checker package.

## Development Environment Setup

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/brgsstm/entra-expiry-checker.git
cd entra-expiry-checker

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .
```

### 2. Environment Configuration

Create a `.env` file for local development:

```bash
# .env
MODE=tenant  # or storage
SG_API_KEY=your_sendgrid_api_key
FROM_EMAIL=your_email@domain.com
DAYS_THRESHOLD=30
VERIFY_SSL=true

# For storage mode
STG_ACCT_NAME=your_storage_account
STG_ACCT_TABLE_NAME=your_table_name
```

## Development Workflow

### 1. Making Changes

```bash
# Activate virtual environment
source .venv/bin/activate

# Make your code changes
# Test your changes
python -m pytest tests/ -v

# Run linting
black .
flake8 .
mypy entra_expiry_checker/

# Test the package functionality
python -m entra_expiry_checker.main
```

### 2. Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=entra_expiry_checker --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_config.py -v

# Run linting checks
black --check .
flake8 .
mypy entra_expiry_checker/
```

### 3. Building Package

```bash
# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Build package
python -m build

# Check the built package
twine check dist/*

# Test installation locally
pip install dist/*.whl
```

### 4. Publishing

#### TestPyPI (Testing)

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ entra-expiry-checker
```

#### PyPI (Production)

```bash
# Upload to PyPI
python -m twine upload dist/*
```

## Code Quality Tools

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Manual Code Formatting

```bash
# Format code with Black
black .

# Check style with Flake8
flake8 .

# Type checking with MyPy
mypy entra_expiry_checker/
```

## Key Commands Summary

| Task             | Command                                                                                     |
| ---------------- | ------------------------------------------------------------------------------------------- |
| **Setup**        | `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt` |
| **Test**         | `python -m pytest tests/ -v`                                                                |
| **Lint**         | `black . && flake8 . && mypy entra_expiry_checker/`                                         |
| **Build**        | `python -m build`                                                                           |
| **Publish Test** | `python -m twine upload --repository testpypi dist/*`                                       |
| **Publish Prod** | `python -m twine upload dist/*`                                                             |

## Troubleshooting

### Build Issues

- Ensure all dependencies are installed: `pip install -r requirements-dev.txt`
- Clean build artifacts: `rm -rf build/ dist/ *.egg-info/`
- Use virtual environment to avoid conflicts

### Test Issues

- Check environment variables are set correctly
- Ensure Azure CLI is authenticated: `az login`
- Verify SendGrid API key is valid

### Publishing Issues

- Create accounts on [TestPyPI](https://test.pypi.org/) and [PyPI](https://pypi.org/)
- Set up API tokens in `~/.pypirc`
- Use `--extra-index-url` when installing from TestPyPI

## Version Management

### Updating Version

1. Update version in `entra_expiry_checker/__init__.py`
2. Update version in `pyproject.toml`
3. Build and test the package
4. Publish to TestPyPI first
5. Publish to PyPI

### Release Process

```bash
# 1. Update version
# Edit entra_expiry_checker/__init__.py and pyproject.toml

# 2. Build package
python -m build

# 3. Test installation
pip install dist/*.whl

# 4. Test on TestPyPI
python -m twine upload --repository testpypi dist/*

# 5. Publish to PyPI
python -m twine upload dist/*

# 6. Create git tag
git tag v1.0.0
git push origin v1.0.0
```

## CI/CD Integration

The project includes GitHub Actions workflows that automatically:

- Run tests on multiple Python versions
- Perform linting checks
- Build and validate packages
- Upload build artifacts

See `.github/workflows/test.yml` for the complete CI/CD configuration.
