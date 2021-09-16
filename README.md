# json2netns

JSON parsing Linux Network Namespace (netns) topology builder.

# Install

From PyPI:

- `pip install json2netns`

From GitHub:
- `pip install git+git://github.com/cooperlees/json2netns`

# Concepts

- What is a Linux Namespace - aka NetNS?
  - https://blog.scottlowe.org/2013/09/04/introducing-linux-network-namespaces/
- WHat is JSON?
  - https://www.json.org/

The script takes a JSON config file and drives namespace creation from that JSON toplogy file.
Lets look at the following simple two network namespace topology:

![json2netns sample topology](https://user-images.githubusercontent.com/3005596/117493918-79af0d00-af28-11eb-96df-ba2f43d889f2.png)

We have two namespaces that have 1 direct connection via a veth. It also has a OOB (Out of Band)
set of interfaces that allow the main Linux Network Namespace to communicate with the netns directly.

- By default it even bridges with a physical interface to allow external packets to be routed into the netns if desired from a physical NIC.

## Configuration

The above topology is represented by [sample.json](https://github.com/cooperlees/json2netns/blob/main/src/json2netns/sample.json). This config is also used by unittests to ensure correct functioning. We can add to it over time as users require more features.

### Small 1 NS Example JSON Config

```json
{
    "namespaces": {
        "left": {
            "id": 1,
            "interfaces": {
                "left0": {
                    "prefixes": ["fd00::1/64", "10.1.1.1/24"],
                    "peer_name": "right0",
                    "type": "veth"
                },
                "lo": {
                    "prefixes": ["fd00:1::/64", "10.6.9.1/32"],
                    "type": "loopback"
                }
            },
            "oob": false,
            "routes": {
                "route1": {
                    "dest_prefix" : "10.6.9.6/32",
                    "next_hop_ip" : "10.1.1.2",
                    "egress_if_name" : ""
                },
                "route2": {
                    "dest_prefix" : "fd00:6::/64",
                    "next_hop_ip" : "fd00::2",
                    "egress_if_name" : ""
                }
            }
        }
    },
    "oob": {},
    "physical_int": ""
}
```

# Usage

After installing just point `json2netns` at a valid config file and run as
root *(in the future we could make it capability aware too - PR Welcome!)*.

- usage: json2netns [-h] [-d] [--validate] [--workers WORKERS] config action


## Actions

- **create**: Create the interfaces and namespaces + bring interfaces up
- **check**: Print the interface addressing + v4/6 routing tables to stdout
- **delete**: Remove the namespaces and all interfaces

# Development

The code has attempted to be object oriented first. Please try to use inheritance
and keep new interface types sub classes of Interface etc. for all code additions.

## Development 'editable' Install

```console
python3 -m venv [--upgrade-deps] /tmp/tj
/tmp/tj/bin/pip install -r requirements_test.txt
/tmp/tj/bin/pip install -e .
````

## Run Tests

For testing we use [ptr](https://github.com/facebookincubator/ptr/).

```console
/tmp/tj/bin/ptr [-k] [--print-cov] [--debug]
```

- `-k`: keep venv ptr creates
- `--print-cov`: handy to see what coverage is on all files
- `--debug`: Handy to see all commands run so you can run a step manually
