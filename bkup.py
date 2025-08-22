#!/usr/bin/env python3

import shutil
from pathlib import Path
import argparse
from datetime import datetime
from logging import getLogger, basicConfig, DEBUG

LOGGING_FORMAT = '%(asctime)s.%(msecs)03d %(levelname)-8s %(module)s-%(funcName)s: %(message)s'
basicConfig(level=DEBUG, format=LOGGING_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')

logger = getLogger(__name__)


def backup(args):
    src_file = Path(args.filename)
    suffix = src_file.suffix
    dst_dir = Path(args.dir) if args.dir else src_file.parent
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_basefile = src_file.stem
    time = datetime.now() if args.current_time else datetime.fromtimestamp(src_file.stat().st_mtime)
    time_str = f'{time:%Y-%m-%d_%H%M%S}'
    dst_file = dst_dir / f'{dst_basefile}_{time_str}{suffix}'
    logger.debug(f'src: {src_file}, dst: {dst_file}')
    if args.move:
        shutil.move(src_file, dst_file)
    else:
        shutil.copy2(src_file, dst_file)


def main():
    parser = argparse.ArgumentParser(description='CLI tool for taking backup of file',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('filename', help='specify filename')
    parser.add_argument('-m', '--move', action='store_true', help='move file')
    parser.add_argument('-d', '--dir', help='specify destination directory[')
    parser.add_argument('--current-time', action='store_true', help='use current time')
    args = parser.parse_args()

    try:
        backup(args)
    except Exception as e:
        logger.error(f'Exception in args: {args}. e: {e}')
        raise e


if __name__ == '__main__':
    main()
