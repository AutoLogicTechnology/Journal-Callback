# Journal Callback

This Ansible [callback plugin](http://docs.ansible.com/developing_plugins.html#callbacks) is designed to log (locally and remotely) all activity during an Ansible Play. It grabs all the raw JSON output from Ansible and builds up a "journal" of everything that took place, including the results, and then dumps this journal entry into a local SQLite cache. If configured, the callback plugin will also talk to a remote [Autologic Journal](#) (coming soon) API which can be used as a "write once, never forget" audit trail of who did what, and how.

## Version

v1.0.0

## Benefits

As it stands now, when Ansible is executed, the results are only a local concern. Any errors, issues, warnings, etc, are only known to the administrator who executed the command(s). With Journal Callback, all the results of the Play(s) are logged remotely for the entire team to see, thus making it easier to understand what has changed within your estate (which may be in response to a website going down or a service that has stopped working.)

After an Ansible run, the remote system only contains logs of the fact someone logged in, made some changes, and left again. It's not entirely clear what was done, and how. Journal Callback helps alleviate this problem by providing a means of auditing past Plays, allowing you and your team to determine who did what, and how, and fix any issues that might have occured.

## Current Goals

The current version has the following features:

- Process everything that happens and log the raw Ansible JSON output to the journal;
- Process the ```setup``` module and grab the remote environment used by Ansible. This includes who logged in and what their environment looked like;
- Process the ```yum``` module and determine what took place, such as what packages were installed, updated, removed, etc;
- Log the final journal to a local SQLite3 database;

## Going Forward

To see what's up and coming, please see our ["Kanban" board.](https://trello.com/b/FCdKoIU3)

## Author Information

- Michael Crilly
- Autologic Technology Ltd
- http://www.mcrilly.me/
