#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   centos_init.py
@Time    :   2020/03/02 11:43:43
@Author  :   
@Version :   1.0

Init Shell only in CentOS 7 x86_64:
1、Base Alter system conf:
    - /etc/sysctl.conf
    - disable SELINUX
    - disable firewalld、postfix
    - install base tools
    - hostname
    - add user && sudo
    - set yum source
    - sshd_config
4、App conf:

Issue:
2、$(yum list installed | grep docker) is None
3、Command '['curl', '-fsSL', 'get.docker.com', '-o', 'get-docker.sh']' returned non-zero exit status 28
"""

import os
import sys

from subprocess import check_call as run
from subprocess import call
from subprocess import Popen, PIPE

s_log, e_log = [], []


def simple_replace(file, source, target):
    """simple replace use sed.

    """
    return run(['sed', '-i', 's/{}/{}/g'.format(source, target), file])


def in_file(file, text):
    """
    """
    with open(file) as fp:
        for c in fp:
            if text in c:
                return True
    return False


def check_root():
    """check root.
    """
    if os.geteuid() == 0:
        return True
    else:
        return False


def base_conf():
    """alter conf

    """

    # +x rc.local
    run(['chmod', '+x', '/etc/rc.d/rc.local'])
    s_log.append('--> +x rc.local')

    # disable SELINUX
    Popen(['setenforce', '0'])
    simple_replace('/etc/selinux/config', 'SELINUX=enforcing',
                   'SELINUX=disabled')
    s_log.append('--> Disable SELINUX')

    # disable firewalld、postfix
    run('systemctl stop firewalld && systemctl disable firewalld', shell=True)
    run('systemctl stop postfix && systemctl disable postfix', shell=True)
    s_log.append('--> Disable firewalld、postfix')

    # enable ipv4 forward
    run("sed -ie '/net.ipv4.ip_forward = [01]/d' /etc/sysctl.conf", shell=True)
    run("echo -e 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf", shell=True)
    run(['/sbin/sysctl', '-p'])
    s_log.append('--> Add ipv4 forward')


def yum_conf():
    """alter some useful conf.

    """
    # alter yum source
    flag = False
    run([
        'mv', '/etc/yum.repos.d/CentOS-Base.repo',
        '/etc/yum.repos.d/CentOS-Base.repo.bak'
    ])
    p = Popen([
        'curl', '-o', '/etc/yum.repos.d/CentOS-Base.repo',
        'http://mirrors.aliyun.com/repo/Centos-7.repo'
    ],
              stderr=PIPE)
    flag = p.communicate()[1].decode('utf-8')
    if flag:
        run([
            'mv', '/etc/yum.repos.d/CentOS-Base.repo.bak',
            '/etc/yum.repos.d/CentOS-Base.repo'
        ])
        e_log.append('--> Alter Base.repo timeout.')
        e_log.append(flag)
    run(['rm', '-f', '*pel.repo'])
    p = Popen([
        'curl', '-o', '/etc/yum.repos.d/CentOS-Epel.repo',
        'http://mirrors.aliyun.com/repo/epel-7.repo'
    ],
              stderr=PIPE)
    flag = p.communicate()[1].decode('utf-8')
    if flag:
        e_log.append('--> Alter Epel.repo timeout.')
        e_log.append(flag)
    p = Popen(['yum', 'makecache'], stderr=PIPE)
    flag = p.communicate()[1].decode('utf-8')
    if flag:
        e_log.append('--> Yum makecache error.')
        e_log.append(flag)

    # install base tools
    p = Popen(
        "yum groupinstall -y 'Development Tools' && yum install -y gcc glibc gcc-c++ make net-tools telnet ntpdate tree wget curl vim mtr bash-completion git yum-utils deltarpm",
        shell=True,
        stderr=PIPE)
    flag = p.communicate()[1].decode('utf-8')
    if flag:
        e_log.append(flag)
    s_log.append('--> Install base tools success.')


def set_host(hostname):
    """set hostname and user

    """
    if hostname:
        run(['hostnamectl', 'set-hostname', hostname])
        s_log.append('--> Hostname is set to {}'.format(hostname))


def add_user(user):
    """add user with sudo

    """
    if in_file('/etc/passwd', user):
        e_log.append('--> User: {} duplicate.'.format(user))
        return
    run(['useradd', user])
    run("echo '!QAZ2wsx' | passwd --stdin {}".format(user), shell=True)
    run(['usermod', '-aG', 'wheel', user])
    s_log.append("--> User created !!!\nuser: {}\npasswd: {}".format(
        user, '!QAZ2wsx'))


def ssh_conf():
    """Ban root login

    """
    simple_replace('/etc/ssh/sshd_config', 'GSSAPIAuthentication yes',
                   'GSSAPIAuthentication no')
    simple_replace('/etc/ssh/sshd_config', '#UseDNS yes', 'UseDNS no')
    simple_replace('/etc/ssh/sshd_config', '#PermitRootLogin yes',
                   'PermitRootLogin no')
    simple_replace('/etc/ssh/sshd_config', '#PermitEmptyPasswords no',
                   'PermitEmptyPasswords no')
    simple_replace('/etc/ssh/sshd_config', '#PubkeyAuthentication yes',
                   'PubkeyAuthentication yes')
    run(['systemctl', 'restart', 'sshd'])
    s_log.append("--> Increase sshd service security")


def install_py3():
    """Install pyenv

    """
    if sys.version_info.major > 2:
        e_log.append('--> Already install python3.')
        return
    for i in os.listdir('/usr/bin'):
        if 'python3' in i:
            e_log.append('--> Already install python3.')
            return
    run(['bash', 'py3_install.sh'])


def install_docker(user=''):
    """Install docker

    """
    if not call('docker -v', shell=True):
        e_log.append('--> Already install docker.')
        return

    run('yum remove -y docker docker-client \
                  docker-client-latest \
                  docker-common \
                  docker-latest \
                  docker-latest-logrotate \
                  docker-logrotate \
                  docker-selinux \
                  docker-engine-selinux \
                  docker-engine',
        shell=True)

    p = Popen('yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo && yum makecache fast && sudo yum -y install docker-ce',
              shell=True,
              stderr=PIPE)
    flag = p.communicate()[1].decode('utf-8')
    if flag:
        e_log.append(flag)

    if not os.path.isdir('/etc/docker'):
        os.mkdir('/etc/docker')
    run(['cp', './sources/docker_daemon.json', '/etc/docker/daemon.json'])
    if user:
        run(['usermod', '-aG', 'docker', user])

    run('systemctl daemon-reload && systemctl enable docker && systemctl start docker',
        shell=True)

    p = Popen(['docker', 'run', 'hello-world'], stderr=PIPE)
    flag = p.communicate()[1].decode('utf-8')
    if flag:
        e_log.append(flag)

    # install docker-compose
    p = Popen(
        'curl -L https://get.daocloud.io/docker/compose/releases/download/1.25.4/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose',
        shell=True,
        stderr=PIPE)
    flag = p.communicate()[1].decode('utf-8')
    if flag:
        e_log.append('--> Install docker-compose error.')
        e_log.append(flag)
    run('chmod +x /usr/local/bin/docker-compose', shell=True)
    s_log.append('--> Install docker-compose success.')
    p = Popen(
        'curl -L https://raw.githubusercontent.com/docker/compose/1.24.1/contrib/completion/bash/docker-compose > /etc/bash_completion.d/docker-compose',
        shell=True,
        stderr=PIPE)
    flag = p.communicate()[1].decode('utf-8')
    if flag:
        e_log.append('--> Install bash_completion error.')
        e_log.append(flag)
    s_log.append('--> Install docker success.')


def uninstall_docker():
    """Uninstall docker

    """
    call('yum remove -y $(yum list installed | grep docker)', shell=True)
    # remove image container
    call(['rm', '-rf', '/var/lib/docker'])
    # remove config
    call(['rm', '-rf', '/etc/docker'])
    # remove old
    call('yum remove -y docker docker-client \
                  docker-client-latest \
                  docker-common \
                  docker-latest \
                  docker-latest-logrotate \
                  docker-logrotate \
                  docker-selinux \
                  docker-engine-selinux \
                  docker-engine',
          shell=True)
    if os.path.exists('/usr/local/bin/docker-compose'):
        os.remove('/usr/local/bin/docker-compose')
    if os.path.exists('/etc/bash_completion.d/docker-compose'):
        os.remove('/etc/bash_completion.d/docker-compose')

    s_log.append('--> Uninstall docker success.')


def item1():
    """Base init.

    """
    user = raw_input("Enter a username: ")
    host = raw_input("Enter a hostname[None]: ")
    base_conf()
    yum_conf()
    set_host(host)
    add_user(user)
    ssh_conf()
    install_py3()
    install_docker(user)


def item2():
    """Install python

    """
    install_py3()


def item3():
    """Install Docker

    """
    install_docker()


def item4():
    """Uninstall Docker

    """
    uninstall_docker()


switch = {'1': item1, '2': item2, '3': item3, '4': item4}

if __name__ == '__main__':

    if not check_root():
        print("Operate must be root.")
        exit(1)

    print('-' * 30)
    print('1、Base init.')
    print('2、Install Python3')
    print('3、Install Docker')
    print('4、Uninstall Docker')
    print('-' * 30)
    key = raw_input('Choose item: ')
    if key not in switch:
        print("Select item error.")
        exit(1)
    switch[key]()
    for item in s_log:
        print(item)
    for item in e_log:
        print(item)
