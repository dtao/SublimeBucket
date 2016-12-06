import os
import re
import sublime_plugin
import subprocess

BITBUCKET_HOST = 'bitbucket.org'
TEXT_ENCODING = 'utf-8'


class SublimeBucketBase():
    @property
    def full_path(self):
        if not hasattr(self, '_full_path'):
            self._full_path = self.view.file_name()
        return self._full_path

    @property
    def directory(self):
        if not hasattr(self, '_directory'):
            for folder in self.view.window().folders():
                if self.full_path.startswith(folder):
                    self._directory = folder
                    break
        return self._directory

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
            remote_match = re.search(bitbucket_pattern, remote)
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
                revision_match = re.search(r'commit (\w+)', line)
                if revision_match:
                    return revision_match.group(1)
        except subprocess.CalledProcessError:
            revision = self._exec('hg id -i')
            return revision.strip()

    def get_file_path(self):
        """Get the path to the current file, relative to the repository root.
        """
        for folder in self.view.window().folders():
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

    def get_default_branch(self):
        """Get the default branch for the current repo.

        Currently this method just default to "master" as I need to figure out
        how to actually do this.
        """
        return 'master'

    def _exec(self, command):
        """Execute command with cwd set to the project path and shell=True.
        """
        output = subprocess.check_output(command, cwd=self.directory,
                                         shell=True)
        return output.decode(TEXT_ENCODING)


class OpenInBitbucketCommand(SublimeBucketBase, sublime_plugin.TextCommand):
    def run(self, edit):
        url = 'https://%(host)s/%(repo)s/src/%(branch)s/%(path)s#%(hash)s' % {
            'host': BITBUCKET_HOST,
            'repo': self.find_bitbucket_repo(),
            'branch': self.find_current_revision(),
            'path': self.get_file_path(),
            'hash': '%s-%s' % (os.path.basename(self.full_path),
                               ','.join(self.get_line_ranges()))
        }
        subprocess.call(['open', url])


class FindBitbucketPullRequestCommand(SublimeBucketBase,
                                      sublime_plugin.TextCommand):
    def run(self, edit):
        target_revision = self.find_selected_revision()
        merge_revision = self.get_merge_revision(target_revision)
        pull_request_id = self.get_pull_request_id(merge_revision)
        url = 'https://%(host)s/%(repo)s/pull-requests/%(id)d' % {
            'host': BITBUCKET_HOST,
            'repo': self.find_bitbucket_repo(),
            'id': pull_request_id
        }
        subprocess.call(['open', url])

    def find_selected_revision(self):
        """Get the hash of the revision associated with the current line.

        This method works by invoking `git blame` and parsing the output.
        """
        current_line = self.get_current_line()
        blame_output = self._exec(
            'git blame -L %d,%d %s' % (current_line, current_line,
                                       self.get_file_path()))
        revision_match = re.match(r'^(\w+)', blame_output)
        if revision_match:
            return revision_match.group(1)

    def get_merge_revision(self, target_revision=None):
        """Get the hash of the revision where the target change was merged.
        """
        target_revision = target_revision or self.find_current_revision()
        default_branch = self.get_default_branch()
        revspec = '%s..%s' % (target_revision, default_branch)
        ancestry_path = self._exec('git rev-list %s --ancestry-path' %
                                   revspec).splitlines()
        first_parent = self._exec('git rev-list %s --first-parent' %
                                  revspec).splitlines()
        common = set(ancestry_path) & set(first_parent)
        return next(rev for rev in reversed(ancestry_path)
                    if rev in common)

    def get_pull_request_id(self, merge_revision):
        """Get the Bitbucket pull request ID associated with the given merge.
        """
        info = self._exec('git show --oneline %s' % merge_revision)
        pull_request_match = re.search(r'pull request #(\d+)', info)
        if pull_request_match:
            return int(pull_request_match.group(1))
