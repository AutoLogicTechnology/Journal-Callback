
# Copyright 2015 (c) Autologic Technology Ltd
# Author: Michael Crilly (mike@autologic.cm)
#
# This callback plugin is designed to work in conjunction with
# Autologic Journal, an Ansible auditing system. See
# http://autologic.cm/journal for more information
#
# License: MIT

import datetime
import uuid
import json
import re 
import urllib2 as http 
import sqlite3 as db 

class CallbackModule(object):
  """
  Log JSON results to the Autologic Journal API.
  """

  def __init__(self):
    self.entry_id = uuid.uuid4().hex 
    self.journal = {
      'id': self.entry_id,
      'data': {
        'date': datetime.datetime.now().strftime('%c'),
        'who': {},
        'hosts': {},
      },
    }

    self.installed_reg  = re.compile('[Dependency ]?Installed:\\n[ ]+?(.*)')
    self.updated_reg    = re.compile('Updated:\\n[ ]+?(.*)')
    self.replaced_reg   = re.compile('Replaced:\\n[ ]+?(.*)')
    self.ignored_reg    = re.compile('(.*) providing (.*) is already installed')

  def pprintjson(self, data):
    print(json.dumps(data,separators=(',',':'),sort_keys=True,indent=4))

  def new_host(self, host):
    """
    If a host doesn't exist within the journal, create a new entry for it.
    """

    if not host in self.journal['data']['hosts']:
      self.journal['data']['hosts'][host] = {
        'success': 0,
        'failed': 0,
        'tasks': [],
      }

  def success(self, host):
    self.journal['data']['hosts'][host]['success'] += 1

  def parse_yum_output(self, host, results):
    """
    Process the horrible Ansible Yum module output and provide a better
    way of indexing and reading it.
    """

    entry = {
      'date': datetime.datetime.now().strftime('%c'),
      'ansible_results': results,
      'position': len(self.journal['data']['hosts'][host]['tasks'])+1,
      'yum': {
        'installed': [],
        'replaced': [],
        'updated': [],
        'ignored': [],
      }
    }

    self.pprintjson(results)

    for result in results['results']:
      installed = self.installed_reg.search(result)
      if installed:
        entry['yum']['installed'].append(installed.group(1).strip())
        continue

      updated = self.updated_reg.search(result)
      if updated:
        entry['yum']['updated'].append(updated.group(1).strip())
        continue

      replaced = self.replaced_reg.search(result)
      if replaced:
        entry['yum']['replaced'].append(replaced.group(1).strip())
        continue

      ignored = self.ignored_reg.search(result)
      if ignored:
        entry['yum']['ignored'].append(ignored.group(1).strip())
        continue

    self.success(host)
    self.journal['data']['hosts'][host]['tasks'].append(entry)
 
  def parse_setup_output(self, host, res):
    self.journal['data']['who'] = res['ansible_facts']['ansible_env']

  def store_raw_output(self, host, res):
    entry = {'date': datetime.datetime.now().strftime('%c'), 'ansible_results': res, 'position': len(self.journal['data']['hosts'][host]['tasks'])+1}
    self.success(host)
    self.journal['data']['hosts'][host]['tasks'].append(entry)

  def on_any(self, *args, **kwargs):
    pass

  def runner_on_failed(self, host, res, ignore_errors=False):
    pass

  def runner_on_ok(self, host, res):
    self.new_host(host)

    if res['invocation']['module_name'] == 'setup':
      self.parse_setup_output(host, res)
      return

    if res['invocation']['module_name'] == 'yum':
      self.parse_yum_output(host, res)
      return

    self.store_raw_output(host, res)

  def runner_on_skipped(self, host, item=None):
    pass

  def runner_on_unreachable(self, host, res):
    pass

  def runner_on_no_hosts(self):
    pass

  def runner_on_async_poll(self, host, res, jid, clock):
    pass

  def runner_on_async_ok(self, host, res, jid):
    pass

  def runner_on_async_failed(self, host, res, jid):
    pass

  def playbook_on_start(self):
    pass 

  def playbook_on_notify(self, host, handler):
    self.pprintjson([host, handler])

  def playbook_on_no_hosts_matched(self):
    pass

  def playbook_on_no_hosts_remaining(self):
    pass

  def playbook_on_task_start(self, name, is_conditional):
    pass

  def playbook_on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
    pass

  def playbook_on_setup(self):
    pass

  def playbook_on_import_for_host(self, host, imported_file):
    pass

  def playbook_on_not_import_for_host(self, host, missing_file):
    pass

  def playbook_on_play_start(self, name):
    pass

  def playbook_on_stats(self, stats):
    self.pprintjson(self.journal)
