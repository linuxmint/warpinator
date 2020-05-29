import datetime
import threading
import stat
import os
import socket
import uuid
import logging

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

REQUEST = b"REQUEST"


day = datetime.timedelta(1, 0, 0)
EXPIRE_TIME = 30 * day

DEFAULT_GROUP_CODE = "Warpinator"
KEYFILE_GROUP_NAME = "warpinator"
KEYFILE_CODE_KEY = "code"
KEYFILE_UUID_KEY = "connect_id"
CONFIG_FILE_NAME = ".group"

CONFIG_FOLDER = os.path.join(GLib.get_user_config_dir(), "warpinator")
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
        self.ident = None

        self.cert_server = None
        self.requests_lock = threading.Lock()
        self.requests = {}

        self.clean_cert_folder()

        self.keyfile = GLib.KeyFile()

        try:
            self.keyfile.load_from_file(os.path.join(CONFIG_FOLDER, CONFIG_FILE_NAME), GLib.KeyFileFlags.NONE)
        except GLib.Error as e:
            if e.code == GLib.FileError.NOENT:
                logging.debug("No group code file, making one.")
                pass
            else:
                logging.debug("Could not load existing keyfile (%s): %s" %(CONFIG_FOLDER, e.message))

        self.code = self.get_group_code()

    def restart_cert_server(self):
        if self.cert_server != None:
            self.cert_server.stop()

        self.cert_server = CertServer()

    def shutdown(self):
        if self.cert_server != None:
            self.cert_server.stop()

        self.clean_cert_folder()

        for key in self.requests.keys():
            self.requests[key].cancel()

    def clean_cert_folder(self):
        for filename in os.listdir(CERT_FOLDER):
            path = os.path.join(CERT_FOLDER, filename)

            try:
                os.unlink(path)
            except Exception as e:
                logging.critical("Cannot delete item in remote cert folder (%s): %s" % (CERT_FOLDER, e))

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

    def load_cert(self, hostname, ip):
        path = os.path.join(CERT_FOLDER, "%s.%s.pem" % (hostname, ip))
        return self._load_bytes(path)

    def save_cert(self, hostname, ip, cert_bytes):
        path = os.path.join(CERT_FOLDER, "%s.%s.pem" % (hostname, ip))

        self._save_bytes(path, cert_bytes)

    def load_server_cert(self):
        path = os.path.join(CERT_FOLDER, "%s.pem" % (util.get_hostname(),))
        return self._load_bytes(path)

    def save_server_cert(self, cert_bytes):
        path = os.path.join(CERT_FOLDER, "%s.pem" % (util.get_hostname(),))

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

    def get_server_creds(self):
        logging.debug("Creating server credentials")
        key, cert = self.make_key_cert_pair(self.hostname, util.get_ip())

        try:
            self.save_private_key(key)
            self.save_server_cert(cert)
        except OSError as e:
            logging.critical("Unable to save new server key and/or certificate: %s" % e)

        return (key, cert)

    def get_boxed_server_cert(self):
        hasher = hashlib.sha256()
        hasher.update(self.get_group_code())
        key = hasher.digest()

        encoder = secret.SecretBox(key)

        encrypted = encoder.encrypt(self.load_server_cert())
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

    def process_encoded_server_cert(self, hostname, ip, server_data):
        if server_data == None:
            return False
        decoded = base64.decodebytes(server_data)
        cert = self.unbox_server_cert(decoded)

        if cert:
            self.save_cert(hostname, ip, cert)
            return True
        else:
            return False

    def get_encoded_server_cert(self):
        box = self.get_boxed_server_cert()

        encoded = base64.encodebytes(box)
        return encoded

    def retrieve_remote_cert(self, ident, hostname, ip, port):
        logging.debug("Starting a new RequestLoop for '%s' (%s:%d)" % (hostname, ip, port))
        with self.requests_lock:
            req = RequestLoop(ip, port)

            self.requests[ident] = req

        data = req.request()

        with self.requests_lock:
            del self.requests[ident]

        logging.debug("RequestLoop complete for '%s' (%s:%d): got cert? %s" % (hostname, ip, port, "Yes" if data else "No"))

        if data == None:
            return False

        return self.process_encoded_server_cert(hostname, ip, data)

    def cancel_request_loop(self, ident):
        req = None

        with self.requests_lock:
            try:
                req = self.requests[ident]
            except KeyError:
                pass

        if req:
            req.cancel()

############################ Getting server certificate via udp after discovery ###########

class RequestLoop():
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

        self.timer = threading.Event()

    def request(self):
        while not self.timer.is_set():
            logging.debug("Requesting cert from remote (%s:%d)" % (self.ip, self.port))
            try_count = 0

            while try_count < 3:
                try:
                    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    server_sock.settimeout(1.0)
                    server_sock.sendto(REQUEST, (self.ip, self.port))

                    reply, addr = server_sock.recvfrom(2000)

                    if addr == (self.ip, self.port):
                        return reply
                except socket.timeout:
                    try_count += 1
                    continue
                except socket.error as e:
                    logging.critical("Something wrong with cert request (%s:%s): " % (self.ip, self.port, e))
                    break

            logging.debug("Cert request failed from remote (%s:%d), waiting 30s to try again. (Is their udp port blocked?"
                              % (self.ip, self.port))
            self.timer.wait(30)

        logging.debug("RequestLoop canceled (event set) for (%s:%s)" % (self.ip, self.port))
        return None

    def cancel(self):
        self.timer.set()

class CertServer():
    def __init__(self):
        logging.debug("Starting local cert server")
        self.exit = False

        self.thread = threading.Thread(target=self.serve_cert_thread)
        self.thread.start()

    def serve_cert_thread(self):
        try:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server_sock.settimeout(1.0)
            server_sock.bind((util.get_ip(), prefs.get_port()))
        except socket.error as e:
            logging.critical("Could not create udp socket for cert requests: %s" % str(e))
            return

        while True:
            try:
                data, address = server_sock.recvfrom(2000)

                if data == REQUEST:
                    cert_data = get_singleton().get_encoded_server_cert()
                    server_sock.sendto(cert_data, address)
            except socket.timeout as e:
                if self.exit:
                    server_sock.close()
                    break

    def stop(self):
        self.exit = True
        self.thread.join()

