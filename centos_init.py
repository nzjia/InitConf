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
"""

import os

from subprocess import check_call as run
from subprocess import Popen, PIPE


def simple_replace(file, source, target):
    """simple replace use sed.

    """
    return run(['sed', '-i', 's/{}/{}/g'.format(source, target), file])


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
    print('--> +x rc.local')

    # disable SELINUX
    Popen(['setenforce', '0'])
    simple_replace('/etc/selinux/config', 'SELINUX=enforcing',
                   'SELINUX=disabled')
    print('--> Disable SELINUX')

    # disable firewalld、postfix
    run('systemctl stop firewalld && systemctl disable firewalld', shell=True)
    run('systemctl stop postfix && systemctl disable postfix', shell=True)
    print('--> Disable firewalld、postfix')

    # enable ipv4 forward
    run("sed -ie '/net.ipv4.ip_forward = [01]/d' /etc/sysctl.conf", shell=True)
    run("echo -e 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf", shell=True)
    run(['/sbin/sysctl', '-p'])
    print('--> Add ipv4 forward')


def yum_conf():
    """alter some useful conf.

    """
    # alter yum source
    print("--> Alter ali yum source.")
    run([
        'mv', '/etc/yum.repos.d/CentOS-Base.repo',
        '/etc/yum.repos.d/CentOS-Base.repo.bak'
    ])
    p = Popen([
        'curl', '-o', '/etc/yum.repos.d/CentOS-Base.repo',
        'http://mirrors.aliyun.com/repo/Centos-7.repo'
    ],
              stdout=PIPE)
    if p.communicate()[1]:
        run([
            'mv', '/etc/yum.repos.d/CentOS-Base.repo.bak',
            '/etc/yum.repos.d/CentOS-Base.repo'
        ],
            stdout=PIPE)
        print(p.communicate()[1])
    p = Popen([
        'curl', '-o', '/etc/yum.repos.d/epel.repo',
        'http://mirrors.aliyun.com/repo/epel-7.repo'
    ],
              stdout=PIPE)
    if p.communicate()[1]:
        print(p.communicate()[1])
    p = Popen(['yum', 'makecache'], stdout=PIPE)
    if p.communicate()[1]:
        print(p.communicate()[1])

    # install base tools
    p = Popen(
        "yum groupinstall -y 'Development Tools' && yum install -y gcc glibc gcc-c++ make net-tools telnet ntpdate tree wget curl vim mtr bash-completion git",
        shell=True,
        stdout=PIPE)
    if p.communicate()[1]:
        print(p.communicate()[1])
    else:
        print('--> Install base tools success.')


def set_host(hostname):
    """set hostname and user

    """
    if hostname:
        run(['hostnamectl', 'set-hostname', hostname])
        print('--> Hostname is set to {}'.format(hostname))


def add_user(user):
    """add user with sudo

    """
    run(['useradd', user])
    run("echo '!QAZ2wsx' | passwd --stdin {}".format(user), shell=True)
    run(['usermod', '-aG', 'wheel', user])
    print("--> User created !!!\nuser: {}\npasswd: {}".format(
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
    print("Increase sshd service security")


def install_py3():
    """Install pyenv

    """
    run(['bash', 'py3_install.sh'])


def install_docker():
    """Install docker

    """
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
    run(['curl', '-fsSL', 'get.docker.com', '-o', 'get-docker.sh'])
    run('sh get-docker.sh --mirror Aliyun', shell=True)
    run(['cp', './sources/docker_daemon.json', '/etc/docker/daemon.json'])
    run('systemctl daemon-reload && systemctl enable docker && systemctl start docker', shell=True)
    run(['rm', '-f', 'get-docker.sh'])
    run(['docker', 'run', 'hello-world'])
    # install docker-compose
    run('curl -L https://github.com/docker/compose/releases/download/1.25.4/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose')
    run('curl -L https://raw.githubusercontent.com/docker/compose/1.24.1/contrib/completion/bash/docker-compose > /etc/bash_completion.d/docker-compose')


def uninstall_docker():
    """Uninstall docker

    """
    run('yum remove -y $(yum list installed | grep docker)', shell=True)
    # remove image container
    run(['rm', '-rf', '/var/lib/docker'])
    # remove config
    run(['rm', '-rf', '/etc/docker'])
    # remove old
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
    run(['sudo', 'rm', '/usr/local/bin/docker-compose'])


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
    install_docker()


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
