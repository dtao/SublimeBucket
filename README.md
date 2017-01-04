# SublimeBucket

Bitbucket plugin for Sublime Text 3

## Installation

The easiest way to install the Bitbucket plugin is using [Package Control][1]
(the package is listed as simply "Bitbucket"). If you prefer to do things the
hard way, you can create a directory called "SublimeBucket" (or anything for
that matter) in your Packages folder and copy the following files there:

- sublime_bucket.py
- Context.sublime-menu

## Commands

The following commands are available under "Bitbucket" from the context menu
and can be assigned to keyboard shortcuts:

### 1. Open in Bitbucket (Git + Hg)

Opens the selected line(s) in Bitbucket, preserving all highlighted ranges.

Example keyboard shortcut:

```
{
  "keys": ["super+b", "super+o"],
  "command": "open_in_bitbucket"
}
```

### 2. Open Bitbucket Changeset (Git + Hg)

Opens the commit where the current line was last changed in Bitbucket.

Example keyboard shortcut:

```
{
  "keys": ["super+b", "super+c"],
  "command": "open_bitbucket_changeset"
}
```

### 3. Find Bitbucket Pull Request (Git + Hg)

Looks up the commit where the current line was last changed and opens the pull
request where that change was introduced.

Example keyboard shortcut:

```
{
  "keys": ["super+b", "super+p"],
  "command": "find_bitbucket_pull_request"
}
```

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

[1]: https://packagecontrol.io/
