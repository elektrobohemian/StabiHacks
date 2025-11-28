#!/bin/bash
# tar millions of files (the common shell wildcard will not extend to > 100,000 files (or far less)
find ./ -name "*.jpg" | cpio -ov --format=ustar > ppn_images_2025_11_27.tar
