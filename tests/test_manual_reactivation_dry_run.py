from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "manual_reactivation_dry_run.py"

FORBIDDEN_IMPORTS = (
    "app.services.reactivation_template_dispatcher",
    "app.services.reactivation_template_transport",
)


def _load_script():
    assert SCRIPT_PATH.exists(), (
        "P6-F.11.7-C requires the controlled administrative entrypoint "
        "scripts/manual_reactivation_dry_run.py"
    )

    spec = importlib.util.spec_from_file_location(
        "manual_reactivation_dry_run",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manual_reactivation_dry_run_requires_explicit_enable(
    monkeypatch,
):
    module = _load_script()

    monkeypatch.delenv("REACTIVATION_DRY_RUN_ENABLED", raising=False)

    dependency_calls = []

    def fake_build_dependencies(*args, **kwargs):
        dependency_calls.append((args, kwargs))
        raise AssertionError(
            "dependencies must not be built while dry run is disabled"
        )

    monkeypatch.setattr(
        module,
        "build_reactivation_dry_run_dependencies",
        fake_build_dependencies,
    )

    result = module.main()

    assert result != 0
    assert dependency_calls == []


def test_manual_reactivation_dry_run_rejects_ambiguous_enable_value(
    monkeypatch,
):
    module = _load_script()

    monkeypatch.setenv("REACTIVATION_DRY_RUN_ENABLED", "true")

    dependency_calls = []

    def fake_build_dependencies(*args, **kwargs):
        dependency_calls.append((args, kwargs))
        raise AssertionError(
            "ambiguous enable values must fail closed"
        )

    monkeypatch.setattr(
        module,
        "build_reactivation_dry_run_dependencies",
        fake_build_dependencies,
    )

    result = module.main()

    assert result != 0
    assert dependency_calls == []


def test_manual_reactivation_dry_run_has_no_meta_transport_imports():
    _load_script()

    source = SCRIPT_PATH.read_text(encoding="utf-8")

    for forbidden_import in FORBIDDEN_IMPORTS:
        assert forbidden_import not in source


def test_manual_reactivation_dry_run_enabled_delegates_once_and_prints_safe_summary(
    monkeypatch,
    capsys,
):
    from types import SimpleNamespace

    module = _load_script()

    monkeypatch.setenv("REACTIVATION_DRY_RUN_ENABLED", "1")
    monkeypatch.setenv(
        "REACTIVATION_DRY_RUN_CAMPAIGN_ID",
        "controlled-real-dry-run",
    )
    monkeypatch.setenv(
        "REACTIVATION_DRY_RUN_DEFAULT_COUNTRY_CODE",
        "57",
    )

    fake_settings = object()
    fake_engine = object()
    fake_patient_lookup = object()
    fake_adapter = object()
    fake_context_resolver = object()

    fake_dependencies = SimpleNamespace(
        adapter=fake_adapter,
        context_resolver=fake_context_resolver,
        default_country_code="57",
    )

    fake_result = SimpleNamespace(
        total=3,
        eligible=1,
        excluded=1,
        invalid_input=0,
        runtime_error=1,
        items=(
            SimpleNamespace(
                phone_e164="+573001234567",
                source_reference="SECRET_SOURCE_REFERENCE",
            ),
        ),
    )

    factory_calls = []
    runtime_calls = []

    monkeypatch.setattr(module, "Settings", lambda: fake_settings)
    monkeypatch.setattr(module, "engine", fake_engine)
    monkeypatch.setattr(
        module,
        "find_patient_by_phone_read_only",
        fake_patient_lookup,
    )

    def fake_build_dependencies(**kwargs):
        factory_calls.append(kwargs)
        return fake_dependencies

    def fake_run(**kwargs):
        runtime_calls.append(kwargs)
        return fake_result

    monkeypatch.setattr(
        module,
        "build_reactivation_dry_run_dependencies",
        fake_build_dependencies,
    )
    monkeypatch.setattr(
        module,
        "run_reactivation_dry_run_best_effort",
        fake_run,
    )

    result = module.main()

    assert result == 1

    assert factory_calls == [
        {
            "settings": fake_settings,
            "campaign_id": "controlled-real-dry-run",
            "default_country_code": "57",
            "engine": fake_engine,
            "patient_lookup": fake_patient_lookup,
        }
    ]

    assert runtime_calls == [
        {
            "adapter": fake_adapter,
            "context_resolver": fake_context_resolver,
            "default_country_code": "57",
        }
    ]

    captured = capsys.readouterr()

    assert (
        captured.out.strip()
        == "reactivation_dry_run total=3 eligible=1 excluded=1 "
        "invalid_input=0 runtime_error=1"
    )
    assert "+573001234567" not in captured.out
    assert "SECRET_SOURCE_REFERENCE" not in captured.out
    assert captured.err == ""


def test_manual_reactivation_dry_run_unexpected_runtime_failure_fails_closed(
    monkeypatch,
    capsys,
):
    from types import SimpleNamespace

    module = _load_script()

    monkeypatch.setenv("REACTIVATION_DRY_RUN_ENABLED", "1")
    monkeypatch.setenv(
        "REACTIVATION_DRY_RUN_CAMPAIGN_ID",
        "controlled-real-dry-run",
    )
    monkeypatch.delenv(
        "REACTIVATION_DRY_RUN_DEFAULT_COUNTRY_CODE",
        raising=False,
    )

    fake_dependencies = SimpleNamespace(
        adapter=object(),
        context_resolver=object(),
        default_country_code=None,
    )

    monkeypatch.setattr(module, "Settings", lambda: object())
    monkeypatch.setattr(
        module,
        "build_reactivation_dry_run_dependencies",
        lambda **kwargs: fake_dependencies,
    )

    def fail_runtime(**kwargs):
        raise RuntimeError(
            "SECRET_RUNTIME_DETAIL +573001234567"
        )

    monkeypatch.setattr(
        module,
        "run_reactivation_dry_run_best_effort",
        fail_runtime,
    )

    result = module.main()

    assert result != 0

    captured = capsys.readouterr()

    combined_output = captured.out + captured.err

    assert "SECRET_RUNTIME_DETAIL" not in combined_output
    assert "+573001234567" not in combined_output
