import glob
import os
import fnmatch
import subprocess
import argparse
import re

class Status:
    UNCHANGED = 0
    CREATED = 1
    MODIFIED = 2
    
def _get_argument_parser():
    parser = argparse.ArgumentParser()

    # General arguments    
    parser.add_argument('-r', dest='repo', action='store',
                        help='The path to the repo')
    
    usage = "usage: %prog [options]"
    
    return parser

def _locate(pattern, root):
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)

def _get_commit_message(status, dir, created, modified):
    name = dir[1:]
    
    if status == Status.CREATED:
        message = "Initial commit of '%s'.\n\n" + \
                  "Date-Created: %s\n" + \
                  "Date-Updated: %s\n" 
        message = message % (name, created, modified) 
    else:
        message = "Updates to '%s'.\n" % name 
                  
    return message 

def _status(dir):
    os.chdir(dir)
    output = subprocess.check_output(['git', 'status', dir, '--porcelain'])
    status = Status.UNCHANGED
    
    lines = output.split('\n')
    
    modified = False
    created = False
    
    
    for l in lines:
        match = re.search(r'^\?\? (.*)$',l)
        if match:
            status_path = match.group(1)
            if dir.endswith(status_path[0:len(status_path)-1]):
                created = True
                break
            else:
                modified = True
                break
        
        match = re.search(r'^M (.*)',l.strip())
        if match: 
            modified = True
    
    if created:
        status = Status.CREATED
    elif modified:
        status = Status.MODIFIED    
    
    return status
    

def _add_files(dir):
    os.chdir(dir)
    subprocess.check_call(['git', 'add', '-A', '*', ])

def _commit(msg, created, updated):
    
    date = updated
    
    if updated == '--':
        date = created
        
    iso_date = '%s 00:00:00' % date 
    
    subprocess.check_call(['git', 'commit', '-m', msg, '--date',iso_date, '--author', 'US DVA <va.gov>'])

class Commit:
    def __init__(self, dir, status, created, updated):
        self.dir = dir
        self.status = status
        self.created = created
        self.updated = updated
        
        if updated  == '--':
            self.sort_key = self.created
        else:
            self.sort_key = self.updated 

def _commit_files(config):
    files = _locate("info.txt", config.repo)
    dirs = []
    commits = []
    for f in files:
        d = f[0:f.rindex('/')]
        if not d in dirs:
            dirs.append(d)
            with open(f, 'r') as fp:
                lines = fp.readlines()
            created = lines[0].strip()
            modified = lines[1].strip()
            os.remove(f)
                
            status = _status(d) 
            if status != Status.UNCHANGED:
                commit = Commit(d, status, created, modified)
                commits.append(commit)
                
    # for by updated date 
    sorted_commits = sorted(commits, key=lambda commit: commit.sort_key)
    
    for commit in sorted_commits:        
        message = _get_commit_message(commit.status, 
                                      commit.dir.replace(config.repo, ''), 
                                      commit.created, 
                                      commit.updated)
        _add_files(commit.dir)
        _commit(message, commit.created, commit.updated)

def main():
    
    parser = _get_argument_parser()
    config = parser.parse_args()    
        
    _commit_files(config)
                
        
if __name__ == '__main__': 
    main() 