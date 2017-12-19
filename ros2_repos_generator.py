#!/usr/bin/env python

"""ROS2 repos file generator.

script for generating ros2 repository files
in the form of gist files which can be used
to run run for external PR contributions.

using gist rest api as descripted here
https://developer.github.com/v3/gists/#create-a-gist
"""

import argparse
import getpass
import json
import os
import requests
from requests.auth import HTTPBasicAuth

api_url = 'https://api.github.com'
default_ros2_repos = 'https://raw.githubusercontent.com/' \
        'ros2/ros2/master/ros2.repos'


def _get_github_token():
    return os.environ.get('GITHUB_TOKEN')


def _get_username_and_password():
    username = input('github username: ')
    password = getpass.getpass('password: ')
    return username, password


def _create_gist(repos_content, token_param, auth):
    gist_file_name = 'external_contribution_repos.txt'
    jGist = json.dumps({
      'description': 'external contribution repos file',
      'public': True,
      'files': {
        gist_file_name: {
          'content': repos_content}}})

    response = requests.post(
            api_url + '/gists' + token_param,
            auth=auth,
            verify=True,
            data=jGist)
    if not response.ok:
        raise ConnectionError('failed to create gist')

    gist_details = json.loads(response.content.decode())
    return gist_details['files'][gist_file_name]['raw_url']


def _modify_master_repos(repos, pkg, url, branch):
    lines = repos.split('\n')

    pkg_found = False
    for idx, val in enumerate(lines):
        if pkg + ':' == val.lstrip():
            pkg_found = True
            print('found pkg to replace', val)
            lines[idx+2] = '{indent} url: {url}'.format(
                    indent=3 * ' ', url=url)
            lines[idx+3] = '{indent} version: {branch}'.format(
                    indent=3 * ' ', branch=branch)
            break

    if not pkg_found:
        raise ValueError('{pkg} does not exist in repos file'.format(
            pkg=pkg))
    return '\n'.join(lines)


def _fetch_master_repos_file(repos_file_url=default_ros2_repos):
    response = requests.get(repos_file_url)
    if not response.ok:
        raise ConnectionError('failed to fetch ros2 repos on {url}'.format(
            url=repos_file_url))
    return response.content.decode()


def _fetch_pr_info(pr_url):
    url_items = pr_url.split('/')
    org = url_items[3]
    repo = url_items[4]
    pr_id = url_items[6]
    if org is None:
        raise IndexError(
                'could not find any github organization in url {url}'.format(
                    url=pr_url))
    if repo is None:
        raise IndexError(
                'could not find any github repository in url {url}'.format(
                    url=pr_url))
    if pr_id is None or not pr_id.isdigit():
        raise IndexError(
                'could not find any pull request id in url {url}'.format(
                    url=pr_url))

    print('analyzing pull request url')
    print('found github organization: ', org)
    print('found github repo: ', repo)
    print('found pull request number:', pr_id)

    request_url = api_url + '/repos/{org}/{repo}/pulls/{pr_id}'.format(
            org=org, repo=repo, pr_id=pr_id)
    pr_info = requests.get(request_url)
    jPr = json.loads(pr_info.content.decode())

    repos_index = org + '/' + repo
    url = jPr['head']['repo']['html_url'] + '.git'
    branch = jPr['head']['ref']
    return repos_index, url, branch


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('pr_url', help='modify repos file with this PR url')
    args = parser.parse_args()

    auth = None
    token_param = ''
    github_token = _get_github_token()
    if github_token is None:
        username, password = _get_username_and_password()
        auth = HTTPBasicAuth(username, password)
    else:
        token_param = '?access_token=' + github_token

    pkg, url, branch = _fetch_pr_info(args.pr_url)
    ros2_repos = _fetch_master_repos_file()
    modified_repos = _modify_master_repos(ros2_repos, pkg, url, branch)
    gist_url = _create_gist(modified_repos, token_param, auth)

    print('new gist url:\n{gist_url}'.format(gist_url=gist_url))
