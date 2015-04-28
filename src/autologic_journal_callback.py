
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
import base64
import re 
import urllib2 as http 
import sqlite3 as db 

class SQLiteCache(object):

  def __init__(self):
    self.connection = db.connect('journal_callback.cache')
    self._build_database()

  def _build_database(self):
    cache_table = '''
    CREATE TABLE IF NOT EXISTS callback_cache (
      id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
      date TEXT NOT NULL,
      journal BLOB NOT NULL
    );
    '''

    c = self.connection.cursor()
    c.execute(cache_table)
    self.connection.commit()
    c.close()

  def cache_item(self, journal):
    insert_cache_item = '''
    INSERT INTO callback_cache (date, journal) VALUES (?, ?);
    '''

    now = datetime.datetime.now().strftime('%c')
    c = self.connection.cursor()
    c.execute(insert_cache_item, (now, base64.b64encode(json.dumps(journal))))
    self.connection.commit()
    c.close()

  def have_cached_items(self):
    find_cached_items = '''
    SELECT * FROM callback_cache;
    '''

    c = self.connection.cursor()

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

    # This is in place a the Journal API hasn't been started yet
    # so ALL runs go into a SQLite DB for the time being. That being said,
    # all runs that failo to talk to the API (for whatever reason) will
    # be cached in SQLite until the next run.
    self.cache = SQLiteCache()

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

  def failure(self, host):
    self.journal['data']['hosts'][host]['failed'] += 1

  def parse_yum_output(self, host, results):
    """
    Process the horrible Ansible Yum module output and provide a better
    way of indexing and reading it.
    """

    installed_reg  = re.compile('[Dependency ]?Installed:\\n[ ]+?(.*)')
    updated_reg    = re.compile('Updated:\\n[ ]+?(.*)')
    replaced_reg   = re.compile('Replaced:\\n[ ]+?(.*)')
    ignored_reg    = re.compile('(.*) providing (.*) is already installed')

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

    for result in results['results']:
      installed = installed_reg.search(result)
      if installed:
        entry['yum']['installed'].append(installed.group(1).strip())
        continue

      updated = updated_reg.search(result)
      if updated:
        entry['yum']['updated'].append(updated.group(1).strip())
        continue

      replaced = replaced_reg.search(result)
      if replaced:
        entry['yum']['replaced'].append(replaced.group(1).strip())
        continue

      ignored = ignored_reg.search(result)
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
    self.new_host(host)
    self.store_raw_output(host, res)
    self.failure(host)

  def runner_on_ok(self, host, res):
    self.new_host(host)

    if res['invocation']['module_name'] == 'setup':
      self.parse_setup_output(host, res)
    elif res['invocation']['module_name'] == 'yum':
      self.parse_yum_output(host, res)
    else:
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
    pass

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
    self.cache.cache_item(self.journal)
