# virtualenv setup
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv -a /vagrant atp
workon atp
echo -e "\n\nworkon atp\ncd ovpr_atp" >> ~/.bashrc

cp ovpr_atp/.env.sample ovpr_atp/.env

# Django setup
pip install -r requirements/local.txt
cd ovpr_atp
source .env
python manage.py syncdb --migrate --noinput

#Project initialization
python manage.py setup_project
python manage.py createinitialrevisions