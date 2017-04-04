import os
import subprocess
import sys

import appdirs


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)

    version = sys.argv[-1]
    delete = not not sys.argv[-2] == '-d'
    delete_only = not not sys.argv[-2] == '--d'

    try:
        subprocess.call('git -h')
        git_path = 'git'
    except:
        git_path = None

    # Assume Windows portable Git
    if git_path is None:
        github_dir = os.path.join(appdirs.user_data_dir(), 'GitHub')
        for d in os.listdir(github_dir):
            if d.startswith('PortableGit'):
                git_path = os.path.join(github_dir, d, 'cmd', 'git.exe')

    if git_path is None:
        raise OSError('Unable to find git executable.')

    cmds = [
        '{0} tag -a {1} -m "Version {1}"'.format(git_path, version),
        '{} push origin {}'.format(git_path, version)
    ]
    delete_cmd = '{} tag -d {}'.format(git_path, version)

    if delete:
        cmds.insert(0, delete_cmd)
    elif delete_only:
        cmds = [delete_cmd]

    for cmd in cmds:
        subprocess.call(cmd)

    print(cmds)


if __name__ == '__main__':
    main()
