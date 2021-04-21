import datetime
import stat
import os
import uuid
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

singleton = None

def get_singleton():
    global singleton

    if singleton == None:
        singleton = AuthManager()

    return singleton

class AuthManager(GObject.Object):
    __gsignals__ = {
        'group-code-changed': (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self):
        GObject.Object.__init__(self)
        self.hostname = util.get_hostname()
        self.ident = None
        self.ips = None
        self.port = None
        self.code = None

        self.private_key = None
        self.server_cert = None

        self.remote_certs = {}

        self.keyfile = GLib.KeyFile()

    def update(self, ips, port):
        self.ips = ips
        self.port = port

        try:
            self.keyfile.load_from_file(os.path.join(CONFIG_FOLDER, CONFIG_FILE_NAME), GLib.KeyFileFlags.NONE)
        except GLib.Error as e:
            if e.code == GLib.FileError.NOENT:
                logging.debug("Auth: No group code file, making one.")
                pass
            else:
                logging.debug("Auth: Could not load existing keyfile (%s): %s" %(CONFIG_FOLDER, e.message))

        self.ident = self.get_ident()
        self.code = self.get_group_code()

        self.make_key_cert_pair()

    def _save_bytes(self, path, file_bytes):
        try:
            os.remove(path)
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
            f.write(file_bytes)

    def _load_bytes(self, path):
        ret = None

        try:
            with open(path, "rb") as f:
                ret = f.read()
        except FileNotFoundError:
            pass

        return ret

    def get_ident(self):
        if self.ident != None:
            return self.ident

        try:
            self.ident = self.keyfile.get_string(KEYFILE_GROUP_NAME, KEYFILE_UUID_KEY)
        except GLib.Error as e:
            if e.code not in (GLib.KeyFileError.KEY_NOT_FOUND, GLib.KeyFileError.GROUP_NOT_FOUND):
                logging.critical("Could not read group code from settings file: %s" % e.message)

            self.ident = str(uuid.uuid4())
            self.keyfile.set_string(KEYFILE_GROUP_NAME, KEYFILE_UUID_KEY, self.ident)

            path = os.path.join(CONFIG_FOLDER, CONFIG_FILE_NAME)

            keyfile_bytes = bytes(self.keyfile.to_data()[0], "utf-8")

            self._save_bytes(path, keyfile_bytes)

        return self.ident

    def get_group_code(self):
        code = DEFAULT_GROUP_CODE

        try:
            code = self.keyfile.get_string(KEYFILE_GROUP_NAME, KEYFILE_CODE_KEY)
        except GLib.Error as e:
            if e.code not in (GLib.KeyFileError.KEY_NOT_FOUND, GLib.KeyFileError.GROUP_NOT_FOUND):
                logging.warn("Could not read group code from settings file (%s): %s" % (CONFIG_FOLDER, e.message))
            self.save_group_code(DEFAULT_GROUP_CODE)

        if code == "":
            logging.warn("Settings file contains no code, setting to default (%s)" % CONFIG_FOLDER)
            self.save_group_code(DEFAULT_GROUP_CODE)

        if len(code) < 8:
            logging.warn("Group Code is short, consider something longer than 8 characters.")

        return bytes(code, "utf-8")

    def save_group_code(self, code):
        if bytes(code, "utf-8") == self.code:
            return

        self.keyfile.set_string(KEYFILE_GROUP_NAME, KEYFILE_CODE_KEY, code)

        path = os.path.join(CONFIG_FOLDER, CONFIG_FILE_NAME)

        self.code = bytes(code,  "utf-8")
        keyfile_bytes = bytes(self.keyfile.to_data()[0], "utf-8")

        self._save_bytes(path, keyfile_bytes)
        self.emit("group-code-changed")

    def make_key_cert_pair(self):
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

        if self.ips.ip4 != None:
            alt_names.append(x509.IPAddress(ipaddress.IPv4Address(self.ips.ip4)))
        if self.ips.ip6 != None:
            alt_names.append(x509.IPAddress(ipaddress.IPv6Address(self.ips.ip6)))

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

    def get_server_creds(self):
        return (self.server_private_key, self.server_pub_key)

    def load_cert(self, hostname, ips):
        try:
            return self.remote_certs["%s.%s" % (hostname, ips)]
        except KeyError:
            return None

    def process_remote_cert(self, hostname, ips, server_data):
        if server_data == None:
            return False
        decoded = base64.decodebytes(server_data)

        hasher = hashlib.sha256()
        hasher.update(self.code)
        key = hasher.digest()
        decoder = secret.SecretBox(key)

        try:
            cert = decoder.decrypt(decoded)
        except nacl.exceptions.CryptoError as e:
            print(e)
            cert = None

        if cert:
            self.remote_certs["%s.%s" % (hostname, ips)] = cert
            return True
        else:
            return False

    def get_encoded_local_cert(self):
        hasher = hashlib.sha256()
        hasher.update(self.code)
        key = hasher.digest()

        encoder = secret.SecretBox(key)

        encrypted = encoder.encrypt(self.server_pub_key)
        encoded = base64.encodebytes(encrypted)
        return encoded
