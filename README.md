# SublimeBucket

Bitbucket plugin for Sublime Text 3

## Commands

### 1. open_in_bitbucket (Git + Hg)

Opens the selected line(s) in Bitbucket, preserving all highlighted ranges.

### 2. find_bitbucket_pull_request (Git + Hg)

Looks up the commit where the current line was last changed and opens the pull
request where that change was introduced.

## Settings

This plugin stores settings in the Bitbucket.sublime-settings package. The
following values are configurable:

### 1. bitbucket_hosts

A list of hosts to identify as Bitbucket. For the vast majority of users this
should just stay as the default of `['bitbucket.org']`. On the off chance you
have some fancy access to a different Bitbucket environment (e.g., you're a
developer on the Bitbucket team), you can add the domain for that environment
to this list.
