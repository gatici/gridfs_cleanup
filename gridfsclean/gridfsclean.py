#!/usr/bin/python3
""" OSM Gridfs Cleanup CLI tool"""
from pymongo import MongoClient, errors as dberrors
from gridfs import GridFSBucket, GridFS
from gridfs import errors as fserrors
import logging
import argparse
import sys
import os


class GridfsClean:
    def __init__(self, mongo_uri: str):
        """
        :param mongo_uri: str  mongodb uri
        """
        self.client = MongoClient(mongo_uri)
        self.filedb = self.client["files"]
        self.fs = GridFS(self.filedb)
        self.fs_bucket = GridFSBucket(self.filedb)
        self.db = self.client.osm
        self.collections = [
            "vnfds",
            "nsds",
            "k8sclusters",
            "nsds_revisions",
            "vnfds_revisions",
        ]
        self.grid_file = "all_grid_files.txt"
        self.logger = logging.getLogger()
        logging.basicConfig(level=logging.DEBUG)
        self.map_operations = {
            "show": self.show_files,
            "rename": self.rename_files,
            "revert": self.revert_files,
            "delete": self.delete_files,
        }
        self.required_set, self.grid_set, self.unused_files = set(), set(), list()

    def find_required_files(self, collections: list) -> set:
        """
        Find all required files by id
        :param collections: list
        :return: required_set: set
        """
        count = 0
        # check collections exists or not
        for col in collections:
            if col in self.db.list_collection_names():
                collection = self.db[col]
                cursor = collection.find({})
                for document in cursor:
                    self.required_set.add(document.get("_id"))
                    count += 1
        print(f"{count} required file _id found according to given collections")
        return self.required_set

    def delete_gridfs_file(self, file_2delete: str) -> float:
        """
        Delete file from Gridfs
        :param file_2delete: str
        :return: number of deleted items for a given filename: float
        """
        count = 0
        #file_cursor = self.fs.find({"filename": {"$regex": "_renamed"}})
        file_cursor = self.fs.find({"filename": file_2delete}, no_cursor_timeout=True)
        for requested_file in file_cursor:
            if requested_file.metadata["type"] == "dir":
                dir_cursor = self.fs.find(
                    {"filename": {"$regex": "^{}(/|$)".format(file_2delete)}},
                    no_cursor_timeout=True,
                )
                for tmp in dir_cursor:
                    self.fs.delete(tmp._id)
                    count += 1
                    print(f"{tmp.filename} deleted")
            self.fs.delete(requested_file._id)
            count += 1
            print(f"{requested_file.filename} deleted")
        return count

    def rename_gridfs_file(self, src: str) -> float:
        """
        Rename one directory name. If destination exist, it replaces (deletes) existing directory
        :param src: source directory
        :return: tuple: (float, float) (delete_count, replace_count)
        """
        replace_count = 0
        if src:
            dst = src + "_renamed"
            src_cursor = self.fs_bucket.find(
                {"filename": {"$regex": "^{}(/|$)".format(src)}}, no_cursor_timeout=True
            )
            for src_file in src_cursor:
                if "_renamed" not in src_file.filename:
                    self.fs_bucket.rename(src_file._id, src_file.filename.replace(src, dst, 1))
                    replace_count += 1
                    print(f"{src_file._id} renamed with the name {src_file.filename}")
        return replace_count

    def write_to_file(self, file_2write: str) -> None:
        """
        Write all Gridfs content to a file
        :param file_2write: str
        :return: None
        """
        content = self.fs.list()
        with open(file_2write, "w") as file:
            file.seek(0)
            file.truncate()
            for line in content:
                file.write(line + "\n")
        print(f"All Gridfs content is written to {file_2write}")

    def find_unused(self) -> None:
        """
        Find all unused items
        :return: None
        """
        # write all Gridfs files names to a txt file
        self.write_to_file(self.grid_file)
        # find the unused files
        with open(self.grid_file, "r") as all_files:
            lines = all_files.readlines()
            self.required_set = self.find_required_files(self.collections)
            self.grid_set = {line.split("/")[0].strip("\n") for line in lines}
            self.unused_files = list(self.grid_set.difference(self.required_set))
        return

    def clean(self):
        self.unused_files.clear()
        self.grid_set.clear()
        self.required_set.clear()

    def show_files(self):
        """
        Prints the unused file id's to user
        :return:
        """
        self.find_unused()
        for item in self.unused_files:
            print(item)
        print(f"{len(self.unused_files)} unused id found")
        self.clean()

    def rename_files(self):
        """
        Renames the unused files by adding "_renamed" suffix
        :return: None
        """
        total_delete_count, total_replace_count = 0, 0
        self.find_unused()
        if self.unused_files:
            # Rename files
            for item in list(self.unused_files):
                delete_count, replace_count = self.rename_gridfs_file(item)
                total_delete_count += delete_count
                total_replace_count += replace_count
            print(f"Totally, {total_replace_count} files renamed")
        self.clean()

    def revert_files(self):
        """
        Revert back to the renamed filename to original filename
        :return: None
        """
        replace_count = 0
        renamed_cursor = self.fs_bucket.find(
            {"filename": {"$regex": "_renamed"}}, no_cursor_timeout=True
        )
        for renamed_file in renamed_cursor:
            renamed_filename = renamed_file.filename
            original_filename = renamed_filename.replace("_renamed", "")
            self.fs_bucket.rename(
                renamed_file._id,
                renamed_file.filename.replace(renamed_filename, original_filename, 1),
            )
            replace_count += 1
            print(f"{renamed_filename} reverted to original name {original_filename}")
        print(f"Totally {replace_count} files reverted to original")
        self.clean()

    def delete_files(self):
        """
        Delete all unused files
        return: None
        """
        total_delete_count = 0
        self.revert_files()
        self.find_unused()
        if self.unused_files:
            for item in self.unused_files:
                delete_count = self.delete_gridfs_file(item)
                total_delete_count += delete_count
            print(f"Totally, {total_delete_count} files deleted")
        self.clean()


def run_cli():
    """
    It gets the arguments from user and executes the operation depend on input and show the result to user.
    """
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--uri", type=str, required=True, help="OSM Mongodb URI")
        parser.add_argument(
            "--operation",
            type=str,
            required=True,
            help="Available operations for Gridfs unused files: "
            " show (list files), rename (rename files), revert (rename to original filename), delete (delete all unused files)",
        )
        args = parser.parse_args()

        if "mongodb://" not in args.uri:
            print(
                "Please insert the URI in this format: mongodb://10.152.183.118:27017/"
            )
            sys.exit()
        elif args.operation not in ["show", "rename", "revert", "delete"]:
            print(
                "Please insert the correct operation type. Available operations for Gridfs unused files: "
                "show (show files), rename (rename files), revert (rename to original filename),"
                "delete (delete all unused files)"
            )
            sys.exit()

        solution = GridfsClean(args.uri)
        solution.map_operations[args.operation]()
    except (
        IOError,
        fserrors.NoFile,
        fserrors.GridFSError,
        fserrors.CorruptGridFile,
        dberrors.PyMongoError,
        dberrors.ConnectionFailure,
        FileNotFoundError,
    ) as e:
        raise type(e)(f"Error {e} occured during fsmongo unused file investigation.")
