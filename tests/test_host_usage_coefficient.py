"""Host / config traffic coefficient models and helpers."""

from app.models.host import ApplyHostCoefficientRequest, BaseHost, UserHostCoefficientUpsert


def test_base_host_default_usage_coefficient():
    host = BaseHost(remark="FI-STUN", address={"fi.example.com"}, priority=0)
    assert host.usage_coefficient == 1.0


def test_base_host_custom_usage_coefficient():
    host = BaseHost(remark="DE-TUN", address={"de.example.com"}, priority=1, usage_coefficient=10)
    assert host.usage_coefficient == 10


def test_user_host_coefficient_upsert_requires_positive():
    item = UserHostCoefficientUpsert(username="alice", usage_coefficient=2.5)
    assert item.username == "alice"
    assert item.usage_coefficient == 2.5


def test_apply_host_coefficient_request_optional():
    body = ApplyHostCoefficientRequest()
    assert body.usage_coefficient is None
    body2 = ApplyHostCoefficientRequest(usage_coefficient=5)
    assert body2.usage_coefficient == 5
