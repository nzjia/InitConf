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

from subprocess import call, check_call, Popen, PIPE

s_log, e_log = [], []


def simple_replace(file, source, target):
    """simple replace use sed.

    """
    return check_call(['sed', '-i', 's/{}/{}/g'.format(source, target), file])


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
    call(['chmod', '+x', '/etc/rc.d/rc.local'])

    # disable SELINUX
    call(['setenforce', '0'])
    simple_replace('/etc/selinux/config', 'SELINUX=enforcing',
                   'SELINUX=disabled')

    # disable firewalld、postfix
    call('systemctl stop firewalld && systemctl disable firewalld',
               shell=True)
    call('systemctl stop postfix && systemctl disable postfix',
               shell=True)
    s_log.append('--> Disable firewalld、postfix')

    # enable ipv4 forward
    call("sed -ie '/net.ipv4.ip_forward = [01]/d' /etc/sysctl.conf",
               shell=True)
    call("echo -e 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf",
               shell=True)
    call(['/sbin/sysctl', '-p'])

    # check
    if oct(os.stat('/etc/rc.d/rc.local').st_mode)[-1] in '751':
        s_log.append('--> +x rc.local')
    else:
        e_log.append('--> +x re.local E.')
    p = Popen(['getenforce'], stdout=PIPE, stderr=PIPE)
    flag = p.communicate()
    if flag[0].decode('utf-8') == 'Disabled\n':
        s_log.append('--> Disable SELINUX')
    else:
        e_log.append('--> Disable SELINUX E. {}'.format(
            flag[1].decode('utf-8')))
    if in_file('/etc/sysctl.conf', 'net.ipv4.ip_forward = 1'):
        s_log.append('--> Add ipv4 forward')
    else:
        e_log.append('--> Add ipv4 forward E.')


def yum_conf():
    """alter some useful conf.

    """
    # alter yum source
    check_call([
        'mv', '/etc/yum.repos.d/CentOS-Base.repo',
        '/etc/yum.repos.d/CentOS-Base.repo.bak'
    ])
    check_call([
        'curl', '-o', '/etc/yum.repos.d/CentOS-Base.repo',
        'http://mirrors.aliyun.com/repo/Centos-7.repo'
    ])

    check_call(['rm', '-f', '*pel.repo'])
    check_call([
        'curl', '-o', '/etc/yum.repos.d/CentOS-Epel.repo',
        'http://mirrors.aliyun.com/repo/epel-7.repo'
    ])
    check_call(['chmod', '+x', '/etc/yum.repos.d/CentOS-Epel.repo'])

    # check
    if in_file('/etc/yum.repos.d/CentOS-Base.repo',
               'mirrors.aliyun.com') and in_file(
                   '/etc/yum.repos.d/CentOS-Epel.repo', 'mirrors.aliyun.com'):
        s_log.append('--> Curl Aliyun repo.')
    else:
        e_log.append('--> Curl Aliyum repo E.')
        call([
            'cp', '/etc/yum.repos.d/CentOS-Base.repo.bak',
            '/etc/yum.repos.d/CentOS-Base.repo'
        ])

    check_call(['yum', 'makecache'])

    # install base tools
    call(
        "yum groupinstall -y 'Development Tools' && yum install -y gcc glibc gcc-c++ make net-tools telnet ntpdate tree wget curl vim mtr bash-completion git yum-utils deltarpm",
        shell=True)

    s_log.append('--> Install base tools success.')


def set_host(hostname):
    """set hostname and user

    """
    if hostname:
        p = call(['hostnamectl', 'set-hostname', hostname])
        if not p:
            s_log.append('--> Hostname is set to {}'.format(hostname))
        else:
            e_log.append('--> Hostname set E.')


def add_user(user):
    """add user with sudo

    """
    if in_file('/etc/passwd', user):
        e_log.append('--> User: {} duplicate.'.format(user))
        return
    check_call(['useradd', user])
    check_call("echo '!QAZ2wsx' | passwd --stdin {}".format(user), shell=True)
    check_call(['usermod', '-aG', 'wheel', user])
    if in_file('/etc/passwd', user):
        s_log.append("--> User created !!!\nuser: {}\npasswd: {}".format(
            user, '!QAZ2wsx'))
    else:
        e_log.append("--> User create E.")


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
    check_call(['systemctl', 'restart', 'sshd'])
    if in_file('/etc/ssh/sshd_config', 'GSSAPIAuthentication no') and in_file(
            '/etc/ssh/sshd_config', 'PermitRootLogin no') and in_file(
                '/etc/ssh/sshd_config', 'PermitEmptyPasswords no') and in_file(
                    '/etc/ssh/sshd_config', 'PubkeyAuthentication yes'):
        s_log.append("--> Increase sshd service security")
    else:
        e_log.append('--> Increase sshd service security E.')


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
    call(['bash', 'py3_install.sh'])
    for i in os.listdir('/usr/bin'):
        if 'python3' in i:
            s_log.append('--> Install python3 success.')
    e_log.append('--> Install python3 E.')


def install_docker(user=''):
    """Install docker

    """
    if not call('docker -v', shell=True):
        e_log.append('--> Already install docker.')
        return

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

    call(
        'yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo && yum makecache fast && sudo yum -y install docker-ce',
        shell=True)

    if not os.path.isdir('/etc/docker'):
        os.mkdir('/etc/docker')
    call(
        ['cp', './sources/docker_daemon.json', '/etc/docker/daemon.json'])
    if user:
        check_call(['usermod', '-aG', 'docker', user])

    call(
        'systemctl daemon-reload && systemctl enable docker && systemctl start docker',
        shell=True)

    p = call(['docker', 'check_call', 'hello-world'], stderr=PIPE)
    if not p:
        s_log.append('--> Install docker success.')
    else:
        e_log.append('--> Install docker E.')
        return

    # install docker-compose
    call(
        'curl -L https://get.daocloud.io/docker/compose/releases/download/1.25.4/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose',
        shell=True)
    check_call('chmod +x /usr/local/bin/docker-compose', shell=True)
    call(
        'curl -L https://raw.githubusercontent.com/docker/compose/1.24.1/contrib/completion/bash/docker-compose > /etc/bash_completion.d/docker-compose',
        shell=True)
    if os.path.exists('/etc/bash_completion.d/docker-compose'
                      ) and os.path.exists('/usr/local/bin/docker-compose'):
        s_log.append('--> Install docker-compose && completion success.')
    else:
        e_log.append('--> Install docker-compose && completion E.')


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

    print('*' * 30)
    for item in e_log:
        print(item)
    print('*' * 30)
    for item in s_log:
        print(item)
    print('*' * 30)
