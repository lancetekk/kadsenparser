#!/usr/bin/python3
import urllib.request, urllib.error, urllib.parse, argparse, logging, json, shutil
import os, sys, re, time
import http.client
import fileinput
from multiprocessing import Process

log = logging.getLogger('kadsensprung')
workpath = os.path.dirname(os.path.realpath(__file__))
args = None
kadse_url = 'https://kohlchan.net/{}/res/{}.json'
kadse_media = 'https://kohlchan.net'
byte_conversion = 2 ** 20  # MiB


def main():
    global args
    parser = Kadsenparser(description='kadsensprung: a lightweight mediadownloader for KADSE')
    parser.add_argument('thread', nargs=1, help='url of the thread (or filename; one url per line)')
    parser.add_argument('-q', '--quiet', action='store_true', help='remove non-essential logging')
    parser.add_argument('-b', '--use-board-ids', action='store_true', help='use thread ids and file ids instead of subject and original filename')
    parser.add_argument('-o', '--omit-size-check', action='store_true', help='skips calculating the total media size and '
                                                                             'the corresponding check against the available disk space')
    # parser.add_argument('-a', '--autoremove-dead', action='store_true', help='removes dead links from the file automatically')
    # parser.add_argument('-r', '--reload', action='store_true', help='reload the queue file every 5 minutes')
    args = parser.parse_args()
    if args.quiet:
        loglevel = logging.ERROR
    else:
        loglevel = logging.INFO
    logging.basicConfig(level=loglevel, format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    thread = args.thread[0].strip()
    if thread[:4].lower() == 'http':
        download_thread(thread)
    # else:
    #    download_from_file(thread)


def download_thread(thread):
    log.info('Downloading media from thread-URL %s', thread)
    thread_no = None
    board_shortcut = None
    try:
        thread_split = thread.split('/')
        thread_no = thread_split[5].split('.')[0]
        board_shortcut = thread_split[3]
    except IndexError:
        log.error('Thread argument is not a valid kadse-thread-link URL. Aborting.')
        exit()

    if thread_no.isnumeric():
        log.info('Board: /%s/, Thread: %s', board_shortcut, thread_no)
    else:
        log.error('Thread identifier should be numerical. Aborting.')
        exit()

    with urllib.request.urlopen(kadse_url.format(board_shortcut, thread_no)) as response:
        data = json.load(response)

    thread_dir_name = thread_no
    if (not args.use_board_ids) and (data['subject'] is not None) and (not len(data['subject']) == 0):
        thread_dir_name = data['subject']

    log.info('Saving files for thread : %s', thread_dir_name)

    directory = os.path.join(workpath, 'downloads', board_shortcut, thread_dir_name)
    if not os.path.exists(directory):
        os.makedirs(directory)

    total, used, free = shutil.disk_usage(directory)

    if not args.omit_size_check:
        total_bytes = 0
        for post in data['posts']:
            for file in post['files']:
                file_name = get_filepath(file)
                img_path = os.path.join(directory, file_name)
                if not os.path.exists(img_path):
                    total_bytes += file['size']
        if free > total_bytes:
            log.info('Free Memory in MiB: %s', round((free / byte_conversion), 2))
            log.info('Expected total MiB: %s', round((total_bytes / byte_conversion), 2))
        else:
            log.error('Preliminary size estimation indicates that the combined size of the attachments planned '
                      'for download is greater than the free disk capacity. Aborting.')
            log.error('Free Memory in MiB: %s', round((free / byte_conversion), 2))
            log.error('Expected total MiB: %s', round((total_bytes / byte_conversion), 2))
            exit()
    else:
        log.info('Omitting size check according to -o flag.')

    for post in data['posts']:
        for file in post['files']:
            file_name = get_filepath(file)
            img_path = os.path.join(directory, file_name)

            if not os.path.exists(img_path):  # avoid duplicate downloads
                mediaurl = kadse_media + file['path']
                log.info('Trying to download %s.', mediaurl)
                try:
                    # wget.download(mediaurl, img_path)  # seems discontinued
                    # urllib.request.urlretrieve(mediaurl, img_path)  # deprecated
                    with urllib.request.urlopen(mediaurl) as in_stream, open(img_path, 'wb') as out_file:  # wb: write, binary
                        shutil.copyfileobj(in_stream, out_file)

                except urllib.error.URLError:
                    log.error('%s could not be loaded.', mediaurl)
                    break


def get_filepath(file):
    if not args.use_board_ids:
        return file['originalName']
    else:
        return file['path'].split('/')[2]


class Kadsenparser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
