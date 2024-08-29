from flask import Flask, render_template, request, redirect, url_for, session
import requests
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # SESSION TOKEN VARIABLE

# API-Daten
api_key = 'LAST_FM_API_HERE'
youtube_api_key = 'YOUTUBE_API_HERE'

def get_current_song(api_key, username):
    url = f'http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={username}&api_key={api_key}&format=json&limit=1'
    response = requests.get(url)
    data = response.json()
    if 'recenttracks' in data and len(data['recenttracks']['track']) > 0:
        track = data['recenttracks']['track'][0]
        song_name = track['name']
        artist_name = track['artist']['#text']
        return song_name, artist_name
    return None, None

def get_youtube_link(song_name, artist_name, youtube_api_key):
    search_query = f'{song_name} {artist_name}'
    url = f'https://www.googleapis.com/youtube/v3/search?part=snippet&q={search_query}&key={youtube_api_key}&maxResults=1&type=video'
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an error for HTTP codes 4xx/5xx
        data = response.json()

        if 'items' in data and len(data['items']) > 0:
            video_id = data['items'][0]['id']['videoId']
            return f'https://www.youtube.com/watch?v={video_id}'
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f'Error fetching YouTube link: {e}')
        return None

def update_y99_bio(auth_token, song_title, youtube_link, bio_template):
    # Ensure that song_title and youtube_link are strings, defaulting to an empty string if None
    song_title = song_title or ''
    youtube_link = youtube_link or ''
    
    bio = bio_template.replace('{song_title}', song_title).replace('{youtube_link}', youtube_link)
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {
        'description': bio,
        'auth': auth_token
    }
    y99_url = 'https://api2.y99.in/api.vf.random/api.php/user/profile/update?='
    response = requests.post(y99_url, headers=headers, data=data)
    return response.status_code == 200

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/start_monitoring', methods=['POST'])
def start_monitoring():
    session['lastfm_username'] = request.form['lastfm_username']
    session['y99_session_token'] = request.form['y99_session_token']
    session['bio_template'] = request.form['bio_template']
    return redirect(url_for('monitor'))

@app.route('/monitor', methods=['GET', 'POST'])
def monitor():
    if request.method == 'POST':
        if 'stop' in request.form:
            session.clear()
            return redirect(url_for('index'))
    
    last_song = None
    while 'lastfm_username' in session:
        song_name, artist_name = get_current_song(api_key, session['lastfm_username'])
        if song_name and artist_name:
            song_title = f'Now Playing: {song_name} - {artist_name}'
            
            if song_title != last_song:
                youtube_link = get_youtube_link(song_name, artist_name, youtube_api_key)
                
                if update_y99_bio(session['y99_session_token'], song_title, youtube_link, session['bio_template']):
                    print(f'Bio updated with: {song_title} - {youtube_link}')
                    last_song = song_title
                else:
                    print('Error updating bio.')
                
        time.sleep(30)
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=5000, debug=True) #Only uncomment if you want to pu it on a linux server. WARNING: Sessiontoken unencrypted.
    app.run(port=5000)
