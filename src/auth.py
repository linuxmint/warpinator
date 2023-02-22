#!/usr/bin/python3

import datetime
import stat
import os
from pathlib import Path
import secrets
import logging
import ipaddress

from cryptography import x509
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.x509.oid import NameOID
import nacl
from nacl import secret
import hashlib
import base64

from gi.repository import GLib, GObject

import util
import prefs

day = datetime.timedelta(1, 0, 0)
EXPIRE_TIME = 30 * day

singleton = None

def get_singleton():
    global singleton

    if singleton is None:
        singleton = AuthManager()

    return singleton

class AuthManager(GObject.Object):
    __gsignals__ = {
        'group-code-changed': (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self):
        GObject.Object.__init__(self)
        self.hostname = util.get_hostname()
        self.ip_info = None
        self.port = None

        self.private_key = None
        self.server_cert = None

        self.remote_certs = {}

        prefs.prefs_settings.connect("changed::group-code", self.notify_group_code_changed)

    def notify_group_code_changed(self, settings, key, data=None):
        self.emit("group-code-changed")

    def update(self, ip_info, port):
        self.ip_info = ip_info;
        self.port = port

        self._make_key_cert_pair()

    def get_server_creds(self):
        return (self.server_private_key, self.server_pub_key)

    def get_cached_cert(self, hostname, ip_info):
        try:
            return self.remote_certs["%s.%s" % (hostname, ip_info.ip4_address)]
        except KeyError:
            return None

    def process_remote_cert(self, hostname, ip_info, server_data):
        if server_data is None:
            return False
        decoded = base64.decodebytes(server_data)

        hasher = hashlib.sha256()
        hasher.update(bytes(prefs.get_group_code(), "utf-8"))
        key = hasher.digest()
        decoder = secret.SecretBox(key)

        try:
            cert = decoder.decrypt(decoded)
        except nacl.exceptions.CryptoError as e:
            logging.debug("Decryption failed for remote '%s': %s" % (hostname, str(e)))
            cert = None

        if cert:
            self.remote_certs["%s.%s" % (hostname, ip_info.ip4_address)] = cert
            return True
        else:
            return False

    def get_encoded_local_cert(self):
        hasher = hashlib.sha256()
        hasher.update(bytes(prefs.get_group_code(), "utf-8"))
        key = hasher.digest()

        encoder = secret.SecretBox(key)

        encrypted = encoder.encrypt(self.server_pub_key)
        encoded = base64.encodebytes(encrypted)
        return encoded

    def _make_key_cert_pair(self):
        logging.debug("Auth: Creating server credentials")

        private_key = rsa.generate_private_key(
            backend=crypto_default_backend(),
            public_exponent=65537,
            key_size=2048
        )

        public_key = private_key.public_key()

        builder = x509.CertificateBuilder()
        builder = builder.subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, self.hostname),
        ]))
        builder = builder.issuer_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, self.hostname),
        ]))
        builder = builder.not_valid_before(datetime.datetime.today() - day)
        builder = builder.not_valid_after(datetime.datetime.today() + EXPIRE_TIME)
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.public_key(public_key)

        alt_names = []

        if self.ip_info.ip4_address is not None:
            alt_names.append(x509.IPAddress(ipaddress.IPv4Address(self.ip_info.ip4_address)))

        builder = builder.add_extension(x509.SubjectAlternativeName(alt_names), critical=True)

        certificate = builder.sign(
            private_key=private_key, algorithm=hashes.SHA256(),
            backend=crypto_default_backend()
        )

        ser_private_key = private_key.private_bytes(
            crypto_serialization.Encoding.PEM,
            crypto_serialization.PrivateFormat.PKCS8,
            crypto_serialization.NoEncryption())

        ser_public_key = certificate.public_bytes(
            crypto_serialization.Encoding.PEM
        )

        self.server_pub_key = ser_public_key
        self.server_private_key = ser_private_key
