from pydantic import BaseModel, Field


class OpenVPNPkiResponse(BaseModel):
    ca_cert: str
    ca_key: str
    server_cert: str
    server_key: str
    tls_crypt_key: str


class OpenVPNPkiRequest(BaseModel):
    ca_common_name: str = Field(default="HPXPANEL-OpenVPN-CA", max_length=128)
    server_common_name: str = Field(default="openvpn-server", max_length=128)
