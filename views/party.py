from flask import Blueprint, render_template, request
from models import Orgy
from database import get_db_session
import hmac
import hashlib
import mycorgi_app

party = Blueprint('party', __name__)

# If coming in to a subdomain, that's a new party
@party.route('/', subdomain='<party_subdomain>')
def show_party(party_subdomain):
    db_session = get_db_session()
    party = db_session.query(Orgy)\
                      .filter(Orgy.name.ilike(party_subdomain))\
                      .filter(Orgy.is_old == False)\
                      .one_or_none()
    if not party:
        return 'Party not found! Make one <a href="//my.corgiorgy.com">here</a>!', 404
    
    if party.creator_ip:
        creator_ip = party.creator_ip.replace('/32','')
        if creator_ip == request.remote_addr:
            token_message = creator_ip + party.name  
            delete_token = hmac.new(mycorgi_app.mycorgi_app.config['SECRET_DELETE_KEY'], token_message, hashlib.sha1).hexdigest()
            delete_url = '?name='+party.name+'&delete_token='+delete_token
        else:
            delete_url = None
    return render_template('party.html', party=party, delete_url=delete_url)

# If coming to an unrecgnized path on 'my' subdomain,
# that's an old party
@party.route('/<path:old_party_name>', subdomain='my')
def show_old_party(old_party_name):
    db_session = get_db_session()
    party = db_session.query(Orgy)\
                      .filter(Orgy.name == old_party_name)\
                      .filter(Orgy.is_old == True)\
                      .one_or_none()
    if not party:
        return 'Party not found! Make one <a href="//my.corgiorgy.com">here</a>!', 404
    else:
        return render_template('party.html', party=party)
