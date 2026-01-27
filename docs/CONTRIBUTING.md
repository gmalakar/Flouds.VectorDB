# Contributing to FloudsVector.Py

We welcome contributions! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/FloudsVector.Py.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes: `pytest tests/`
6. Commit: `git commit -m "Add your feature"`
7. Push: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Development Setup

```bash
# Install dependencies
pip install -r app/requirements.txt

# Run tests
pytest tests/

# Run linting
black app/
isort app/

# Start development server
python -m app.main
```

## Code Style

- Use Black for code formatting
- Use isort for import sorting
- Follow PEP 8 guidelines
- Add type hints where possible
- Write docstrings for functions and classes

## Testing

- Write tests for new features
- Maintain test coverage above 80%
- Use pytest for testing
- Mock external dependencies

## Pull Request Guidelines

- Keep PRs focused and small
- Write clear commit messages
- Update documentation if needed
- Add tests for new features
- Ensure all tests pass

## Areas for Contribution

- Bug fixes
- Performance improvements
- Documentation updates
- New features
- Test coverage improvements
- Docker/deployment enhancements

## Questions?

Open an issue or contact the maintainers.
