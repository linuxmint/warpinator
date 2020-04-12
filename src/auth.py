import datetime
import stat
import os

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

from gi.repository import GLib, GObject, Gio

import util

day = datetime.timedelta(1, 0, 0)
EXPIRE_TIME = 30 * day

DEFAULT_GROUP_CODE = "Warpinator"
KEYFILE_GROUP_NAME = "warp"
KEYFILE_CODE_KEY = "code"
CODEFILE_NAME = ".group"

CONFIG_FOLDER = os.path.join(GLib.get_user_config_dir(), "warp")
CERT_FOLDER = os.path.join(CONFIG_FOLDER, "remotes")

os.makedirs(CERT_FOLDER, 0o700, exist_ok=True)

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
        self.code = None

        self.keyfile = GLib.KeyFile()

        try:
            self.keyfile.load_from_file(os.path.join(CONFIG_FOLDER, CODEFILE_NAME), GLib.KeyFileFlags.NONE)
        except GLib.Error as e:
            if e.code == GLib.FileError.NOENT:
                print("No group code file, making one.")
                pass
            else:
                print("Could not load existing settings: %s" % e.message)

        self.code = self.get_group_code()


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

    def load_cert(self, hostname):
        path = os.path.join(CERT_FOLDER, hostname + ".pem")
        return self._load_bytes(path)

    def save_cert(self, hostname, cert_bytes):
        path = os.path.join(CERT_FOLDER, hostname + ".pem")

        self._save_bytes(path, cert_bytes)

    def load_private_key(self):
        path = os.path.join(CERT_FOLDER, self.hostname + "-key.pem")

        return self._load_bytes(path)

    def save_private_key(self, key_bytes):
        path = os.path.join(CERT_FOLDER, self.hostname + "-key.pem")

        self._save_bytes(path, key_bytes)

    def make_key_cert_pair(self, hostname, ip):
        private_key = rsa.generate_private_key(
            backend=crypto_default_backend(),
            public_exponent=65537,
            key_size=2048
        )

        public_key = private_key.public_key()

        builder = x509.CertificateBuilder()
        builder = builder.subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        ]))
        builder = builder.issuer_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        ]))
        builder = builder.not_valid_before(datetime.datetime.today() - day)
        builder = builder.not_valid_after(datetime.datetime.today() + EXPIRE_TIME)
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.public_key(public_key)
        builder = builder.add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName(ip)]
            ),
            critical=True
        )

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

        return ser_private_key, ser_public_key

    def lookup_single_by_oid(self, name_attrs, oid):
        res = name_attrs.get_attributes_for_oid(oid)

        if res and res[0]:
            return res[0].value

        return None

    def ip_and_hostname_matches_certificate(self, hostname, ip, data):
        cert_ip = None
        backend = crypto_default_backend()
        instance = x509.load_pem_x509_certificate(data, backend)

        issuer = self.lookup_single_by_oid(instance.issuer, x509.NameOID.COMMON_NAME)
        subject = self.lookup_single_by_oid(instance.subject, x509.NameOID.COMMON_NAME)
        if issuer != subject:
            return False

        for ext in instance.extensions:
            if isinstance(ext.value, x509.SubjectAlternativeName):
                for item in ext.value:
                    if isinstance(item, x509.DNSName):
                        cert_ip = item.value

        return issuer == hostname and cert_ip == ip

    def get_server_creds(self):
        key = self.load_private_key()
        cert = self.load_cert(util.get_hostname())

        if (key != None and cert != None) and self.ip_and_hostname_matches_certificate(self.hostname,
                                                                                       util.get_ip(),
                                                                                       cert):
            print("Using existing server credentials")
            return (key, cert)

        print("Creating server credentials")
        key, cert = self.make_key_cert_pair(self.hostname, util.get_ip())

        try:
            self.save_private_key(key)
            self.save_cert(self.hostname, cert)
        except OSError as e:
            print("Unable to save new server key and/or certificate: %s" % e)

        return (key, cert)

    def get_boxed_server_cert(self):
        hasher = hashlib.sha256()
        hasher.update(self.get_group_code())
        key = hasher.digest()

        encoder = secret.SecretBox(key)

        encrypted = encoder.encrypt(self.load_cert(self.hostname))
        return encrypted

    def unbox_server_cert(self, box):
        hasher = hashlib.sha256()
        hasher.update(self.get_group_code())
        key = hasher.digest()
        decoder = secret.SecretBox(key)

        try:
            cert = decoder.decrypt(box)
        except nacl.exceptions.CryptoError as e:
            print(e)
            return None

        return cert

    def get_group_code(self):
        path = os.path.join(CONFIG_FOLDER, ".groupcode")

        code = DEFAULT_GROUP_CODE

        try:
            code = self.keyfile.get_string(KEYFILE_GROUP_NAME, KEYFILE_CODE_KEY)
        except GLib.Error as e:
            if e.code not in (GLib.KeyFileError.KEY_NOT_FOUND, GLib.KeyFileError.GROUP_NOT_FOUND):
                print("Could not read group code from settings file: %s" % e.message)
            self.save_group_code(DEFAULT_GROUP_CODE)

        if code == "":
            print ("Settings file contains no code, setting to default")
            self.save_group_code(DEFAULT_GROUP_CODE)

        if len(code) < 8:
            print("******** Group Code is short, consider something longer than 8 characters.")

        return bytes(code, "utf-8")

    def save_group_code(self, code):
        if bytes(code, "utf-8") == self.code:
            return

        self.keyfile.set_string(KEYFILE_GROUP_NAME, KEYFILE_CODE_KEY, code)

        path = os.path.join(CONFIG_FOLDER, CODEFILE_NAME)

        self.code = bytes(code,  "utf-8")
        keyfile_bytes = bytes(self.keyfile.to_data()[0], "utf-8")

        self._save_bytes(path, keyfile_bytes)
        self.get_server_creds()
        self.emit("group-code-changed")

    def process_remote_cert_b64_dict(self, hostname, zc_dict):
        box = b''
        x = 0
        while zc_dict[str(x).encode()] != False:
            box += zc_dict[str(x).encode()] + b'\n'
            x += 1

        box = box.replace(b"*", b"=") # zeroconf uses = as a delimiter
        decoded = base64.decodebytes(box)

        cert = self.unbox_server_cert(decoded)

        if cert:
            self.save_cert(hostname, cert)
            return True
        else:
            return False

    def get_server_cert_b64_dict(self):
        box = self.get_boxed_server_cert()

        encoded = base64.encodebytes(box)
        encoded =  encoded.replace(b"=", b"*") # zeroconf uses = as a delimiter
        encoded_list = encoded.split(b'\n')

        zc_dict = {}
        x = 0

        for line in encoded_list:
            zc_dict[str(x).encode()] = line
            x += 1

        return zc_dict

if __name__ == "__main__":
    a = AuthManager()

    a.get_server_creds()