import re
from pathlib import Path


def test_release_version_and_install_rollback_contract():
    version = Path("VERSION").read_text(encoding="utf-8").strip()
    app_source = Path("app/__init__.py").read_text(encoding="utf-8")
    installer = Path("scripts/marzban.sh").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/build.yml").read_text(encoding="utf-8")
    release_docs = Path("RELEASES.md").read_text(encoding="utf-8")

    app_version = re.search(r'^__version__ = "([0-9]+\.[0-9]+\.[0-9]+)"$', app_source, re.MULTILINE)
    assert app_version is not None
    assert version == app_version.group(1) == "4.9.2"

    assert 'MARZBAN_GITHUB_BRANCH="${MARZBAN_GITHUB_BRANCH:-master}"' in installer
    assert 'MARZBAN_DOCKER_IMAGE="${MARZBAN_DOCKER_IMAGE:-ghcr.io/smorad3363/marzban}"' in installer
    assert 'target_image=$(marzban_docker_image "$requested_version")' in installer
    assert 'update_command --version "$1"' in installer
    assert 'tags:' in workflow and '- "v*"' in workflow
    assert '${IMAGE_NAME}:${VERSION_TAG}' in workflow
    assert 'gh release create "${VERSION_TAG}"' in workflow

    assert "install --version v4.9.2 --database mysql" in release_docs
    assert "install --version v4.8.0 --database mysql" in release_docs
    assert "marzban rollback v4.8.0" in release_docs
