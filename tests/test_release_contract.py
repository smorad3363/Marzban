import re
from pathlib import Path


def test_release_version_and_install_rollback_contract():
    version = Path("VERSION").read_text(encoding="utf-8").strip()
    app_source = Path("app/__init__.py").read_text(encoding="utf-8")
    installer = Path("scripts/marzban.sh").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/build.yml").read_text(encoding="utf-8")
    release_docs = Path("RELEASES.md").read_text(encoding="utf-8")

    app_version = re.search(
        r'^__version__ = "([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?)"$',
        app_source,
        re.MULTILINE,
    )
    assert app_version is not None
    assert version == app_version.group(1) == "5.0.0-rc.8"

    assert 'MARZBAN_GITHUB_BRANCH="${MARZBAN_GITHUB_BRANCH:-master}"' in installer
    assert 'MARZBAN_DOCKER_IMAGE="${MARZBAN_DOCKER_IMAGE:-ghcr.io/smorad3363/marzban}"' in installer
    assert 'target_image=$(marzban_docker_image "$requested_version")' in installer
    assert 'update_command --version "$1"' in installer
    assert 'if [ "$#" -eq 0 ]; then' in installer
    assert 'cli_command admin set-owner' in installer
    assert 'cli_command admin set-owner --username "$1"' in installer
    assert 'install_marzban_script_from_repo "$marzban_version"' in installer
    assert 'update_marzban_script "$requested_version"' in installer
    assert 'script_ref=$(marzban_script_ref "$requested_version")' in installer
    assert (
        '[[ "$requested_version" =~ '
        '^v[0-9]+\\.[0-9]+\\.[0-9]+(-[0-9A-Za-z][0-9A-Za-z.-]*)?$ ]]'
        in installer
    )
    assert 'tags:' in workflow and '- "v*"' in workflow
    assert '${IMAGE_NAME}:${VERSION_TAG}' in workflow
    assert 'if [[ "${VERSION_TAG}" != *-* ]]; then' in workflow
    assert 'release_flags+=(--prerelease)' in workflow
    assert 'gh release create "${VERSION_TAG}"' in workflow
    for isolated_test in (
        "test_mysql_stage8_bulk_jobs.py",
        "test_mysql_stage9_dashboard.py",
        "test_mysql_stage10_pagination.py",
        "test_mysql_stage11_operations.py",
    ):
        assert f"--ignore=tests/{isolated_test}" in workflow
        assert f"tests/{isolated_test}" in workflow
    assert "Verify Stage 8-11 isolated MySQL evidence" in workflow
    assert "matrix.mysql-image == 'mysql:8.0'" in workflow

    assert "marzban update --version v5.0.0-rc.8" in release_docs
    assert "install --version v5.0.0-rc.8 --database mysql" in release_docs
    assert "marzban update --version v5.0.0-rc.7" in release_docs
    assert "install --version v5.0.0-rc.7 --database mysql" in release_docs
    assert "marzban update --version v5.0.0-rc.6" in release_docs
    assert "install --version v5.0.0-rc.6 --database mysql" in release_docs
    assert "marzban update --version v5.0.0-rc.5" in release_docs
    assert "install --version v5.0.0-rc.5 --database mysql" in release_docs
    assert "marzban update --version v5.0.0-rc.4" in release_docs
    assert "install --version v5.0.0-rc.4 --database mysql" in release_docs
    assert "marzban update --version v5.0.0-rc.3" in release_docs
    assert "install --version v5.0.0-rc.3 --database mysql" in release_docs
    assert "marzban update --version v5.0.0-rc.2" in release_docs
    assert "install --version v5.0.0-rc.2 --database mysql" in release_docs
    assert "marzban update --version v5.0.0-rc.1" in release_docs
    assert "install --version v5.0.0-rc.1 --database mysql" in release_docs
    assert "install --version v4.9.8 --database mysql" in release_docs
    assert "install --version v4.9.6 --database mysql" in release_docs
    assert "marzban rollback v4.9.6" in release_docs
