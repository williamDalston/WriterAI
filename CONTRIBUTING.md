# Contributing to WriterAI

Thank you for your interest in contributing to WriterAI/Prometheus Novel!

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Poetry for dependency management
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd WriterAI
   ```

2. **Install dependencies**
   ```bash
   cd prometheus_novel
   poetry install
   ```

3. **Set up pre-commit hooks** (optional but recommended)
   ```bash
   poetry run pre-commit install
   ```

4. **Set up environment**
   ```bash
   cp .env.example .env
   # Add your API keys to .env
   ```

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**
   - Write code
   - Add tests
   - Update documentation

3. **Run tests locally**
   ```bash
   make test
   # or
   cd prometheus_novel && poetry run pytest tests/
   ```

4. **Check code quality**
   ```bash
   make lint      # Check for issues
   make format    # Auto-format code
   make typecheck # Type checking
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   # or
   git commit -m "fix: resolve bug in X"
   ```

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(cli): add project quick-start system
fix(parser): handle empty character descriptions
docs(readme): update installation instructions
test(unit): add tests for project parser
```

### Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new features
3. **Ensure all tests pass**
   ```bash
   make test
   ```
4. **Ensure code quality checks pass**
   ```bash
   make check-all
   ```
5. **Push your branch**
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Create a Pull Request** on GitHub
   - Fill out the PR template
   - Link any related issues
   - Request reviews

### Code Review

- PRs require at least one approval
- Address review comments
- Keep PRs focused and reasonably sized
- Respond to feedback promptly

## Code Standards

### Python Style

- Follow PEP 8
- Use type hints for function signatures
- Maximum line length: 120 characters
- Use meaningful variable names
- Write docstrings for public functions/classes

**Example:**
```python
def parse_novel_description(text: str, genre: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse a novel description and extract structured information.
    
    Args:
        text: The novel description text
        genre: Optional genre override
    
    Returns:
        Dictionary containing extracted novel details
    
    Raises:
        ValueError: If text is empty or invalid
    """
    if not text.strip():
        raise ValueError("Description text cannot be empty")
    
    # Implementation...
    return result
```

### Testing

- Write unit tests for new functions
- Add integration tests for feature workflows
- Maintain or improve code coverage
- Use fixtures from `tests/conftest.py`

**Test structure:**
```python
import pytest

@pytest.mark.unit
class TestNovelParser:
    def test_parse_basic_text(self, sample_text):
        parser = NovelParser()
        result = parser.parse(sample_text)
        
        assert result['title'] == 'Expected Title'
        assert result['genre'] == 'sci-fi'
```

### Documentation

- Update README.md for user-facing changes
- Update docs/ for architectural changes
- Add docstrings to new code
- Include examples in docstrings
- Update CHANGELOG.md

## Project Structure

```
WriterAI/
├── prometheus_novel/        # Main application
│   ├── interfaces/         # User interfaces (CLI, API, Web)
│   ├── prometheus_lib/     # Core library
│   ├── stages/            # Pipeline stages
│   ├── tests/             # Test suite
│   ├── configs/           # Configuration files
│   ├── prompts/           # Prompt templates
│   └── docs/              # Documentation
├── examples/              # Example projects
└── [Root documentation]   # README, guides, etc.
```

## Adding New Features

### Adding a Pipeline Stage

1. Create stage file in `stages/stage_XX_name.py`
2. Implement the stage function
3. Add prompts in `prompts/default/`
4. Update pipeline configuration
5. Add tests in `tests/unit/` and `tests/integration/`
6. Update documentation

### Adding CLI Commands

1. Add command in `interfaces/cli/main.py`
2. Create handler function
3. Add help text and arguments
4. Add tests in `tests/unit/test_cli.py`
5. Update USAGE_GUIDE.md

### Adding Tests

1. Choose appropriate directory:
   - `tests/unit/` - Individual component tests
   - `tests/integration/` - Multi-component tests
   - `tests/e2e/` - Full pipeline tests

2. Use existing fixtures from `conftest.py`

3. Mark tests appropriately:
   ```python
   @pytest.mark.unit
   @pytest.mark.asyncio
   async def test_something():
       ...
   ```

## Running Tests

```bash
# All tests
make test

# Specific test types
make test-unit
make test-integration
pytest tests/e2e/

# With coverage
make coverage

# Fast tests only (skip slow ones)
make test-fast

# Specific test file
pytest tests/unit/test_parser.py -v

# Specific test function
pytest tests/unit/test_parser.py::TestParser::test_basic -v
```

## Code Quality Checks

```bash
# Run all checks
make check-all

# Individual checks
make lint        # Ruff linting
make format      # Auto-format with Ruff
make typecheck   # MyPy type checking

# Pre-commit (runs automatically on commit if installed)
pre-commit run --all-files
```

## Common Tasks

### Adding Dependencies

```bash
cd prometheus_novel
poetry add package-name

# Dev dependencies
poetry add --group dev package-name
```

### Updating Documentation

1. Edit relevant .md files
2. Rebuild docs if needed
3. Check links and formatting
4. Commit with `docs:` prefix

### Debugging

```python
# Add breakpoint in code
breakpoint()

# Or use pdb
import pdb; pdb.set_trace()

# Check logs
tail -f logs/prometheus_novel.log
```

## Release Process

(Maintainers only)

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Run full test suite
4. Create git tag
5. Push tag to trigger release workflow

## Getting Help

- **Documentation**: Check `docs/` directory
- **Examples**: See `examples/` directory
- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions
- **Questions**: Ask in pull request or issue

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn
- Focus on the code, not the person
- Follow project guidelines

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.

## Questions?

If you have questions about contributing:
1. Check existing documentation
2. Look at similar past contributions
3. Open a discussion on GitHub
4. Ask in your pull request

---

**Thank you for contributing to WriterAI!** 🎉

Your contributions help make novel generation more accessible to everyone.

