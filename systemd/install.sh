#!/usr/bin/env bash
# Install systemd service and timer
mkdir -p ~/.config/systemd/user/
cp systemd/devpulse.service ~/.config/systemd/user/
cp systemd/devpulse.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now devpulse.timer
