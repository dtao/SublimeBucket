# SublimeBucket

Bitbucket plugin for Sublime Text 3

## Installation

The easiest way to install the Bitbucket plugin is using [Package Control][1]
(the package is listed as simply "Bitbucket"). If you prefer to do things the
hard way, you can create a directory called "SublimeBucket" (or anything for
that matter) in your Packages folder and copy the following files there:

- sublime_bucket.py
- Main.sublime-menu
- Context.sublime-menu
- Bitbucket.sublime-commands
- Bitbucket.sublime-settings

## Commands

The following commands are available under "Bitbucket" from the context menu as
well as the command palette and can be assigned to keyboard shortcuts. Every
command should work for both Git and Mercurial repositories.

### 1. Open in Bitbucket

Opens the selected line(s) in Bitbucket, preserving all highlighted ranges.

Example keyboard shortcut:

```
{
  "keys": ["super+b", "super+o"],
  "command": "open_in_bitbucket"
}
```

### 2. Open Bitbucket Changeset

Opens the commit where the current line was last changed in Bitbucket.

Example keyboard shortcut:

```
{
  "keys": ["super+b", "super+c"],
  "command": "open_bitbucket_changeset"
}
```

### 3. Find Bitbucket Pull Request

Looks up the commit where the current line was last changed and opens the pull
request where that change was introduced.

Example keyboard shortcut:

```
{
  "keys": ["super+b", "super+p"],
  "command": "find_bitbucket_pull_request"
}
```

### 4. Open in Issue Tracker

Looks up the commit where the current line was last changed and opens the issue
in your issue tracker (e.g., in Jira) with which that change is associated.

See the [issue_trackers setting][2] for more information.

Example keyboard shortcut:

```
{
  "keys": ["super+b", "super+i"],
  "command": "open_in_issue_tracker"
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

### 2. issue_trackers

A list of issue trackers you use, to power the "Open in Issue Tracker" command.

Each issue tracker type has its own style of configuration. Currently Bitbucket
and Jira are supported.

#### Bitbucket

The Bitbucket tracker identifies links to Bitbucket issues in commit messages.

```
{
  "type": "bitbucket",

  // Optional: a custom Bitbucket host, in case you're one of those special
  // people who also modified the `bitbucket_hosts` setting above. Defaults to
  // https://bitbucket.org for the majority of the population.
  "host": "https://bitbucket.org"
}
```

#### Jira

The Jira tracker identifies links to Jira issues for a given instance and a
specified list of project keys.

```
{
  "type": "jira",

  // The base URL (including https://) of the Jira instance.
  "host": "https://jira.company.com",

  // An array of project keys (e.g., ABC) for identifying issue references. For
  // example, if you have `["ABC"]` in here, then if a commit message includes
  // a string like 'ABC-123' the Bitbucket plugin can take you straight to that
  // issue.
  "project_keys": []
}
```

## Why is this on GitHub? Don't you work for Bitbucket?

GitHub is for toy projects (like this) while Bitbucket is for Serious Work™.

Just kidding. I didn't have enough Python projects on GitHub.

[1]: https://packagecontrol.io/
[2]: #2-issue_trackers
