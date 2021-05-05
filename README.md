# json2netns

JSON parsing Linux Network Namespace (netns) topology builder.

- What is a Linux Namespace - aka NetNS?
  - https://blog.scottlowe.org/2013/09/04/introducing-linux-network-namespaces/
- WHat is JSON?
  - https://www.json.org/

# Install

```console
pip install git+git://github.com/cooperlees/json2netns
```

# Usage

The script takes a JSON config gile and drives all from that.

## Configuration

It's JSON modeling the topology. TBA.

# Development

## Install

```console
python3 -m venv [--upgrade-deps] /tmp/tj
/tmp/tj/bin/pip install -r requirements_test.txt wheel
/tmp/tj/bin/pip install -e .
````

## Run Tests

```console
/tmp/tj/bin/ptr [-k] [--print-cov] [--debug]
```

- `-k`: keep venv ptr creates
- `--print-cov`: handy to see what coverage is on all files
- `--debug`: Handy to see all commands run so you can run a step manually