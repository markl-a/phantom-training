# phantom-training 索引

更新日期：2026-06-27

本文件是專案導覽索引，目的在於讓人類維護者與 AI agent 能快速找到每個文件、程式碼、測試、設定與範例入口。

索引範圍：目前 git 追蹤的全部檔案，加上本 index.md。

## 快速入口

- [README.md](README.md)
- [PHANTOM-SATELLITES-OPEN-SOURCE-FINAL-SUMMARY.md](PHANTOM-SATELLITES-OPEN-SOURCE-FINAL-SUMMARY.md)
- [docs/OPEN_SOURCE_READINESS.md](docs/OPEN_SOURCE_READINESS.md)
- [docs/FINAL_RELEASE_AUDIT.md](docs/FINAL_RELEASE_AUDIT.md)
- [docs/PUBLIC_RELEASE_APPROVAL.md](docs/PUBLIC_RELEASE_APPROVAL.md)
- [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md)
- [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md)
- [CHANGELOG.md](CHANGELOG.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [LICENSE](LICENSE)
- [pyproject.toml](pyproject.toml)
- [.github/workflows/ci.yml](.github/workflows/ci.yml)

## 文件索引

- [CHANGELOG.md](CHANGELOG.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [docs/_archive/02-phantom-training.md](docs/_archive/02-phantom-training.md)
- [docs/_archive/2026-05-22-tier1-initial-dev.md](docs/_archive/2026-05-22-tier1-initial-dev.md)
- [docs/_archive/DESIGN.md](docs/_archive/DESIGN.md)
- [docs/_archive/INDEX.md](docs/_archive/INDEX.md)
- [docs/_archive/OSS-LANDSCAPE-AND-DIRECTION.md](docs/_archive/OSS-LANDSCAPE-AND-DIRECTION.md)
- [docs/_archive/ROADMAP.md](docs/_archive/ROADMAP.md)
- [docs/_archive/ROADMAP.zh-TW.md](docs/_archive/ROADMAP.zh-TW.md)
- [docs/demo.cast](docs/demo.cast)
- [docs/EVAL_JUDGE_SCENARIO.md](docs/EVAL_JUDGE_SCENARIO.md)
- [docs/FINAL_RELEASE_AUDIT.md](docs/FINAL_RELEASE_AUDIT.md)
- [docs/OPEN_SOURCE_READINESS.md](docs/OPEN_SOURCE_READINESS.md)
- [docs/phantom-training.md](docs/phantom-training.md)
- [docs/PUBLIC_DEMO.md](docs/PUBLIC_DEMO.md)
- [docs/PUBLIC_RELEASE_APPROVAL.md](docs/PUBLIC_RELEASE_APPROVAL.md)
- [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md)
- [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md)
- [docs/TAG_PLAN.md](docs/TAG_PLAN.md)
- [LICENSE](LICENSE)
- [PHANTOM-SATELLITES-OPEN-SOURCE-FINAL-SUMMARY.md](PHANTOM-SATELLITES-OPEN-SOURCE-FINAL-SUMMARY.md)
- [README.md](README.md)
- [SECURITY.md](SECURITY.md)

## 完整檔案索引

### 根目錄

- [.gitignore](.gitignore)
- [CHANGELOG.md](CHANGELOG.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [index.md](index.md)
- [LICENSE](LICENSE)
- [PHANTOM-SATELLITES-OPEN-SOURCE-FINAL-SUMMARY.md](PHANTOM-SATELLITES-OPEN-SOURCE-FINAL-SUMMARY.md)
- [pyproject.toml](pyproject.toml)
- [README.md](README.md)
- [SECURITY.md](SECURITY.md)

### .github

- [.github/workflows/ci.yml](.github/workflows/ci.yml)

### docs

- [docs/_archive/02-phantom-training.md](docs/_archive/02-phantom-training.md)
- [docs/_archive/2026-05-22-tier1-initial-dev.md](docs/_archive/2026-05-22-tier1-initial-dev.md)
- [docs/_archive/DESIGN.md](docs/_archive/DESIGN.md)
- [docs/_archive/INDEX.md](docs/_archive/INDEX.md)
- [docs/_archive/OSS-LANDSCAPE-AND-DIRECTION.md](docs/_archive/OSS-LANDSCAPE-AND-DIRECTION.md)
- [docs/_archive/ROADMAP.md](docs/_archive/ROADMAP.md)
- [docs/_archive/ROADMAP.zh-TW.md](docs/_archive/ROADMAP.zh-TW.md)
- [docs/demo.cast](docs/demo.cast)
- [docs/EVAL_JUDGE_SCENARIO.md](docs/EVAL_JUDGE_SCENARIO.md)
- [docs/FINAL_RELEASE_AUDIT.md](docs/FINAL_RELEASE_AUDIT.md)
- [docs/OPEN_SOURCE_READINESS.md](docs/OPEN_SOURCE_READINESS.md)
- [docs/phantom-training.md](docs/phantom-training.md)
- [docs/PUBLIC_DEMO.md](docs/PUBLIC_DEMO.md)
- [docs/PUBLIC_RELEASE_APPROVAL.md](docs/PUBLIC_RELEASE_APPROVAL.md)
- [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md)
- [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md)
- [docs/TAG_PLAN.md](docs/TAG_PLAN.md)

### examples

- [examples/rust-coder.toml](examples/rust-coder.toml)

### phantom_training

- [phantom_training/__init__.py](phantom_training/__init__.py)
- [phantom_training/backend_lifecycle.py](phantom_training/backend_lifecycle.py)
- [phantom_training/cli.py](phantom_training/cli.py)
- [phantom_training/config.py](phantom_training/config.py)
- [phantom_training/dataset.py](phantom_training/dataset.py)
- [phantom_training/demo_loop.py](phantom_training/demo_loop.py)
- [phantom_training/eval_judge_scenario.py](phantom_training/eval_judge_scenario.py)
- [phantom_training/eval.py](phantom_training/eval.py)
- [phantom_training/fixtures.py](phantom_training/fixtures.py)
- [phantom_training/hermetic_judge.py](phantom_training/hermetic_judge.py)
- [phantom_training/judge.py](phantom_training/judge.py)

### tests

- [tests/__init__.py](tests/__init__.py)
- [tests/conftest.py](tests/conftest.py)
- [tests/test_backend_lifecycle_contract.py](tests/test_backend_lifecycle_contract.py)
- [tests/test_cli_judge.py](tests/test_cli_judge.py)
- [tests/test_cli_outputs.py](tests/test_cli_outputs.py)
- [tests/test_cli_validation.py](tests/test_cli_validation.py)
- [tests/test_cli.py](tests/test_cli.py)
- [tests/test_config.py](tests/test_config.py)
- [tests/test_dataset_fallbacks.py](tests/test_dataset_fallbacks.py)
- [tests/test_dataset_recall.py](tests/test_dataset_recall.py)
- [tests/test_demo_loop_contract.py](tests/test_demo_loop_contract.py)
- [tests/test_eval_judge_scenario_contract.py](tests/test_eval_judge_scenario_contract.py)
- [tests/test_eval_robustness.py](tests/test_eval_robustness.py)
- [tests/test_hermetic_judge.py](tests/test_hermetic_judge.py)
- [tests/test_internals.py](tests/test_internals.py)
- [tests/test_judge_real.py](tests/test_judge_real.py)
- [tests/test_open_source_contract.py](tests/test_open_source_contract.py)
- [tests/test_packaging.py](tests/test_packaging.py)
- [tests/test_release_prep_contract.py](tests/test_release_prep_contract.py)
- [tests/test_to_instruction_rows.py](tests/test_to_instruction_rows.py)

