# Gandi Mail Forwarders CLI
An unofficial CLI for modifying the Gandi email forwarders.

## Setup
* API key for the Gandi domain API
* Python (tested with 2.7.9)

## Usage
```
# To list the current forwarders for a domain (example.com)
./gandi-forwarders.py -k "MyAPIKey" -D example.com

# To update the forwarders for a domain with the forwarders in forwardings.txt
./gandi-forwarders.py -k "MyAPIKey" -D example.com -f forwardings.txt
```

It is recommended to list the current forwarders and pipe it to a file, modify the file and then update the server with the modified file.

## Options
### API key
* `-k` option or `GANDI_API_KEY` environment variable (option takes precedence)
* Required, can be obtained from [Gandi's website](https://wiki.gandi.net/en/xml-api/activate)

### Domain
* `-D` option
* Required
* The domain who's forwarders should be fetched/modified

### Input File
* `-f` option
* Optional, ommit to fetch and print the current forwardings
* The file in the specified forwarding displaying what the target forwardings are

### Dry Run
* `--dry-run` flag
* Optional, include to not make any changes to the server, only print what would happen

## Process
1. Fetch the current list of forwardings from the server
2. Fetch the new list of forwardings from the input file
3. Compare the two and work out which forwardings need to be created, updated or deleted (or can be skipped)
4. Try to make the required changes. If a forwarding can't be deleted (because other addresses are forwarding to it) or can't be created/updated (because it's destinations aren't all created), skip it
5. If some changes failed but others succeeded, try step 4 again with the remaining forwardings.
6. If all the changes are completed, finish successfully. If some changes are failing and nothing is changing, abort and finish unsuccessfully.

## File format
* Blank lines and lines starting with a `#` are ignored
* One forwarder per line
* Forwarders must be in the following format `source -> destination1, destination2...`
  - Source email address (forward from)
  - `->`
  - Comma seperated list of destination email addresses (forward to)
* If a source/destination email address is in the current domain (i.e., the value of the "domain" option), the domain can be ommitted.
  - E.g., for the `example.com` domain, `foo@` is equivalent to `foo@example.com`

## File format examples
```
# Forward foo@example.com to bar@domain.com
foo@example.com -> bar@domain.com

# Shorthand for forwarding foo@example.com to bar@example.com
foo@ -> bar@

# Forward foo@example.com to bar@example.com and foo@domain.com
foo@ -> bar@, foo@domain.com
```
