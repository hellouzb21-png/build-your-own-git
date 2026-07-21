#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import zlib
import time

GIT_DIR = ".mygit"

def init():
    """Initializes a new .mygit directory structure."""
    if os.path.exists(GIT_DIR):
        print("Repository already initialized.")
        return

    os.makedirs(os.path.join(GIT_DIR, "objects"))
    os.makedirs(os.path.join(GIT_DIR, "refs", "heads"))

    with open(os.path.join(GIT_DIR, "HEAD"), "w") as f:
        f.write("ref: refs/heads/main\n")
    
    print(f"Initialized empty Git repository in {os.path.abspath(GIT_DIR)}")

def hash_object(file_path: str, write: bool = False) -> str:
    """Hashes a file and optionally writes it to the objects database."""
    if not os.path.exists(file_path):
        print(f"fatal: could not open '{file_path}' for reading: No such file or directory")
        sys.exit(1)

    with open(file_path, "rb") as f:
        content = f.read()

    # Git object header: <type> <size>\0
    header = f"blob {len(content)}\0".encode()
    store = header + content
    
    sha1 = hashlib.sha1(store).hexdigest()

    if write:
        # Create object directory (first 2 chars of hash)
        obj_dir = os.path.join(GIT_DIR, "objects", sha1[:2])
        if not os.path.exists(obj_dir):
            os.makedirs(obj_dir)
        
        # Write compressed object file (remaining 38 chars of hash)
        obj_path = os.path.join(obj_dir, sha1[2:])
        if not os.path.exists(obj_path):
            with open(obj_path, "wb") as f:
                f.write(zlib.compress(store))
    
    return sha1

def get_index():
    index_path = os.path.join(GIT_DIR, "index")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return json.load(f)
    return {}

def save_index(index):
    index_path = os.path.join(GIT_DIR, "index")
    with open(index_path, "w") as f:
        json.dump(index, f)

def add(file_path: str):
    """Hashes a file, saves it, and adds it to the index."""
    sha1 = hash_object(file_path, write=True)
    index = get_index()
    index[file_path] = sha1
    save_index(index)
    print(f"Added {file_path}")

def write_tree() -> str:
    """Creates a tree object from the current index."""
    index = get_index()
    if not index:
        print("Nothing to commit")
        sys.exit(1)

    # Format: <mode> <name>\0<20_byte_sha1>
    tree_content = b""
    # Sort for deterministic tree hash
    for path in sorted(index.keys()):
        sha1 = index[path]
        # Regular file mode is 100644
        entry = f"100644 {path}\0".encode() + bytes.fromhex(sha1)
        tree_content += entry
    
    header = f"tree {len(tree_content)}\0".encode()
    store = header + tree_content
    
    sha1 = hashlib.sha1(store).hexdigest()
    
    obj_dir = os.path.join(GIT_DIR, "objects", sha1[:2])
    if not os.path.exists(obj_dir):
        os.makedirs(obj_dir)
    
    obj_path = os.path.join(obj_dir, sha1[2:])
    if not os.path.exists(obj_path):
        with open(obj_path, "wb") as f:
            f.write(zlib.compress(store))
            
    return sha1

def get_head_ref():
    """Gets the path to the current branch ref from HEAD."""
    with open(os.path.join(GIT_DIR, "HEAD"), "r") as f:
        content = f.read().strip()
    if content.startswith("ref: "):
        return os.path.join(GIT_DIR, content[5:])
    return None

def get_current_commit():
    """Gets the hash of the current commit."""
    ref_path = get_head_ref()
    if ref_path and os.path.exists(ref_path):
        with open(ref_path, "r") as f:
            return f.read().strip()
    return None

def commit(message: str):
    """Creates a commit object and updates HEAD."""
    tree_sha1 = write_tree()
    parent_sha1 = get_current_commit()
    
    timestamp = int(time.time())
    timezone = "+0000"
    author = f"Jasur Shukurov <jasurshukurov701@gmail.com> {timestamp} {timezone}"
    
    commit_data = [f"tree {tree_sha1}"]
    if parent_sha1:
        commit_data.append(f"parent {parent_sha1}")
    commit_data.append(f"author {author}")
    commit_data.append(f"committer {author}")
    commit_data.append("")
    commit_data.append(message)
    commit_data.append("")
    
    commit_content = "\n".join(commit_data).encode()
    header = f"commit {len(commit_content)}\0".encode()
    store = header + commit_content
    
    sha1 = hashlib.sha1(store).hexdigest()
    
    obj_dir = os.path.join(GIT_DIR, "objects", sha1[:2])
    if not os.path.exists(obj_dir):
        os.makedirs(obj_dir)
    
    obj_path = os.path.join(obj_dir, sha1[2:])
    if not os.path.exists(obj_path):
        with open(obj_path, "wb") as f:
            f.write(zlib.compress(store))
            
    # Update branch ref
    ref_path = get_head_ref()
    with open(ref_path, "w") as f:
        f.write(sha1 + "\n")
        
    print(f"[{sha1[:7]}] {message}")

def branch(name: str):
    """Creates a new branch pointing to the current commit."""
    commit_sha1 = get_current_commit()
    if not commit_sha1:
        print("fatal: Not a valid object name: 'HEAD'. (Cannot create a branch from an empty repository)")
        sys.exit(1)
        
    branch_path = os.path.join(GIT_DIR, "refs", "heads", name)
    if os.path.exists(branch_path):
        print(f"fatal: A branch named '{name}' already exists.")
        sys.exit(1)
        
    with open(branch_path, "w") as f:
        f.write(commit_sha1 + "\n")
        
    print(f"Created branch {name}")

def main():
    parser = argparse.ArgumentParser(description="Build Your Own Git")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="Initialize a new, empty repository.")

    hash_parser = subparsers.add_parser("hash-object", help="Compute object ID and optionally create a blob from a file.")
    hash_parser.add_argument("-w", "--write", action="store_true", help="Actually write the object into the object database.")
    hash_parser.add_argument("file", help="File to hash")

    add_parser = subparsers.add_parser("add", help="Add file contents to the index.")
    add_parser.add_argument("file", help="File to add")

    commit_parser = subparsers.add_parser("commit", help="Record changes to the repository.")
    commit_parser.add_argument("-m", "--message", required=True, help="Commit message")

    branch_parser = subparsers.add_parser("branch", help="List, create, or delete branches.")
    branch_parser.add_argument("name", help="Branch name")

    args = parser.parse_args()

    if args.command == "init":
        init()
    elif args.command == "hash-object":
        print(hash_object(args.file, args.write))
    elif args.command == "add":
        if not os.path.exists(GIT_DIR):
            print("fatal: not a mygit repository")
            sys.exit(1)
        add(args.file)
    elif args.command == "commit":
        if not os.path.exists(GIT_DIR):
            print("fatal: not a mygit repository")
            sys.exit(1)
        commit(args.message)
    elif args.command == "branch":
        if not os.path.exists(GIT_DIR):
            print("fatal: not a mygit repository")
            sys.exit(1)
        branch(args.name)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
