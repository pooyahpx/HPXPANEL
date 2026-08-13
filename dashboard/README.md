# Dashboard UI for HPXPANEL

Web UI for [HPXPANEL](https://github.com/pooyahpx/HPXPANEL): large-scale proxy management that supports both [Xray-core](https://github.com/XTLS/Xray-core) and
[WireGuard](https://www.wireguard.com/).

## Requirements

For development, you will only need Node.js installed on your environement.

### Node

[Node](http://nodejs.org/) is really easy to install & now include [NPM](https://npmjs.org/). This project has been developed on the Nodejs v20.x so if you faced any issue during installation that may
related to the node version, install Node with version >= v20

## Install

    Install the latest LTS version of Node.js
    git clone https://github.com/pooyahpx/HPXPANEL.git
    `bash cd HPXPANEL/dashboard`
    `bash curl -fsSL https://bun.sh/install | bash`
    `bash bun install`

### Configure app

Copy `example.env` to `.env` then set the backend api address:

    VITE_BASE_API=https://somewhere.com/

#### Environment variables

| Name          | Description                                                                                 |
| ------------- | ------------------------------------------------------------------------------------------- |
| VITE_BASE_API | The api url of the deployed backend ([HPXPANEL](https://github.com/pooyahpx/HPXPANEL)) |

## Start development server

    bun dev

## Simple build for production

    bun run build
