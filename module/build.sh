#/bin/bash

pyinstaller --onefile sav_cli.py \
  -n sav_cli_$(uname -s | tr 'A-Z' 'a-z')_$(uname -m | tr 'A-Z' 'a-z') \
  --add-data "./palworld_save_tools/libs/oodle/libs/Linux/liboo2corelinux64.so.9:palworld_save_tools/libs/oodle/libs/Linux" \
  --add-data "./palworld_save_tools/libs/oodle/libs/Linux/liboo2extlinux64.so.9:palworld_save_tools/libs/oodle/libs/Linux" \
  --add-binary "/usr/lib/x86_64-linux-gnu/libpython3.10.so.1.0:."
