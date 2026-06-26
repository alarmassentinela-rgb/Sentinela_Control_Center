# -*- coding: utf-8 -*-
"""Centro de dispositivos confiables (W5.9)."""
from ..models import Device, PortalSession
from . import session_service


def list_devices(db, identity_id):
    return (db.query(Device).filter_by(identity_id=identity_id)
            .order_by(Device.last_seen.desc()).all())


def set_trust(db, identity_id, device_pk, trusted):
    d = db.query(Device).filter_by(id=device_pk, identity_id=identity_id).one_or_none()
    if not d:
        return None
    d.trusted = trusted
    db.flush()
    return d


def remove_device(db, odoo, identity_id, device_pk):
    d = db.query(Device).filter_by(id=device_pk, identity_id=identity_id).one_or_none()
    if not d:
        return False
    # revoca todas las sesiones de ese dispositivo
    for s in (db.query(PortalSession)
              .filter_by(identity_id=identity_id, device_id=d.device_id, revoked=False).all()):
        session_service.revoke_session(db, odoo, s, event="revoke_device")
    db.delete(d)
    db.flush()
    return True


def serialize_device(d):
    return {
        "id": d.id, "device_id": d.device_id, "label": d.label, "trusted": d.trusted,
        "first_seen": d.first_seen.isoformat() if d.first_seen else None,
        "last_seen": d.last_seen.isoformat() if d.last_seen else None,
        "last_ip": d.last_ip,
    }
