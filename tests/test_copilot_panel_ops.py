from app.db.models import NodeStatus
from app.models.node import NodeResponse
from app.services.copilot.panel_ops import diagnose_node_record


def _node(**kwargs) -> NodeResponse:
    base = {
        "id": 1,
        "name": "test-node",
        "address": "1.2.3.4",
        "port": 62050,
        "api_port": 62051,
        "usage_coefficient": 1.0,
        "connection_type": "grpc",
        "server_ca": "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----",
        "keep_alive": 60,
        "core_config_id": 1,
        "api_key": "00000000-0000-0000-0000-000000000001",
        "status": NodeStatus.connected,
        "message": "",
        "xray_version": "1.8.0",
        "node_version": "1.0.0",
    }
    base.update(kwargs)
    return NodeResponse.model_validate(base)


def test_diagnose_node_record_healthy_when_connected():
    result = diagnose_node_record(
        _node(),
        realtime={"cpu_usage": 10, "mem_total": 1000, "mem_used": 100},
        outbounds=[{"name": "direct", "alive": True}],
    )
    assert result["healthy"] is True
    assert result["issues"] == []


def test_diagnose_node_record_flags_error_status():
    result = diagnose_node_record(_node(status=NodeStatus.error, message="API timeout"))
    assert result["healthy"] is False
    assert any("error" in issue.lower() for issue in result["issues"])
    assert result["suggestions"]
