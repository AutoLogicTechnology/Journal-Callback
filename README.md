# Journal Callback

This Ansible [callback plugin](http://docs.ansible.com/developing_plugins.html#callbacks) is designed to log (locally and remotely) all activity during an Ansible Play. It grabs all the raw JSON output from Ansible and builds up a "journal" of everything that took place, including the results, and then dumps this journal entry into a local SQLite cache. If configured, the callback plugin will also talk to a remote [Autologic Journal](#) (coming soon) API which can be used as a "write once, never forget" audit trail of who did what, and how.

## Version

v1.3.3

## Benefits

As it stands now, when Ansible is executed, the results are only a local concern. Any errors, issues, warnings, etc, are only known to the administrator who executed the command(s). With Journal Callback, all the results of the Play(s) are logged remotely for the entire team to see, thus making it easier to understand what has changed within your estate (which may be in response to a website going down or a service that has stopped working.)

After an Ansible run, the remote system only contains logs of the fact someone logged in, made some changes, and left again. It's not entirely clear what was done, and how. Journal Callback helps alleviate this problem by providing a means of auditing past Plays, allowing you and your team to determine who did what, and how, and fix any issues that might have occured.

## Current Features

The current version has the following features:

- Process everything that happens and log the raw Ansible JSON output to the journal;
- Process the ```setup``` module and grab the remote environment used by Ansible. This includes who logged in and what their environment looked like;
- Process the ```yum``` module and determine what took place, such as what packages were installed, updated, removed, etc;
- Log the final journal to a local SQLite3 database;

## CLI

The CLI options allow you to easily interact with the SQLite cache, saving you the job of having to write code or manually wade through the (base64 encoded) contents.

Current arguments include:

- Pretty printing the contents of the cache with a limited, bird's eye view of the contents;
- JSON printing the contents in full for your use;
- Blame. This is a core feature and allows you to supply a host name and see what happened on that host, and by whom;

### Pretty Printing

This feature is just a simple way of looking at an overview of what's in your cache. It produces results along these lines:

```
$ python autologic_journal_callback.py --pretty-list
ID        Date                          Hosts     Total Success       Total Failed        
1         Tue Apr 28 15:38:52 2015      1         8                   0                   
2         Tue Apr 28 15:51:22 2015      1         9                   0            
```

It's useful for glancing over the cache and seeing if you need to clear it due to size (which can be done by simply deleting the cache or moving it aside) or perhaps if anything in the "Total Failed" needs your attention.

### JSON Printing

This is somewhat obvious: it prints out the entire cache as a JSON document. You can use this with the [jq](https://github.com/stedolan/jq) tool to refine the data coming out, or just review it on the CLI (it's pretty printed for you.)

### Blame

The blame feature is basic as it stands now, but it's one of the core features and as such it'll get more attention going forward. This feature was inspired by the ```git blame``` command.

An example of the output would look like this:

```json
[
    {
        "date":"Tue Apr 28 15:38:52 2015",
        "host":"sandbox",
        "tasks":[
            {
                "changed":false,
                "module":"yum"
            },
            {
                "changed":false,
                "module":"group"
            },
            {
                "changed":false,
                "module":"user"
            }
        ],
        "who":{
            "sudo_user":"vagrant",
            "user":"root"
        }
    },
    {
        "date":"Tue Apr 28 15:51:22 2015",
        "host":"sandbox",
        "tasks":[
            {
                "changed":true,
                "module":"yum"
            }
        ],
        "who":{
            "sudo_user":"vagrant",
            "user":"root"
        }
    }
]
```

It contains the ```sudo_user``` used to access the system, plus the ```user``` which executed the remote Ansible scripts (which implement the state you've defined.) This is very useful for determining if you've done something to break a system/state, or perhaps if someone else has done it.

## Going Forward

To see what's up and coming, please see our ["Kanban" board.](https://trello.com/b/FCdKoIU3)

## Author Information

- Michael Crilly
- Autologic Technology Ltd
- http://www.mcrilly.me/
