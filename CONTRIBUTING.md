# Contributing to AI Stock Analysis Assistant

Thank you for your interest in contributing! Here's how you can help make this project better.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Report issues professionally
- Respect intellectual property

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/ai-stock-analysis.git`
3. Create a feature branch: `git checkout -b feature/your-feature`
4. Install development dependencies: `pip install -r requirements.txt`
5. Make your changes
6. Add tests for new functionality
7. Commit: `git commit -m "Add feature: description"`
8. Push: `git push origin feature/your-feature`
9. Create a Pull Request

## Pull Request Process

1. Update README.md with any new features or API changes
2. Add tests covering your changes
3. Ensure all tests pass: `pytest tests/`
4. Update CHANGELOG.md
5. Request review from maintainers
6. Address review comments
7. Merge only after approval

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest black flake8 mypy

# Run tests
pytest tests/

# Code formatting
black backend/ frontend/

# Linting
flake8 backend/

# Type checking
mypy backend/
```

## Coding Standards

- **Python**: Follow PEP 8 style guide
- **JavaScript**: Use consistent formatting
- **Comments**: Write clear, concise comments
- **Type Hints**: Use Python type hints where applicable
- **Error Handling**: Handle errors gracefully

## Commit Messages

Format: `type(scope): description`

Examples:
- `feat(sentiment): add multi-language support`
- `fix(api): resolve rate limiting issue`
- `docs(readme): update installation instructions`
- `test(indicators): add RSI calculation tests`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `style`: Formatting changes

## Reporting Issues

Include:
- Clear description of the issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- Screenshots/logs if applicable
- Environment details (Python version, OS, etc.)

## Feature Requests

Describe:
- The feature you want to add
- Why it's needed
- How it should work
- Examples of use cases

## Questions?

- Check existing issues/discussions
- Read documentation
- Ask in GitHub Discussions
- Open an issue for clarification

## Recognition

Contributors will be:
- Added to CONTRIBUTORS.md
- Mentioned in release notes
- Credited in project documentation

## Licensing

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to AI Stock Analysis Assistant! 🙏

