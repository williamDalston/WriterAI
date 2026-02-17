"""
Unified Config Resolution

Single canonical path: env defaults → project config → CLI overlay → resolved output.
Writes resolved_config.yaml to run output for perfect reproducibility.

Uses deep merge: nested dicts (model_defaults, defense, etc.) are recursively overlaid,
not replaced, so project config can extend env defaults without wiping them.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml
import copy
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone


def _deep_merge(base: Dict, overlay: Dict) -> Dict:
    """Recursively merge overlay into base. Overlay wins on conflicts.

    Semantics:
    - Nested dicts: recursive merge (project can extend env without wiping).
    - Lists, scalars, None: replaced entirely by overlay (predictable, no concat).
    """
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_env_defaults(env: Optional[str] = None) -> Dict[str, Any]:
    """Load environment-level defaults (the_empathy_clause.yaml or {env}_config.yaml)."""
    configs_dir = Path(__file__).parent
    config_name = f"{env}_config.yaml" if env else "the_empathy_clause.yaml"
    config_path = configs_dir / config_name

    if not config_path.exists():
        if env:
            config_path = configs_dir / "the_empathy_clause.yaml"
        if not config_path.exists():
            return {}

    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_project_config(project_path: Path) -> Dict[str, Any]:
    """Load project-level config.yaml."""
    config_file = project_path / "config.yaml"
    if not config_file.exists():
        return {}

    with open(config_file, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_config(
    project_path: Path,
    env: Optional[str] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Produce a single resolved config: env → project → CLI.
    Later layers override earlier. Returns merged dict.
    """
    resolved: Dict[str, Any] = {}

    # 1. Env defaults (model_defaults, budget_usd, etc.)
    env_cfg = load_env_defaults(env)
    if env_cfg:
        resolved = _deep_merge(resolved, env_cfg)

    # 2. Project config (title, synopsis, key_plot_points, etc.)
    project_cfg = load_project_config(project_path)
    if project_cfg:
        resolved = _deep_merge(resolved, project_cfg)

    # 3. CLI overrides (e.g. --model, --budget)
    if cli_overrides:
        resolved = _deep_merge(resolved, cli_overrides)

    # Ensure project_name and project_path are set
    if "project_name" not in resolved and project_cfg:
        resolved["project_name"] = project_cfg.get("project_name", project_path.name)
    if "project_name" not in resolved:
        resolved["project_name"] = project_path.name

    # Optional config validation (enhancements.config_validation)
    val_cfg = resolved.get("enhancements", {}).get("config_validation", {})
    if val_cfg.get("enabled", True):
        try:
            from configs.schema_validator import validate_config
            mode = str(val_cfg.get("mode", "warn")).lower()
            passed, issues = validate_config(resolved, mode=mode)
            for issue in issues:
                if issue.startswith("ERROR"):
                    import logging
                    logging.getLogger("config_validator").error(issue)
                elif issue.startswith("WARN"):
                    import logging
                    logging.getLogger("config_validator").warning(issue)
            if not passed and mode == "strict":
                raise ValueError("Config validation failed. Fix errors and retry.")
        except ImportError:
            pass

    return resolved


def _get_provenance(project_path: Path, seed_fingerprint: Optional[str] = None) -> Dict[str, Any]:
    """Build provenance meta block for reproducibility.
    Degrades gracefully when run outside a git repo or when git is unavailable.
    """
    # Git hash (best-effort); search from project dir up to repo root
    git_commit = ""
    search_dir = project_path if project_path.is_dir() else project_path.parent
    try:
        for _ in range(8):  # limit depth
            if (search_dir / ".git").exists():
                break
            parent = search_dir.parent
            if parent == search_dir:
                break
            search_dir = parent

        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=search_dir,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if r.returncode == 0:
            git_commit = r.stdout.strip()[:12]
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=search_dir,
            capture_output=True,
            text=True,
            timeout=2,
        )
        dirty = "--dirty" if r.returncode == 0 and r.stdout.strip() else ""
        if git_commit:
            git_commit += dirty
    except Exception:
        pass

    return {
        "run_id": str(uuid.uuid4())[:8],
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_commit": git_commit or "(unknown)",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.system(),
        "seed_fingerprint": seed_fingerprint or "(none)",
    }


def _model_summary(model_defaults: Dict) -> str:
    """Short summary of model routing for provenance."""
    if not model_defaults:
        return "(defaults)"
    api = model_defaults.get("api_model", "")
    critic = model_defaults.get("critic_model", api)
    return f"api={api}, critic={critic}"


def write_resolved(
    output_dir: Path,
    resolved: Dict[str, Any],
    filename: str = "resolved_config.yaml",
    provenance: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write resolved config to output dir for reproducibility.
    Ensures output_dir exists. Injects meta.provenance if provided.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / filename

    to_write = dict(resolved)
    if provenance:
        to_write.setdefault("meta", {})["provenance"] = provenance

    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(to_write, f, default_flow_style=False, allow_unicode=True)
    return out_path


def resolve_and_write(
    project_path: Path,
    env: Optional[str] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
    seed_fingerprint: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve config and write to project_path/output/resolved_config.yaml with provenance."""
    resolved = resolve_config(project_path, env=env, cli_overrides=cli_overrides)

    prov = _get_provenance(project_path, seed_fingerprint)
    prov["model_routing_summary"] = _model_summary(resolved.get("model_defaults", {}))

    output_dir = project_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    write_resolved(output_dir, resolved, provenance=prov)
    return resolved


def update_resolved_outline_meta(
    output_dir: Path,
    outline_json_report: Optional[Dict[str, Any]] = None,
) -> None:
    """Merge outline_json summary counters into resolved_config.yaml meta."""
    if not outline_json_report:
        return
    out_path = output_dir / "resolved_config.yaml"
    if not out_path.exists():
        return
    try:
        with open(out_path, encoding="utf-8") as f:
            resolved = yaml.safe_load(f) or {}
        meta = resolved.setdefault("meta", {})
        prov = meta.setdefault("provenance", {})
        batches = outline_json_report.get("batches", [])
        parse_failures = sum(b.get("parse_failures", 0) for b in batches)
        repair_uses = sum(b.get("repair_uses", 0) for b in batches)
        backfill_retries = len(outline_json_report.get("backfill", {}).get("attempts", []))
        prov["outline_json"] = {
            "parse_failures": parse_failures,
            "repair_uses": repair_uses,
            "backfill_retries": backfill_retries,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.dump(resolved, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        import logging
        logging.getLogger("config_resolver").warning("Failed to update resolved_config outline meta: %s", e)
