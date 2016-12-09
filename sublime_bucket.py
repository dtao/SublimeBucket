import os
import re
import sublime
import sublime_plugin
import subprocess

TEXT_ENCODING = 'utf-8'


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
        file_path = self.view.file_name()[len(self.get_directory()):]
        if file_path.startswith('/'):
            file_path = file_path[1:]
        return file_path

    def get_line_ranges(self):
        """Get the list of currently selected line ranges, in start:end format.
        """
        ranges = []

        for (start, end) in self.view.sel():
            # Sublime provides 0-based line numbers but Bitbucket line numbers
            # start with 1.
            first_line = self.view.rowcol(start)[0] + 1
            last_line = self.view.rowcol(end)[0] + 1

            if first_line == last_line:
                ranges.append(str(first_line))
            else:
                # Fix ordering in case selection was made bottom-up.
                ranges.append('%d:%d' % (min(first_line, last_line),
                                         max(first_line, last_line)))

        return ranges

    def get_current_line(self):
        """Get the 1-based line number of the (first) currently selected line.
        """
        start, end = self.view.sel()[0]
        row, col = self.view.rowcol(start)
        return row + 1


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
            subprocess.call(['open', url])
        except SublimeBucketError as e:
            sublime.error_message(str(e))
        except Exception as e:
            print(e)
            sublime.error_message('Encountered an unexpected error')


class FindBitbucketPullRequestCommand(CommandBase,
                                      sublime_plugin.TextCommand):
    def run(self, edit):
        backend = self.get_backend()

        try:
            target_revision = backend.find_selected_revision(
                self.get_file_path(), self.get_current_line())
            pull_request_id = backend.get_pull_request_id(target_revision)
            remote_match = backend.find_bitbucket_remote_match()
            url = 'https://%(host)s/%(repo)s/pull-requests/%(id)d' % {
                'host': remote_match.group('host'),
                'repo': remote_match.group('repo'),
                'id': pull_request_id
            }
            subprocess.call(['open', url])
        except SublimeBucketError as e:
            sublime.error_message(str(e))
        except Exception as e:
            print(e)
            sublime.error_message('Encountered an unexpected error')


class BackendBase():
    def __init__(self, cwd):
        self.cwd = cwd

    @property
    def settings(self):
        return sublime.load_settings('Bitbucket.sublime-settings')

    @property
    def bitbucket_hosts(self):
        custom_hosts = self.settings.get('bitbucket_hosts', [])
        return list(set(['bitbucket.org'] + custom_hosts))

    def find_bitbucket_remote_match(self):
        """Get a regex match of the first remote containing a Bitbucket host.

        Returns an _sre.SRE_MATCH object w/ `string` attribute referring to the
        full remote string.
        """
        remotes = self.get_remote_list()

        for host in self.bitbucket_hosts:
            bitbucket_pattern = (r'(?P<host>%s)[:/](?P<repo>[\w\-]+/[\w\-]+)'
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

    def find_selected_revision(self, file_path, current_line):
        output = self._exec(
            'git blame -L %d,%d %s' % (current_line, current_line, file_path))
        return re.match(r'^(\w+)', output).group(1)

    def get_default_branch(self):
        remote = self.find_bitbucket_remote()
        return self._exec('git rev-parse --abbrev-ref refs/remotes/%s/HEAD'
                          % remote).strip()

    def get_pull_request_id(self, target_revision):
        default_branch = self.get_default_branch()
        revspec = '%s..%s' % (target_revision, default_branch)

        # First find the merge commit where the given commit was merged into
        # the default branch.
        ancestry_path = self._exec('git rev-list %s --ancestry-path' %
                                   revspec).splitlines()
        first_parent = self._exec('git rev-list %s --first-parent' %
                                  revspec).splitlines()
        common = set(ancestry_path) & set(first_parent)
        merge_revision = next(rev for rev in reversed(ancestry_path)
                              if rev in common)

        # Look at the commit message for the merge for a reference to the PR.
        info = self._exec('git show --oneline %s' % merge_revision)
        pull_request_match = re.search(r'pull request #(\d+)', info)
        if pull_request_match:
            return int(pull_request_match.group(1))

        raise SublimeBucketError('Unable to determine the pull request where '
                                 'the commit was merged')


class MercurialBackend(BackendBase):
    command = 'hg'

    def get_remote_list(self):
        return self._exec('hg paths').splitlines()

    def find_current_revision(self):
        return self._exec('hg id -i').strip()

    def find_selected_revision(self, file_path, current_line):
        output = self._exec(
            'hg annotate -c %s | head -n %d | tail -n 1' % (file_path,
                                                            current_line))
        return re.match(r'^(\w+)', output).group(1)

    def get_default_branch(self):
        return 'default'

    def get_pull_request_id(self, target_revision):
        log_output = self._exec(
            'hg log -r "first(descendants(%s) and desc(\'pull request\') '
            'and merge())"' % target_revision)
        pull_request_match = re.search(r'pull request #(\d+)', log_output)
        if pull_request_match:
            return int(pull_request_match.group(1))

        raise SublimeBucketError('Unable to determine the pull request where '
                                 'the changeset was merged')


class SublimeBucketError(Exception):
    pass
