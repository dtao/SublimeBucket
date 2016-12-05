import os
import re
import sublime_plugin
import subprocess

BITBUCKET_HOST = 'bitbucket.org'


class OpenInBitbucketCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.full_path = self.view.file_name()
        self.directory = os.path.dirname(self.full_path)

        url = 'https://%(host)s/%(repo)s/src/%(branch)s/%(path)s#%(hash)s' % {
            'host': BITBUCKET_HOST,
            'repo': self.find_bitbucket_repo(),
            'branch': self.find_current_revision(),
            'path': self.get_file_path(),
            'hash': '%s-%s' % (os.path.basename(self.full_path),
                               ','.join(self.get_line_ranges()))
        }
        subprocess.call(['open', url])

    def find_bitbucket_repo(self):
        """Get the Bitbucket repo (username/repo_slug) for the current file.

        This method works by invoking `git remote -v` and inspecting the output
        for a line containing BITBUCKET_HOST. If this command fails, it tries
        again with `hg paths` for Mercurial repositories.
        """
        try:
            remotes = self._exec('git remote -v').splitlines()
        except subprocess.CalledProcessError:
            remotes = self._exec('hg paths').splitlines()

        bitbucket_pattern = (r'%s[:/]([\w\-]+)/([\w\-]+)(?:\.git)?' %
                             BITBUCKET_HOST)
        for remote in remotes:
            remote_match = re.search(bitbucket_pattern, str(remote))
            if remote_match:
                return '%s/%s' % remote_match.groups()

    def find_current_revision(self):
        """Get the hash of the commit/changeset that's currently checked out.

        This method works by invoking `git show HEAD` and parsing the output.
        If that fails, it tries again with `hg id -i` for Mercurial
        repositories.
        """
        try:
            info = self._exec('git show HEAD').splitlines()
            for line in info:
                revision_match = re.search(r'commit (\w+)', str(line))
                if revision_match:
                    return revision_match.group(1)
        except subprocess.CalledProcessError:
            revision = self._exec('hg id -i')
            return revision.decode('utf-8').strip()

    def get_file_path(self):
        """Get the path to the current file, relative to the repository root.
        """
        folders = self.view.window().folders()
        for folder in folders:
            if self.full_path.startswith(folder):
                file_path = self.full_path[len(folder):]
                if file_path.startswith('/'):
                    file_path = file_path[1:]
                return file_path

    def get_line_ranges(self):
        """Get the list of currently selected line ranges, in start:end format.
        """
        ranges = []

        for (start, end) in self.view.sel():
            first_line = self.view.rowcol(start)[0] + 1
            last_line = self.view.rowcol(end)[0] + 1

            if first_line == last_line:
                ranges.append(str(first_line))
            else:
                # Fix ordering in case selection was made bottom-up.
                ranges.append('%d:%d' % (min(first_line, last_line),
                                         max(first_line, last_line)))

        return ranges

    def _exec(self, command):
        """Execute command with cwd set to the project path and shell=True.
        """
        return subprocess.check_output(command, cwd=self.directory, shell=True)
