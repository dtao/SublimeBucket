import os
import re
import sublime_plugin
import subprocess

BITBUCKET_HOST = 'bitbucket.org'


class OpenInBitbucketCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        full_path = self.view.file_name()
        url = 'https://%(host)s/%(repo)s/src/%(branch)s/%(path)s#%(hash)s' % {
            'host': BITBUCKET_HOST,
            'repo': self.find_bitbucket_repo(full_path),
            'branch': self.find_current_revision(full_path),
            'path': self.get_file_path(full_path),
            'hash': '%s-%s' % (os.path.basename(full_path),
                               ','.join(self.get_line_ranges()))
        }
        subprocess.call(['open', url])

    def find_bitbucket_repo(self, full_path):
        """Get the Bitbucket repo (username/repo_slug) for the current file.

        This method works by invoking `git remote -v` and inspecting the output
        for a line containing BITBUCKET_HOST.
        """
        remotes = subprocess.check_output('git remote -v',
                                          cwd=os.path.dirname(full_path),
                                          shell=True).splitlines()
        bitbucket_pattern = r'%s[:/]([\w\-]+)/([\w\-]+)\.git' % BITBUCKET_HOST
        for remote in remotes:
            remote_match = re.search(bitbucket_pattern, str(remote))
            if remote_match:
                return '%s/%s' % remote_match.groups()

    def find_current_revision(self, full_path):
        """Get the hash of the commit/changeset that's currently checked out.

        This method works by invoking `git show HEAD` and parsing the output.
        """
        info = subprocess.check_output('git show HEAD',
                                       cwd=os.path.dirname(full_path),
                                       shell=True).splitlines()
        for line in info:
            revision_match = re.search(r'commit (\w+)', str(line))
            if revision_match:
                return revision_match.group(1)

    def get_file_path(self, full_path):
        """Get the path to the current file, relative to the repository root.
        """
        folders = self.view.window().folders()
        for folder in folders:
            if full_path.startswith(folder):
                file_path = full_path[len(folder):]
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
