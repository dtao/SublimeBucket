# SublimeBucket

Bitbucket plugin for Sublime Text 3

## Installation

I have a [pull request][1] to add this to [Package Control][2]. In the
meantime, you can create a directory called "SublimeBucket" (or anything for
that matter) in your Packages folder and copy Context.sublime-menu and
sublime_bucket.py there.

## Commands

The following commands are available under "Bitbucket" from the context menu
and can be assigned to keyboard shortcuts:

### 1. open_in_bitbucket (Git + Hg)

Opens the selected line(s) in Bitbucket, preserving all highlighted ranges.

### 2. open_bitbucket_changeset (Git + Hg)

Opens the commit where the current line was last changed in Bitbucket.

### 3. find_bitbucket_pull_request (Git + Hg)

Looks up the commit where the current line was last changed and opens the pull
request where that change was introduced.

## Settings

This plugin stores settings in the Bitbucket.sublime-settings package. The
following values are configurable:

### 1. bitbucket_hosts

A list of hosts to identify as Bitbucket. For the vast majority of users this
should just stay as the default of `['bitbucket.org']`. On the off chance you
have some fancy access to other Bitbucket environments (e.g., you're a
developer on the Bitbucket team), you can add the domain(s) for those
environment to this list.

## Why is this on GitHub? Don't you work for Bitbucket?

GitHub is for toy projects (like this) while Bitbucket is for Serious Work™.

Just kidding. I didn't have enough Python projects on GitHub.

[1]: https://github.com/wbond/package_control_channel/pull/5998
[2]: https://packagecontrol.io/
