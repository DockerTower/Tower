from sh import git
from core.git.repo import Repo


class Git(object):
    def __init__(self, auth=None):
        self.auth = auth

    @classmethod
    def clone(cls, repository, path):
        return git.clone(repository, path, '--progress', '--recursive', _err_to_out=True, _iter=True)

    @classmethod
    def clone_branch(cls, repository, path, branch):
        return git.clone("-b", branch, repository, path, '--progress', '--recursive', _err_to_out=True, _iter=True)

    @classmethod
    def repo(cls, path):
        return Repo(path)
