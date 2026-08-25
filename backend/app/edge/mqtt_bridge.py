from __future__ import annotations

import json
import logging
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.schemas.maintenance import EdgeSignalEnvelope
from app.core.config import get_settings

logger = logging.getLogger("nexora.mqtt_bridge")


def decode_message(topic: str, payload: bytes) -> EdgeSignalEnvelope:
    parts = topic.split("/")
    if len(parts) != 4 or parts[0] != "nexora" or parts[1] != "machines" or parts[3] != "signal-windows":
        raise ValueError("Topic must match nexora/machines/{machine_id}/signal-windows.")
    body = json.loads(payload.decode("utf-8"))
    body["machine_id"] = parts[2]
    return EdgeSignalEnvelope.model_validate(body)


def forward_envelope(envelope: EdgeSignalEnvelope, api_url: str, edge_token: str | None, timeout_seconds: float = 15) -> dict:
    headers = {"Content-Type": "application/json"}
    if edge_token:
        headers["X-Nexora-Edge-Token"] = edge_token
    request = Request(f"{api_url.rstrip('/')}/api/edge/signal-windows", data=envelope.model_dump_json().encode("utf-8"), headers=headers, method="POST")
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise SystemExit("Install backend requirements to run the MQTT bridge (paho-mqtt is required).") from exc
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=settings.mqtt_client_id)
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
    if settings.mqtt_tls:
        client.tls_set(ca_certs=settings.mqtt_ca_file, cert_reqs=ssl.CERT_REQUIRED)

    def on_connect(active_client, _userdata, _flags, reason_code, _properties):
        if reason_code != 0:
            logger.error("mqtt_connection_failed reason=%s", reason_code)
            return
        active_client.subscribe(settings.mqtt_topic, qos=1)
        logger.info("mqtt_subscribed topic=%s", settings.mqtt_topic)

    def on_message(_client, _userdata, message):
        try:
            envelope = decode_message(message.topic, message.payload)
            result = forward_envelope(envelope, settings.api_url, settings.edge_ingest_token)
            logger.info("edge_window_ingested message_id=%s signal_window_id=%s", envelope.message_id, result["id"])
        except (ValueError, json.JSONDecodeError, HTTPError, URLError, TimeoutError, KeyError) as exc:
            logger.error("edge_message_rejected topic=%s error=%s", message.topic, exc)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
