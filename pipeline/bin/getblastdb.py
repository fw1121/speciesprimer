#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import hashlib
import wget
import tarfile
import argparse
import logging
import time
import filecmp
import subprocess

BASEURL = 'ftp://ftp.ncbi.nlm.nih.gov/blast/db/v5/'
extractedendings = [
    ".nhd", ".nhi", ".nhr", ".nin", ".nnd",
    ".nni", ".nog", ".nsq"]


def commandline():
    parser = argparse.ArgumentParser(
        prog="NCBI nt V5 database download",
        formatter_class=argparse.MetavarTypeHelpFormatter,
        description="Downloads the NCBI nt V5 database from NCBI",
        allow_abbrev=False)
    # define targetpath
    parser.add_argument(
        "-dbpath", "--dbpath", type=str, help="Path to save the DB")
    parser.add_argument(
        "-delete", "--delete", action="store_true", default=False,
        help="Delete the tar files after extraction to save Harddisk space")
    args = parser.parse_args()
    return args


def md5Checksum(filePath):
    with open(filePath, 'rb') as fh:
        m = hashlib.md5()
        while True:
            data = fh.read(8192)
            if not data:
                break
            m.update(data)
    return m.hexdigest()


def check_md5(inputfile):
    archivename = inputfile.split(".md5")[0]
    md5_file = inputfile
    with open(md5_file, "r") as f:
        for line in f:
            md5sumcheck = line.split("  ")[0].strip()
            filenamecheck = line.split("  ")[1].strip()
    if archivename == filenamecheck:
        logger("md5Checksum " + filenamecheck)
        filesum = md5Checksum(archivename)
        if filesum == md5sumcheck:
            logger("md5checksum correct " + str(md5sumcheck))
            return archivename
        else:
            logger("Error MD5 checksum not correct")
            logger("File: " + str(filesum))
            logger("Expected: " + str(md5sumcheck))
            raise


def compare_md5_archive(inputfile, delete):
    archivename = inputfile.split(".md5")[0]
    with open(inputfile, "r") as f:
        for line in f:
            md5sumcheck = line.split("  ")[0].strip()
            filenamecheck = line.split("  ")[1].strip()
    if archivename == filenamecheck:
        logger("md5Checksum " + filenamecheck)
        filesum = md5Checksum(archivename)
        if filesum == md5sumcheck:
            logger("No change in " + inputfile + " skip download")
            dbfile = check_md5(inputfile)
            extract_archives(dbfile, delete)
        else:
            os.rename(inputfile, os.path.join("md5_files", inputfile))
            url = BASEURL + "/" + archivename
            logger("Downloading..." + archivename)
            wget.download(url, archivename)
            dbfile = check_md5(inputfile)
            extract_archives(dbfile, delete)


def compare_md5_files(filename, delete):
    old_file = os.path.join("md5_files", filename)
    if filecmp.cmp(filename, old_file) is True:
        logger("No change in " + filename + " skip download")
        os.remove(filename)
    else:
        os.remove(old_file)
        os.rename(filename, os.path.join("md5_files", filename))
        archivename = filename.split(".md5")[0]
        url = BASEURL + "/" + archivename
        logger("Downloading..." + archivename)
        wget.download(url, archivename)
        dbfile = check_md5(filename)
        extract_archives(dbfile, delete)


def download_from_ftp(files, blastdb_dir, delete):
    os.chdir(blastdb_dir)
    for filename in files:
        check_extract = []
        try:
            for end in extractedendings:
                if filename.split(".tar.gz.md5")[0] + end in os.listdir("."):
                    check_extract.append(end)
            if check_extract == extractedendings:
                logger("Found extracted files, checking md5 file")
                if os.path.isfile(os.path.join("md5_files", filename)):
                    compare_md5_files(filename, delete)
                else:
                    logger(
                        "> Skip download of " + filename
                        + " found extracted files ")
                    archivename = filename.split(".md5")[0]
                    time.sleep(1)
            else:
                file_path = os.path.join("md5_files", filename + ".md5")
                if os.path.isfile(file_path):
                    # maybe only the md5 file was downloaded
                    if os.path.isfile(filename):
                        compare_md5_files(filename, delete)
                    else:
                        url = BASEURL + "/" + filename
                        logger("> Downloading..." + filename)
                        wget.download(url, filename)
                        dbfile = check_md5(filename)
                        extract_archives(dbfile, delete)
                else:
                    archivename = filename.split(".md5")[0]
                    if os.path.isfile(archivename):
                        compare_md5_archive(filename, delete)
                    else:
                        url = BASEURL + "/" + archivename
                        logger("> Downloading..." + archivename)
                        wget.download(url, archivename)
                        dbfile = check_md5(filename)
                        extract_archives(dbfile, delete)
                        os.rename(
                            filename, os.path.join("md5_files", filename))
            if os.path.isfile(filename):
                os.rename(filename, os.path.join("md5_files", filename))
        except Exception as exc:
            msg = "> error while working on " + filename + " check logfile"
            print(msg)
            print(exc)
            logger(msg)
            logging.error("error while working on " + filename, exc_info=True)
            time.sleep(2)

        except KeyboardInterrupt:
            logging.error(
                "KeyboardInterrupt while working on "
                + filename, exc_info=True)
            raise

    for files in os.listdir(blastdb_dir):
        if files.endswith(".tmp"):
            filepath = os.path.join(blastdb_dir, files)
            os.remove(filepath)


def extract_archives(dbfile, delete):
    check_extract = []
    extract_archive = []
    if dbfile is not None:
        for end in extractedendings:
            if not dbfile.split(".tar.gz")[0] + end in os.listdir("."):
                if dbfile not in extract_archive:
                    extract_archive.append(dbfile)
            else:
                check_extract.append(end)
        if len(extract_archive) > 0:
            for archive in extract_archive:
                logger("Extract archive " + dbfile)
                tar = tarfile.open(dbfile)
                tar.extractall()
                tar.close()
                check_extract = []
                for end in extractedendings:
                    if dbfile.split(".tar.gz")[0] + end in os.listdir("."):
                        check_extract.append(end)

    if check_extract == extractedendings:
        logger("Extracted " + dbfile)
        if delete is True:
            logger("Remove archive " + dbfile)
            os.remove(dbfile)


def get_md5files(blastdb_dir):
    os.chdir(blastdb_dir)
    command = [
        "wget", "-nv", "-nc", "-r", "--no-parent", "--no-directories",
        "--tries", "4", "-A", "nt_v5.*.tar.gz.md5", BASEURL]
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def check_output():
        while True:
            output = process.stdout.readline().decode().strip()
            if output:
                logger(output)
            else:
                break

    while process.poll() is None:
        check_output()


def get_filelist(blastdb_dir):
    filelist = []
    for filename in os.listdir(blastdb_dir):
        if os.path.isfile(filename):
            if (
                filename.startswith("nt_v5.")
                and filename.endswith(".tar.gz.md5")
            ):
                filelist.append(filename)
    filelist.sort()
    return filelist


def logger(string_to_log):
    print("\n" + string_to_log)
    logging.info(
        time.strftime(" %a, %d %b %Y %H:%M:%S: ", time.localtime())
        + string_to_log)


def get_DB(mode=False):
    today = time.strftime("%Y_%m_%d", time.localtime())
    if mode == "auto":
        import json
        pipe_bin = os.path.abspath(__file__)
        pipe_dir = pipe_bin.split("bin")[0]
        tmp_db_path = os.path.join(pipe_dir, 'tmp_config.json')
        with open(tmp_db_path, 'r') as f:
            for line in f:
                tmp_db = json.loads(line)
        delete = tmp_db['BLAST_DB']['delete']
        blastdb_dir = "/home/blastdb"

        logging.basicConfig(
            filename=os.path.join(
                "/", "home", "primerdesign",
                "speciesprimer_" + today + ".log"),
            level=logging.DEBUG, format="%(message)s")

    else:
        args = commandline()
        delete = args.delete
        if args.dbpath:
            if args.dbpath.endswith("/"):
                blastdb_dir = args.dbpath
            else:
                blastdb_dir = args.dbpath + "/"
        else:
            blastdb_dir = os.getcwd() + "/"

        logging.basicConfig(
            filename=os.path.join(
                blastdb_dir, "blastdb_download_" + today + ".log"),
            level=logging.DEBUG, format="%(message)s")

    try:
        os.mkdir(os.path.join(blastdb_dir, "md5_files"))
    except Exception as exc:
        pass

    logger("Start Download of NCBI nt BLAST database")
    get_md5files(blastdb_dir)
    filelist = get_filelist(blastdb_dir)
    download_from_ftp(filelist, blastdb_dir, delete)

    nt_nal_filepath = os.path.join(blastdb_dir, "nt_v5.nal")
    if os.path.isfile(nt_nal_filepath):
        logger("NCBI nt BLAST database is ready")
    else:
        logger(
            "Error nt.nal file for NCBI nt BLAST database is missing")


if __name__ == "__main__":
    get_DB()