
# Copyright 2015 (c) Autologic Technology Ltd
# Author: Michael Crilly (mike@autologic.cm)
#
# This callback plugin is designed to work in conjunction with
# Autologic Journal, an Ansible auditing system. See
# http://autologic.cm/journal for more information
#
# License: MIT

import os
import datetime
import uuid
import json
import base64
import re 
import argparse
import urllib2 as http 
import sqlite3 as db 

JOURNAL_CALLBACK_DATABASE="%s/%s" % (os.environ['HOME'], '.journal_callback.cache')

class SQLiteCache(object):

  def __init__(self):
    self.connection = db.connect(JOURNAL_CALLBACK_DATABASE)
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

  def get_cache_items(self):
    get_items = '''
    SELECT * FROM callback_cache;
    '''

    c = self.connection.cursor()
    return c.execute(get_items).fetchall()

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

    self.cache = SQLiteCache()

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

  # def runner_on_skipped(self, host, item=None):
  #   pass

  # def runner_on_unreachable(self, host, res):
  #   pass

  # def runner_on_no_hosts(self):
  #   pass

  # def runner_on_async_poll(self, host, res, jid, clock):
  #   pass

  # def runner_on_async_ok(self, host, res, jid):
  #   pass

  # def runner_on_async_failed(self, host, res, jid):
  #   pass

  # def playbook_on_start(self):
  #   pass 

  # def playbook_on_notify(self, host, handler):
  #   pass

  # def playbook_on_no_hosts_matched(self):
  #   pass

  # def playbook_on_no_hosts_remaining(self):
  #   pass

  # def playbook_on_task_start(self, name, is_conditional):
  #   pass

  # def playbook_on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
  #   pass

  # def playbook_on_setup(self):
  #   pass

  # def playbook_on_import_for_host(self, host, imported_file):
  #   pass

  # def playbook_on_not_import_for_host(self, host, missing_file):
  #   pass

  # def playbook_on_play_start(self, name):
  #   pass

  def playbook_on_stats(self, stats):
    self.cache.cache_item(self.journal)

#
# Beginning of the CLI. Anything Ansible related stop here.
#

def prettyprint_json(data):
  print(json.dumps(data,separators=(',',':'),sort_keys=True,indent=4))

def prettyprint_cached_items(cache):
  print "%-10s%-30s%-10s%-20s%-20s" % ("ID", "Date", "Hosts", "Total Success", "Total Failed")

  for item in cache:
    decoded = json.loads(base64.b64decode(item[2]))

    total_hosts = len(decoded['data']['hosts'])
    total_success = 0
    total_failed = 0

    for host in decoded['data']['hosts']:
      total_success += decoded['data']['hosts'][host]['success']
      total_failed += decoded['data']['hosts'][host]['failed']

    print "%-10i%-30s%-10i%-20s%-20s" % (item[0], item[1], total_hosts, total_success, total_failed)

def jsonprint_cached_items(cache):
  fat_journal = []
  for item in cache:
    decoded = json.loads(base64.b64decode(item[2]))

    entry = {
      'cache_id': item[0],
      'cache_date': item[1],
      'cache_entry': decoded,
    }

    fat_journal.append(entry)

  prettyprint_json(fat_journal)

def find_the_blame(cache, host):
  blames = []
  for item in cache:
    decoded = json.loads(base64.b64decode(item[2]))

    if host in decoded['data']['hosts']:
      blame_blob = {
        'host': host,
        'date': item[1],
        'who': {},
        'tasks': [],
      }

      blame_blob['who']['user'] = decoded['data']['who']['USER']
      blame_blob['who']['sudo_user'] = decoded['data']['who']['SUDO_USER']

      for task in decoded['data']['hosts'][host]['tasks']:
        task_blob = {
          'module': task['ansible_results']['invocation']['module_name']
        }

        if 'changed' in task['ansible_results']:
          task_blob['changed'] = task['ansible_results']['changed']

        blame_blob['tasks'].append(task_blob)

      blames.append(blame_blob)

  prettyprint_json(blames)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()

  parser.add_argument('--pretty-list', help="Pretty print a list all the cached items", required=False, action='store_true')
  parser.add_argument('--list', help="Print a JSON document of all the cached items", required=False, action='store_true')
  parser.add_argument('--blame', help="Find out how the who, what, when, how of a given host", required=False, metavar="host")
  parser.add_argument('--export', help="Export all the data as a JSON list", required=False, action='store_true')

  args = parser.parse_args()

  db = SQLiteCache()
  cache = db.get_cache_items()

  if args.pretty_list:
    prettyprint_cached_items(cache)

  if args.list:
    jsonprint_cached_items(cache)

  if args.blame:
    find_the_blame(cache, args.blame)

  if args.export:
    exported = []
    for item in cache:
      exported.append(json.loads(base64.b64decode(item[2])))

    prettyprint_json(exported)
