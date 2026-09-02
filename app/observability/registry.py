from prometheus_client import CollectorRegistry

_REGISTRY = CollectorRegistry(auto_describe=True)


def get_registry() -> CollectorRegistry:
    return _REGISTRY
