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

DEFAULT_GROUP_CODE = "Warpinator"
KEYFILE_GROUP_NAME = "warpinator"
KEYFILE_CODE_KEY = "code"
KEYFILE_UUID_KEY = "connect_id"
CONFIG_FILE_NAME = ".group"

CONFIG_FOLDER = os.path.join(GLib.get_user_config_dir(), "warpinator")
os.makedirs(CONFIG_FOLDER, exist_ok=True)

singleton = None
keyfile = None

def get_singleton():
    global singleton

    if singleton is None:
        singleton = AuthManager()

    return singleton

def _ensure_keyfile_loaded():
    global keyfile

    if keyfile is not None:
        return

    path = Path(os.path.join(CONFIG_FOLDER, CONFIG_FILE_NAME))
    keyfile = GLib.KeyFile()

    try:
        keyfile.load_from_file(path.as_posix(), GLib.KeyFileFlags.NONE)
    except GLib.Error as e:
        if e.code == GLib.FileError.NOENT:
            logging.debug("Auth: No group code file, making one.")
            path.touch()
        else:
            logging.debug("Auth: Could not load existing keyfile (%s): %s" %(CONFIG_FOLDER, e.message))
            path.unlink()
            path.touch()

def _save_keyfile():
    _ensure_keyfile_loaded()
    global keyfile

    keyfile_bytes = bytes(keyfile.to_data()[0], "utf-8")

    path = Path(os.path.join(CONFIG_FOLDER, CONFIG_FILE_NAME))

    try:
        path.unlink()
    except OSError:
        pass

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    mode = stat.S_IRUSR | stat.S_IWUSR
    umask = 0o777 ^ mode  # Prevents always downgrading umask to 0.

    umask_original = os.umask(umask)

    try:
        fdesc = os.open(path, flags, mode)
    finally:
        os.umask(umask_original)

    with os.fdopen(fdesc, 'wb') as f:
        f.write(keyfile_bytes)

def get_group_code():
    reset = False
    code = None

    _ensure_keyfile_loaded()
    global keyfile

    try:
        code = keyfile.get_string(KEYFILE_GROUP_NAME, KEYFILE_CODE_KEY)
    except GLib.Error as e:
        if e.code not in (GLib.KeyFileError.KEY_NOT_FOUND, GLib.KeyFileError.GROUP_NOT_FOUND):
            logging.warn("Could not read group code from settings file (%s): %s" % (CONFIG_FOLDER, e.message))

    if code is None or code == "":
        code = DEFAULT_GROUP_CODE
        _save_keyfile()
        return code

    if len(code) < 4:
        logging.warn("Group Code is short, consider something longer than 8 characters.")

    return code

def get_secure_mode():
    return get_group_code() != DEFAULT_GROUP_CODE

class AuthManager(GObject.Object):
    __gsignals__ = {
        'group-code-changed': (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self):
        GObject.Object.__init__(self)
        self.hostname = util.get_hostname()
        self.ident = ""
        self.ip_info = None
        self.port = None
        self.code = ""

        self.private_key = None
        self.server_cert = None

        self.remote_certs = {}

    def update(self, ip_info, port):
        self.ip_info = ip_info;
        self.port = port

        self._read_ident()
        self.code = get_group_code()
        self._make_key_cert_pair()

    def get_ident(self):
        return self.ident

    def update_group_code(self, code):
        if code == self.code:
            return

        _ensure_keyfile_loaded()

        self.code = code
        keyfile.set_string(KEYFILE_GROUP_NAME, KEYFILE_CODE_KEY, code)
        _save_keyfile()

        self.emit("group-code-changed")

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
        hasher.update(bytes(self.code, "utf-8"))
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
        hasher.update(bytes(self.code, "utf-8"))
        key = hasher.digest()

        encoder = secret.SecretBox(key)

        encrypted = encoder.encrypt(self.server_pub_key)
        encoded = base64.encodebytes(encrypted)
        return encoded

    def _read_ident(self):
        gen_new = False

        _ensure_keyfile_loaded()
        global keyfile

        try:
            self.ident = keyfile.get_string(KEYFILE_GROUP_NAME, KEYFILE_UUID_KEY)
        except GLib.Error as e:
            if e.code not in (GLib.KeyFileError.KEY_NOT_FOUND, GLib.KeyFileError.GROUP_NOT_FOUND):
                logging.critical("Could not read uuid (ident) from settings file: %s" % e.message)

            gen_new = True

        if len(self.ident.split("-")) == 5:
            gen_new = True

        if gen_new:
            # Max 'instance' length is 63.
            # https://datatracker.ietf.org/doc/html/rfc6763#section-7.2
            self.ident = "%s-%s" % (self.hostname.upper()[:42], secrets.token_hex(10).upper())
            keyfile.set_string(KEYFILE_GROUP_NAME, KEYFILE_UUID_KEY, self.ident)
            _save_keyfile()

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
