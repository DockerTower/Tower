import json
from sh import git, tr
from src.core.git.commit import Commit


class Repo(object):
    GIT_LOG_FORMAT = '''
    "%H": {
        "commit": "%H",
        "abbreviated_commit": "%h",
        "tree": "%T",
        "abbreviated_tree": "%t",
        "parent": "%P",
        "abbreviated_parent": "%p",
        "refs": "%D",
        "encoding": "%e",
        "subject": "%s",
        "sanitized_subject_line": "%f",
        "body": "%b",
        "commit_notes": "%N",
        "verification_flag": "%G?",
        "signer": "%GS",
        "signer_key": "%GK",
        "author": {
            "name": "%aN",
            "email": "%aE",
            "date": "%aD"
        },
        "commiter": {
            "name": "%cN",
            "email": "%cE",
            "date": "%cD"
        }
    },
    '''

    def __init__(self, path):
        self.path = path + "/.git"
        self.git = git.bake("--git-dir", self.path, "--work-tree", path, "--no-pager")

    @property
    def commits(self):
        commits = self.git.log('--pretty=format:' + Repo.GIT_LOG_FORMAT)
        commits = json.loads("{" + repr(commits).strip()[:-1] + "}")
        commit_list = {}

        for commit_hash, commit in commits.items():
            commit_list[commit_hash] = Commit(commit)

        return commit_list

    def switch_branch(self, branch):
        return self.git.checkout("-f", branch, _err_to_out=True, _iter=True)

    def create_branch(self, branch, tag=""):
        return self.git.checkout("-b", branch, tag, _err_to_out=True, _iter=True)

    def pull_from_branch(self, origin="origin", branch="master"):
        return self.git.pull(origin, branch, _err_to_out=True, _iter=True)

    def get_refs(self, origin="origin", branch="master"):
        return self.git.pull('{branch}:refs/remotes/{origin}/{branch}'.format(origin=origin, branch=branch),
                             _err_to_out=True, _iter=True)

    def pull(self, origin="origin", branch="master"):
        return self.git.pull(origin, branch, _err_to_out=True, _iter=True)

    def fetch(self, origin="origin", branch="master"):
        return self.git.fetch(origin, branch, _err_to_out=True, _iter=True)

    def remotes(self):
        return self.git("ls-remote", _err_to_out=True, _iter=True)

    def get_last_commit_id(self, commit_format="%h"):
        return self.git.log('--format="{format}"'.format(commit_format=commit_format), n='1')

    def git_log(self):
        clone = self.git.clone(
            '--pretty=format:' + Repo.GIT_LOG_FORMAT,
            '--progress',
            '--recursive',
            _err_to_out=True, _iter=True, _out_bufsize=100
        )
        for line in clone:
            print(line)

    def get_last_tag(self):
        return repr(
            self.git.describe('--tags', tr("-d", "'\n'", _in=self.git("rev-list", "--tags", "--max-count", 1)))).strip()
