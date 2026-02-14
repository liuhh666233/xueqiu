# Project Rules

## Python

### Environment
1. Manage the dev environment with `flake.nix` only.
2. Assume `nix develop` is active.
3. Do not use `pip`, `uv`, or `poetry`.
4. Run programs as modules: `python -m package.module`.

### Library Preferences
1. Use builtin **unittest**.
   - Discover all tests: `python -m unittest discover`
   - Run verbose/specific: `python -m unittest -v path/to/test_file.py`
2. Use **pydantic v2** for schemas and domain models.
3. Use **PyTorch** and **JAX** for ML models.
4. Use **loguru** for logging.
5. Use **click** for CLI/arg parsing.
6. Prefer **pathlib** over `os.path`.
7. Use explicit `StrEnum` / `IntEnum` for enums.

### Code Style
1. **Use absolute imports**; do not use relative imports (e.g., avoid `from .x import y`).
2. Prefer specific imports (e.g., `from pydantic import BaseModel`).
3. **Use type hints everywhere**:
   - Annotate all function parameters and return types.
   - Use builtin generics (`list`, `dict`, `tuple`) instead of `typing.List`, etc.
   - For optionals, use `MyType | None` instead of `Optional[MyType]`.

### Documentation
1. **Write docstrings for all public modules, functions, classes, methods**, and public-facing APIs.
2. In docstrings:
   - **Do not include types in the `Args:` section**, type hints in signatures cover that.

## Modules

| Module | Rules file | Description |
|--------|-----------|-------------|
| models | `.claude/rules/models.md` | Pydantic v2 data models for API responses and sync manifest |
| client | `.claude/rules/client.md` | HTTP client factory with cookie parsing and UA rotation |
| api | `.claude/rules/api.md` | Xueqiu API endpoint wrappers with WAF-aware retry |
| content | `.claude/rules/content.md` | HTML extraction and HTML-to-Markdown conversion |
| storage | `.claude/rules/storage.md` | Markdown file writing, manifest persistence, filename utils |
| crawler | `.claude/rules/crawler.md` | Orchestration: sync, backfill, adaptive delay |
| cli | `.claude/rules/cli.md` | Click CLI commands (sync, status, check-auth, backfill-comments) |

## Adding a New Module

1. Create `.claude/rules/<module>.md` with `paths:` frontmatter listing all related source files
2. Add an entry to the Modules table above
3. Document: key files, architecture, design patterns, type mappings, testing conventions
