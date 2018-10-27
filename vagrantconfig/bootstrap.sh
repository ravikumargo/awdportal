#!/usr/bin/env bash

# Edit the following to change the name of the database user that will be created:
APP_DB_USER=ovpr_atp
APP_DB_PASS=ovpr_atp

# Edit the following to change the name of the database that is created (defaults to the user name)
APP_DB_NAME=ovpr_atp

# Edit the following to change the version of MySQL that is installed
MYSQL_VERSION=5.5

debconf-set-selections <<< 'mysql-server-$MYSQL_VERSION mysql-server/root_password password rootpass'
debconf-set-selections <<< 'mysql-server-$MYSQL_VERSION mysql-server/root_password_again password rootpass'

apt-get update
apt-get install -y git python-pip python-dev libmysqlclient-dev mysql-server-$MYSQL_VERSION libldap2-dev libsasl2-dev libssl-dev

pip install virtualenvwrapper
pip install autoenv

if [ ! -f /var/log/databasesetup ];
then
    echo "CREATE USER '$APP_DB_USER'@'localhost' IDENTIFIED BY '$APP_DB_PASS'" | mysql -uroot -prootpass
    echo "CREATE DATABASE $APP_DB_NAME" | mysql -uroot -prootpass
    echo "GRANT ALL ON $APP_DB_NAME.* TO '$APP_DB_USER'@'localhost'" | mysql -uroot -prootpass
    echo "flush privileges" | mysql -uroot -prootpass

    touch /var/log/databasesetup
fi

# Make changes to .bashrc
if [ ! -f /var/log/bashsetup ];
then
	BASH_FILE="~/.bashrc"
	BASH_UPDATES="/vagrant/vagrantconfig/bashrc.sh"
	su - vagrant -c "cat $BASH_UPDATES >> $BASH_FILE"

	touch /var/log/bashsetup
fi