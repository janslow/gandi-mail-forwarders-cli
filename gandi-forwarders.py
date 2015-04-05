#!/usr/bin/env python

from __future__ import print_function
import xmlrpclib
import argparse
import os
import sys

class colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

ERROR_MODIFY_FORWARDING_FAILED = colors.FAIL + "Failed: %s" + colors.ENDC
ERROR_MODIFY_FORWARDINGS_FAILED = colors.FAIL + colors.BOLD + "FAILED" + colors.ENDC

STATUS_GET_FROM_SERVER_START = colors.HEADER + "Getting existing forwardings..." + colors.ENDC
STATUS_GET_FROM_SERVER_SUCCESS = "Got %s forwardings from server."

STATUS_GET_FROM_FILE_START = colors.HEADER + "Parsing new forwardings..." + colors.ENDC
STATUS_GET_FROM_FILE_SUCCESS = "Got %s forwardings from file."

STATUS_CALCULATE_DIFFERENCE_SUCCESS = "Calculated difference (" + colors.OKGREEN + "%s to create" + colors.ENDC + ", " + colors.WARNING + "%s to update" + colors.ENDC + ", " + colors.WARNING + colors.BOLD + "%s to delete" + colors.ENDC + " and " + colors.OKBLUE + "%s to skip" + colors.ENDC + ")"
STATUS_CREATE_FORWARDING_START = colors.OKGREEN + "Creating" + colors.ENDC + " %s ... "
STATUS_UPDATE_FORWARDING_START = colors.WARNING + "Updating" + colors.ENDC + " %s ... "
STATUS_DELETE_FORWARDING_START = colors.WARNING + colors.BOLD + "Deleting" + colors.ENDC + " %s ... "

STATUS_MODIFY_FORWARDINGS_ATTEMPT_START = colors.HEADER + "Commit attempt %s..." + colors.ENDC
STATUS_MODIFY_FORWARDINGS_SUCCESS = colors.OKGREEN + colors.BOLD + "SUCCESS" + colors.ENDC

def print_forwardings(forwardings, defaultDomain=None):
  forwardings = forwardings.items()
  forwardings.sort(lambda x, y: cmp(x[0], y[0]))
  print("# Role Forwarders")
  for forwarding in [x for x in forwardings if not "." in x[0]]:
    print(forwarding_to_string(forwarding, defaultDomain))

  print("\n# Individual Forwarders")
  for forwarding in [x for x in forwardings if "." in x[0]]:
      print(forwarding_to_string(forwarding, defaultDomain))

def forwarding_to_string(forwarding, defaultDomain=None):
  normalised_destinations = [(x.replace("@" + defaultDomain, "@") if defaultDomain else x) for x in forwarding[1]]
  return "%s@ -> %s" % (forwarding[0], ", ".join(normalised_destinations))

def parse_forwardings(file, defaultDomain):
  forwardings = {}
  with open(file, "r") as fin:
    for line in fin.readlines():
      line = line.strip()
      if not line or line.startswith("#"):
        continue
      source, destinations = parse_forwarding(line, defaultDomain)
      forwardings[source] = destinations
  return forwardings

def parse_forwarding(line, defaultDomain):
  parts = line.split("->")
  if len(parts) != 2:
    raise Exception("Line has an invalid format: %s" % line)
  source, destinations = parts
  destinations = [x.strip() for x in destinations.split(",")]

  return (source.strip().replace("@", ""), [((x + defaultDomain) if x.endswith("@") else x) for x in destinations])

def update_forwardings(api_key, domain, old_forwardings, new_forwardings, dry_run):
  to_create = {}
  to_update = {}
  to_delete = []
  to_skip = []
  for source in (set(old_forwardings.keys()) | set(new_forwardings.keys())):
    old_destinations = old_forwardings.get(source)
    new_destinations = new_forwardings.get(source)
    if old_destinations and not new_destinations:
      to_delete.append(source)
    elif not old_destinations and new_destinations:
      to_create[source] = new_destinations
    else:
      if set(old_destinations) != set(new_destinations):
        to_update[source] = new_destinations
      else:
        to_skip.append(source)

  printStderr(STATUS_CALCULATE_DIFFERENCE_SUCCESS % (len(to_create), len(to_update), len(to_delete), len(to_skip)))
  execute_update_forwardings(api_key, domain, to_create, to_update, to_delete, dry_run)

def execute_update_forwardings(api_key, domain, to_create, to_update, to_delete, dry_run):
  api = get_api()

  attempt = 0
  changes = 1
  while changes > 0 and (to_create or to_update or to_delete):
    attempt += 1
    changes = 0

    printStderr(STATUS_MODIFY_FORWARDINGS_ATTEMPT_START % attempt)
    for source, destinations in to_create.items():
      result = create_forwarding(api, api_key, domain, source, destinations, dry_run)
      if result:
        del to_create[source]
        changes += 1
    for source, destinations in to_update.items():
      result = update_forwarding(api, api_key, domain, source, destinations, dry_run)
      if result:
        del to_update[source]
        changes += 1
    for source in to_delete:
      result = delete_forwarding(api, api_key, domain, source, dry_run)
      if result:
        to_delete.remove(source)
        changes += 1

  printStderr("\n")
  if to_create or to_update or to_delete:
    printStderr(ERROR_MODIFY_FORWARDINGS_FAILED)
  else:
    printStderr(STATUS_MODIFY_FORWARDINGS_SUCCESS)
      
def create_forwarding(api, api_key, domain, source, destinations, dry_run):
  printStderr(STATUS_CREATE_FORWARDING_START % forwarding_to_string((source, destinations), domain))
  if dry_run:
    return True
  else:
    try:
      api.domain.forward.create(api_key, domain, source, {
        "destinations": destinations
      })
      return True
    except xmlrpclib.Fault as e:
      printStderr(ERROR_MODIFY_FORWARDING_FAILED % e)
      return False

def update_forwarding(api, api_key, domain, source, destinations, dry_run):
  printStderr(STATUS_UPDATE_FORWARDING_START % forwarding_to_string((source, destinations), domain))
  if dry_run:
    return True
  else:
    try:
      api.domain.forward.update(api_key, domain, source, {
        "destinations": destinations
      })
      return True
    except xmlrpclib.Fault as e:
      printStderr(ERROR_MODIFY_FORWARDING_FAILED % e)
      return False

def delete_forwarding(api, api_key, domain, source, dry_run):
  printStderr(STATUS_DELETE_FORWARDING_START % source)
  if dry_run:
    return True
  else:
    try:
      api.domain.forward.delete(api_key, domain, source)
      return True
    except xmlrpclib.Fault as e:
      printStderr(ERROR_MODIFY_FORWARDING_FAILED % e)
      return False

def get_forwardings(api_key, domain):
  return { x["source"]:x["destinations"] for x in get_api().domain.forward.list(api_key, domain) }

def get_api():
  return xmlrpclib.ServerProxy('https://rpc.gandi.net/xmlrpc/')

def parse_args():
  parser = argparse.ArgumentParser(description='Updates Gandi email forwardings to match the forwardings specified in the file')
  parser.add_argument("-k", "--api-key", required=False, help="Gandi API key. Defaults to ")
  parser.add_argument("-D", "--domain", required=True, help="Domain to modify")
  parser.add_argument("-f", "--input-file", required=False, help="File to parse forwardings from. Ommit to fetch the current config.")
  parser.add_argument("--dry-run", action="store_true", help="Don't make any changes to the server")

  args = parser.parse_args()
  return args.api_key, args.domain, args.input_file, args.dry_run

def printStderr(*objs):
  # Print logging info to STDERR, otherwise it will get mixed in with the licence output.
  print(*objs, file=sys.stderr)

def main(api_key, domain, input_file, dry_run):
  api_key = api_key or os.environ.get("GANDI_API_KEY")
  if not api_key:
    raise Exception("No API key provided")

  printStderr(STATUS_GET_FROM_SERVER_START)
  old_forwardings = get_forwardings(api_key, domain)
  printStderr(STATUS_GET_FROM_SERVER_SUCCESS % len(old_forwardings))
  
  if input_file:
    printStderr(STATUS_GET_FROM_FILE_START)
    new_forwardings = parse_forwardings(input_file, domain)
    printStderr(STATUS_GET_FROM_FILE_SUCCESS % len(new_forwardings))

    update_forwardings(api_key, domain, old_forwardings, new_forwardings, dry_run)
  else:
    print_forwardings(old_forwardings, domain)

if __name__ == "__main__":
  api_key, domain, input_file, dry_run = parse_args()
  main(api_key, domain, input_file, dry_run)