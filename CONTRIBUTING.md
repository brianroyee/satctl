# Contributing to satctl

Thank you for your interest in contributing to satctl!

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and constructive.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported
2. Create a detailed bug report including:
   - Your environment (OS, Python version)
   - Steps to reproduce the bug
   - Expected vs actual behavior
   - Any relevant logs or error messages

### Suggesting Features

1. Check if the feature has been suggested
2. Provide a clear description of the feature
3. Explain why this feature would be useful
4. Include any relevant use cases

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Add tests if applicable
5. Ensure code passes linting and type checking
6. Commit with clear messages
7. Push to your fork
8. Submit a pull request

## Development Setup

```bash
# Clone the repository
git clone https://github.com/satctl/satctl.git
cd satctl

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .

# Run type checker
mypy .
```

## Coding Standards

- Follow PEP 8 style guide
- Use type hints where appropriate
- Write docstrings for public functions
- Keep lines under 100 characters
- Use meaningful variable names

## Project Structure

```
satctl/
├── satctl/
│   ├── cli.py           # CLI commands
│   ├── config.py        # Configuration
│   ├── database/        # Database models and repository
│   ├── sync/           # TLE download and parsing
│   ├── propagation/    # SGP4 calculations
│   ├── tui/            # Terminal UI
│   └── utils/          # Utilities
├── tests/              # Test suite
└── pyproject.toml     # Project configuration
```

## Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Run: `pytest tests/`

## License

By contributing to satctl, you agree that your contributions will be licensed under the MIT License.
