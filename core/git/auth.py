from io import StringIO
from os import path


class Auth(object):

    def __init__(self, pkey):
        self.pkey = self.setup_pkey(pkey)

    def setup_pkey(self, pkey):
        if isinstance(pkey, str):
            if path.exists(pkey):
                pkey_file = open(pkey)
            else:
                pkey_file = StringIO(pkey)
        else:
            return pkey

        return pkey_file

