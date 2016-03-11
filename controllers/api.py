from flask import Blueprint, request, g, jsonify
from models import Orgy
from database import get_db_session
import re
import hmac
import mycorgi_app
import hashlib
api = Blueprint('api', __name__, subdomain='api')

YOUTUBE_REGEX = (r'(https?://)?(www\.)?'
                  '(youtube|youtu|youtube-nocookie)\.(com|be)/'
                  '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

@api.after_request
def after(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@api.route('/delete')
def delete_party():
    requestor_ip = request.remote_addr
    delete_token = request.args.get('delete_token')
    name = request.args.get('name')

    if (not name) or (not delete_token) or (not requestor_ip): 
        return 'Invalid request'

    db_session = get_db_session()
    party_to_delete = db_session.query(Orgy).filter(Orgy.name == name)\
                                            .one_or_none()
    if not party_to_delete:
        return 'Invalid request'

    if (not party_to_delete.creator_ip) or (party_to_delete.creator_ip == '127.0.0.1/32'):
        return 'Invalid request'
    else:
        creator_ip = party_to_delete.creator_ip.replace('/32','')

    # Additional sanity check
    if creator_ip != requestor_ip:
        return 'Invalid request'
    
    token_message = creator_ip + party_to_delete.name
    valid_delete_token = hmac.new(mycorgi_app.mycorgi_app.config['SECRET_DELETE_KEY'], token_message, hashlib.sha1).hexdigest()

    if delete_token == valid_delete_token:
        db_session.delete(party_to_delete)
        db_session.commit()
        print 'deleted party', party_to_delete.name
        return 'Party deleted! Make another one <a href="//my.corgiorgy.com">here</a>!'
    else:
        return 'Invalid request!'

@api.route('/check_name', methods=['POST'])
def check_name():
    name = request.form.get('name')
    if not name:
        return 'InvalidName'
    elif not re.search("^[a-zA-Z0-9\-]+$", name):
        return 'InvalidName'
    elif not len(name) < 64:
        return 'InvalidName'
    else:
        db_session = get_db_session()
        existing_party = db_session.query(Orgy)\
                                    .filter(Orgy.name.ilike(name))\
                                    .filter(Orgy.is_old == False)\
                                    .one_or_none()
        if existing_party:
            return 'InUse'
        else:
            return 'Success'

@api.route('/check_youtube', methods=['POST'])
def check_youtube():
    youtube_url = request.form.get('youtube_url')
    if not youtube_url:
        return 'InvalidYoutube'
    elif not re.search(YOUTUBE_REGEX, youtube_url):
        return 'InvalidYoutube'
    else:
        return 'Success'

@api.route('/create', methods=['POST'])
def create_party():
    # Required fields 
    name = request.form.get('name')
    foreground = request.form.get('foreground')
    background = request.form.get('background')
    direction = request.form.get('direction')
    # Optional fields
    youtube_url = request.form.get('youtube')
    creator_ip = request.remote_addr

    # Make sure foreground was included in POST
    if not foreground:
        return 'Missing foreground! Please upload a foreground image', 400
    # Validate image foreground image input and construct imgur URL
    if re.search(r"^[a-zA-Z0-9]+$", foreground):
        foreground_url = "http://i.imgur.com/" + foreground + ".gif"
    else:
        return 'Foreground image invalid! Please retry upload', 400 

    # Make sure background was included in POST 
    if not background:        
        return 'Missing background! Please upload a background image', 400 
    # Validate image background image input and construct imgur URL
    if re.search("^[a-zA-Z0-9]+$", background):
        background_url = "http://i.imgur.com/" + background + ".gif"
    else:
        return 'Background image invalid! Please retry upload', 400 

    # Make sure direction was included in POST
    if not direction:
        return 'Missing direction! Hey wat r u doin?', 400
    # Validate direction input and construct ltr/rtl boolean
    if direction == 'right':
        is_left_to_right = True
    elif direction == 'left':
        is_left_to_right = False
    else:
        return 'Invalid direction! Hey wat r u doing?', 400

    # Validate youtube URL
    if youtube_url:
        youtube_match = re.search(YOUTUBE_REGEX, youtube_url)
        if youtube_match:
            youtube_id = youtube_match.group(6) 
        else:
            return 'Invalid YouTube URL!', 400
    else:
        youtube_id = None

    # Make sure name was included in POST
    if not name:
        return 'Missing name! Please pick a name for your party', 400
    # Validate name
    elif not re.search("^[a-zA-Z0-9\-]+$", name):
        return 'Invalid name! Pick a different name', 400
    # Make sure name isn't too long to be a subdomain
    elif len(name) > 63:
        return 'Name too long! Pick a shorter name', 400
    # Forbid protected subdomains
    elif name.lower() in ['my', 'static', 'api', 'www']:
        return 'Forbidden name! Pick a different name', 400

    # Create DB session
    db_session = get_db_session()

    # Make sure name is not already taken
    existing_orgy = db_session.query(Orgy)\
                               .filter(Orgy.name.ilike(name))\
                               .filter(Orgy.is_old == False)\
                               .one_or_none()
    if existing_orgy:
        return name + ' already exists! Pick a different name', 400

    # Instantiate new party and commit to DB
    new_orgy = Orgy(name=name, is_old=False,
                    foreground_url=foreground_url,
                    background_url=background_url,
                    is_left_to_right=is_left_to_right, 
                    youtube_id=youtube_id, creator_ip=creator_ip)

    db_session.add(new_orgy)
    db_session.commit()
    # Return new party URL for client-side redirect target
    new_party_url = 'http://' + name.lower() + '.corgiorgy.com'
    print name, 'party:', new_party_url
    return new_party_url, 201
