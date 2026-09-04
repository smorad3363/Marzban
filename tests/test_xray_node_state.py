from unittest.mock import Mock

from app.xray.node import ReSTXRayNode


def test_remote_started_probe_synchronizes_local_api_state(monkeypatch):
    node = ReSTXRayNode.__new__(ReSTXRayNode)
    node.address = "node.test"
    node.api_port = 62051
    node._node_cert = "certificate"
    node._session_id = "session"
    node._started = False
    node._api = None
    node.make_request = Mock(return_value={"started": True})
    api = Mock()
    monkeypatch.setattr("app.xray.node.XRayAPI", Mock(return_value=api))

    assert node.started is True
    assert node.api is api
    assert node._started is True


def test_remote_stopped_probe_clears_stale_api():
    node = ReSTXRayNode.__new__(ReSTXRayNode)
    node._started = True
    node._api = Mock()
    node.make_request = Mock(return_value={"started": False})

    assert node.started is False
    assert node._started is False
    assert node._api is None
