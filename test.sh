#!/bin/bash

# Clean up
rm -rf .mygit .git

echo "Testing MyGit"
echo "-------------"

chmod +x mygit.py

echo "> ./mygit.py init"
./mygit.py init

echo "hello world" > test.txt
echo "> ./mygit.py hash-object -w test.txt"
./mygit.py hash-object -w test.txt

echo "> ./mygit.py add test.txt"
./mygit.py add test.txt

echo "> ./mygit.py commit -m \"Initial commit\""
./mygit.py commit -m "Initial commit"

echo "> ./mygit.py branch feature"
./mygit.py branch feature

echo ""
echo "Contents of .mygit/objects:"
ls -lR .mygit/objects
