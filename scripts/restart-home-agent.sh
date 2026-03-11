#!/usr/bin/env bash
set -eu

systemctl --user restart --no-block home-agent.service
