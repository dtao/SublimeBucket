import os
import re
import sublime
import sublime_plugin
import subprocess
import traceback
import webbrowser
from urllib.parse import urljoin

TEXT_ENCODING = 'utf-8'


def load_settings():
    return sublime.load_settings('Bitbucket.sublime-settings')


class CommandBase():
    def get_backend(self):
        """Get the backend (Git or Mercurial) for the current project.
        """
        working_directory = self.get_directory()
        for backend in [GitBackend, MercurialBackend]:
            try:
                subprocess.check_output('%s status' % backend.command,
                                        cwd=working_directory, shell=True)
                return backend(working_directory)
            except subprocess.CalledProcessError:
                pass

        raise SublimeBucketError('Unable to find a Git/Hg repository')

    def get_issue_trackers(self):
        settings = load_settings()
        return [self._create_issue_tracker(config)
                for config in settings.get('issue_trackers', [])]

    def get_directory(self):
        """Get the open directory containing the current file.
        """
        full_path = self.view.file_name()
        for folder in self.view.window().folders():
            if full_path.startswith(folder):
                return folder

    def get_file_path(self):
        """Get the path to the current file, relative to the repository root.
        """
        return os.path.relpath(self.view.file_name(), self.get_directory())

    def get_line_ranges(self):
        """Get the list of currently selected line ranges, in start:end format.
        """
        ranges = []

        for region in self.view.sel():
            # Sublime provides 0-based line numbers but Bitbucket line numbers
            # start with 1.
            first_line = self.view.rowcol(region.begin())[0] + 1
            last_line = self.view.rowcol(region.end())[0] + 1

            if first_line == last_line:
                ranges.append(str(first_line))
            else:
                ranges.append('%d:%d' % (first_line, last_line))

        return ranges

    def get_current_line(self):
        """Get the 1-based line number of the (first) currently selected line.
        """
        region = self.view.sel()[0]
        row, col = self.view.rowcol(region.begin())
        return row + 1

    def _create_issue_tracker(self, config):
        if config['type'] == 'bitbucket':
            return BitbucketIssueTracker(config)
        elif config['type'] == 'jira':
            return JiraIssueTracker(config)

        raise SublimeBucketError('Unknown issue tracker type: "%s"' %
                                 config['type'])


class OpenInBitbucketCommand(CommandBase, sublime_plugin.TextCommand):
    def run(self, edit):
        backend = self.get_backend()

        try:
            remote_match = backend.find_bitbucket_remote_match()
            url = '%(host)s/%(repo)s/src/%(branch)s/%(path)s#%(hash)s' % {
                'host': 'https://' + remote_match.group('host'),
                'repo': remote_match.group('repo'),
                'branch': backend.find_current_revision(),
                'path': self.get_file_path(),
                'hash': '%s-%s' % (os.path.basename(self.view.file_name()),
                                   ','.join(self.get_line_ranges()))
            }
            webbrowser.open(url)
        except SublimeBucketError as e:
            sublime.error_message(str(e))
        except Exception:
            traceback.print_exc()
            sublime.error_message('Encountered an unexpected error')


class OpenBitbucketChangesetCommand(CommandBase, sublime_plugin.TextCommand):
    def run(self, edit):
        backend = self.get_backend()

        try:
            remote_match = backend.find_bitbucket_remote_match()
            url = '%(host)s/%(repo)s/commits/%(hash)s#chg-%(file)s' % {
                'host': 'https://' + remote_match.group('host'),
                'repo': remote_match.group('repo'),
                'hash': backend.find_selected_revision(
                    self.get_file_path(), self.get_current_line()),
                'file': self.get_file_path()
            }
            webbrowser.open(url)
        except SublimeBucketError as e:
            sublime.error_message(str(e))
        except Exception:
            traceback.print_exc()
            sublime.error_message('Encountered an unexpected error')


class FindBitbucketPullRequestCommand(CommandBase, sublime_plugin.TextCommand):
    def run(self, edit):
        backend = self.get_backend()

        try:
            target_revision = backend.find_selected_revision(
                self.get_file_path(), self.get_current_line())
            pull_request_id = backend.get_pull_request_id(target_revision)
            remote_match = backend.find_bitbucket_remote_match()
            url = ('https://%(host)s/%(repo)s/pull-requests/%(id)d/diff'
                   '#chg-%(file)s') % {
                'host': remote_match.group('host'),
                'repo': remote_match.group('repo'),
                'id': pull_request_id,
                'file': self.get_file_path()
            }
            webbrowser.open(url)
        except SublimeBucketError as e:
            sublime.error_message(str(e))
        except Exception:
            traceback.print_exc()
            sublime.error_message('Encountered an unexpected error')


class OpenInIssueTrackerCommand(CommandBase, sublime_plugin.TextCommand):
    def run(self, edit):
        self.backend = self.get_backend()

        try:
            remote_match = self.backend.find_bitbucket_remote_match()

            # For now just open the first issue key we find. In the future
            # maybe consider adding support for multiple issues.
            for (key, tracker) in self.get_issue_keys():
                webbrowser.open(
                    tracker.get_issue_url(key, **remote_match.groupdict()))
                return

            raise SublimeBucketError('Unable to find any matching issue keys')

        except SublimeBucketError as e:
            sublime.error_message(str(e))
        except Exception:
            traceback.print_exc()
            sublime.error_message('Encountered an unexpected error')

    def get_issue_keys(self):
        """Get any issue key(s) in the commit message of the target revision.
        """
        target_revision = self.backend.find_selected_revision(
            self.get_file_path(), self.get_current_line())

        revision_message = self.backend.get_revision_message(target_revision)

        for issue_tracker in self.get_issue_trackers():
            issue_key = issue_tracker.find_issue_key(revision_message)
            if issue_key:
                yield issue_key, issue_tracker


class BackendBase():
    def __init__(self, cwd):
        self.cwd = cwd

    @property
    def bitbucket_hosts(self):
        custom_hosts = load_settings().get('bitbucket_hosts', [])
        return list(set(['bitbucket.org'] + custom_hosts))

    def find_bitbucket_remote_match(self):
        """Get a regex match of the first remote containing a Bitbucket host.

        Returns an _sre.SRE_MATCH object w/ `string` attribute referring to the
        full remote string.
        """
        remotes = self.get_remote_list()

        for host in self.bitbucket_hosts:
            bitbucket_pattern = (r'(?P<host>%s)[:/]'
                                 r'(?P<repo>[\w\.\-]+/[\w\.\-]+)'
                                 r'(?:\.git)?') % host
            for remote in remotes:
                remote_match = re.search(bitbucket_pattern, remote)
                if remote_match:
                    return remote_match

        raise SublimeBucketError('Unable to find a remote matching: %r' %
                                 self.bitbucket_hosts)

    def find_bitbucket_remote(self):
        """Get the name of the remote (e.g. 'origin') pointing to Bitbucket.
        """
        remote_match = self.find_bitbucket_remote_match()

        # For both Git and Hg the remote name is the first token in the string.
        return re.split(r'\s+', remote_match.string, maxsplit=1)[0]

    def find_current_revision(self):
        """Get the hash of the commit/changeset that's currently checked out.
        """
        raise NotImplementedError

    def find_current_branch(self):
        """Get the name of the current branch.
        """
        raise NotImplementedError

    def get_default_branch(self):
        """Get the default branch for the current repo.
        """
        raise NotImplementedError

    def find_selected_revision(self, file_path, current_line):
        """Get the hash of the revision associated with the current line.
        """
        raise NotImplementedError

    def get_pull_request_id(self, target_revision):
        """Get the Bitbucket pull request ID where a given change was merged.

        This method invokes `git rev-list` to compute the merge commit for Git
        repos. For Mercurial repos it uses `hg log -r` to query for the
        changeset using Mercurial's revset syntax.

        This method then uses `git show` for Git repos and `hg log -r` for
        Mercurial repos and scans the commit message for an explicit mention of
        a pull request, which is populated by default in the Bitbucket UI.

        This won't work if the author of the PR wrote a custom commit message
        without mentioning the PR.
        """
        raise NotImplementedError

    def _exec(self, command):
        """Execute command with cwd set to the project path and shell=True.
        """
        output = subprocess.check_output(command, cwd=self.cwd, shell=True)
        return output.decode(TEXT_ENCODING)


class GitBackend(BackendBase):
    command = 'git'

    def get_remote_list(self):
        return self._exec('git remote -v').splitlines()

    def find_current_revision(self):
        info = self._exec('git show HEAD').splitlines()
        for line in info:
            revision_match = re.search(r'commit (\w+)', line)
            if revision_match:
                return revision_match.group(1)

        raise SublimeBucketError('Unable to get the current revision')

    def find_current_branch(self):
        info = self._exec('git branch').splitlines()
        for line in info:
            current_branch_match = re.match(r'\* (.*)', line)
            if current_branch_match:
                return current_branch_match.group(1)

        raise SublimeBucketError('Unable to get the current branch')

    def find_selected_revision(self, file_path, current_line):
        output = self._exec(
            'git blame -L %d,%d %s' % (current_line, current_line, file_path))
        return re.match(r'^(\w+)', output).group(1)

    def get_default_branch(self):
        # First try to figure out what the default branch is set to on the
        # remote.
        remote = self.find_bitbucket_remote()
        try:
            return self._exec('git rev-parse --abbrev-ref refs/remotes/%s/HEAD'
                              % remote).strip()
        except subprocess.CalledProcessError:
            # The above can return w/ a 128 exit code and a message like:
            # "unknown revision or path not in the working tree" ¯\_(ツ)_/¯
            pass

        # If we can't get the default branch from the remote, just try to get
        # the *current* branch.
        try:
            return self.find_current_branch()
        except SublimeBucketError:
            pass

        # As a fallback, just go with the git default.
        return 'master'

    def get_merge_revision(self, target_revision):
        default_branch = self.get_default_branch()
        revspec = '%s..%s' % (target_revision, default_branch)

        # First find the merge commit where the given commit was merged into
        # the default branch.
        ancestry_path = self._exec('git rev-list %s --ancestry-path --merges' %
                                   revspec).splitlines()
        first_parent = self._exec('git rev-list %s --first-parent --merges' %
                                  revspec).splitlines()
        first_parent = set(first_parent)
        merge_revision = next(rev for rev in reversed(ancestry_path)
                              if rev in first_parent)
        return merge_revision

    def get_revision_message(self, revision):
        return self._exec('git show %s --format="%%s%%n%%n%%b" --no-patch' %
                          revision)

    def get_pull_request_id(self, target_revision):
        merge_revision = self.get_merge_revision(target_revision)

        # Look at the commit message for the merge for a reference to the PR.
        message = self.get_revision_message(merge_revision)
        pull_request_match = re.search(r'pull request #(\d+)', message)
        if pull_request_match:
            return int(pull_request_match.group(1))

        raise SublimeBucketError('Unable to determine the pull request where '
                                 'the commit was merged')


class MercurialBackend(BackendBase):
    command = 'hg'

    def get_remote_list(self):
        return self._exec('hg paths').splitlines()

    def find_current_revision(self):
        return self._exec('hg id -i').strip().rstrip('+')

    def find_current_branch(self):
        return self._exec('hg branch').strip()

    def find_selected_revision(self, file_path, current_line):
        annotated_lines = self._exec('hg annotate -c %s' % file_path).splitlines()
        return re.match(r'^(\w+)', annotated_lines[current_line - 1]).group(1)

    def get_default_branch(self):
        return 'default'

    def get_revision_message(self, revision):
        output = self._exec('hg log -v -r %s' % revision)
        message_match = re.search(r'description:\n(.*)', output, re.DOTALL)
        return message_match.group(1)

    def get_pull_request_id(self, target_revision):
        log_output = self._exec(
            'hg log -r "first(descendants(%s) and desc(\'pull request\') '
            'and merge())"' % target_revision)
        pull_request_match = re.search(r'pull request #(\d+)', log_output)
        if pull_request_match:
            return int(pull_request_match.group(1))

        raise SublimeBucketError('Unable to determine the pull request where '
                                 'the changeset was merged')


class IssueTrackerBase():
    def find_issue_key(self, message, **kwargs):
        raise NotImplementedError

    def get_issue_url(self, issue_key, **kwargs):
        raise NotImplementedError


class BitbucketIssueTracker(IssueTrackerBase):
    def __init__(self, config):
        self.host = config.get('host', 'https://bitbucket.org')

    def find_issue_key(self, message, **kwargs):
        issue_key_match = re.search(r'\b\#(\d+)\b', message)
        if issue_key_match:
            return issue_key_match.group(1)
        return None

    def get_issue_url(self, issue_key, **kwargs):
        repo = kwargs['repo']
        return urljoin(self.host, '/%s/issues/%s' % (repo, issue_key))


class JiraIssueTracker(IssueTrackerBase):
    def __init__(self, config):
        self.host = config['host']
        self.project_keys = config['project_keys']

    def find_issue_key(self, message, **kwargs):
        for project_key in self.project_keys:
            issue_key_match = re.search(r'\b(%s-\d+)\b' % project_key, message)
            if issue_key_match:
                return issue_key_match.group(1)
        return None

    def get_issue_url(self, issue_key, **kwargs):
        return urljoin(self.host, '/browse/%s' % issue_key)


class SublimeBucketError(Exception):
    pass
