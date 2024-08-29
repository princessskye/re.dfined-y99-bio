from flask import Flask, render_template, request, redirect, url_for
import requests
import time
import threading
from aiotube import Search

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# API Key
api_key = 'YOUR_LAST_FM_API_KEY' #Enter yoour last.fm API key here.

# Global variable to track the monitoring status
monitoring_active = {}

# Initialize aiotube search instance
search = Search()

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

def get_youtube_link(song_name, artist_name):
    search_query = f'{song_name} {artist_name}'
    try:
        # Search for videos using aiotube
        results = search.videos(search_query, limit=1)
        if results and len(results) > 0:
            video_id = results[0]
            youtube_link = f'https://www.youtube.com/watch?v={video_id}'
            return youtube_link
        else:
            print('No results found.')
            return None
    except Exception as e:
        print(f'Error fetching YouTube link: {e}')
        return None

def update_y99_bio(auth_token, song_title, youtube_link, bio_template):
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

def monitor_task(username, auth_token, bio_template):
    last_song = None
    while monitoring_active.get(username, False):
        song_name, artist_name = get_current_song(api_key, username)
        if song_name and artist_name:
            song_title = f'Now Playing: {song_name} - {artist_name}'
            
            if song_title != last_song:
                youtube_link = get_youtube_link(song_name, artist_name)
                
                if update_y99_bio(auth_token, song_title, youtube_link, bio_template):
                    print(f'Bio updated with: {song_title} - {youtube_link}')
                    last_song = song_title
                else:
                    print('Error updating bio.')
                
        time.sleep(30)

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/start_monitoring', methods=['POST'])
def start_monitoring():
    username = request.form['lastfm_username']
    auth_token = request.form['y99_session_token']
    bio_template = request.form['bio_template']
    
    # Activate monitoring
    monitoring_active[username] = True
    
    # Start the monitoring thread
    thread = threading.Thread(target=monitor_task, args=(username, auth_token, bio_template))
    thread.start()
    
    return redirect(url_for('index'))

@app.route('/stop_monitoring', methods=['POST'])
def stop_monitoring():
    username = request.form['lastfm_username']
    monitoring_active[username] = False
    return redirect(url_for('index'))

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=5000, debug=True)
    app.run(port=5000)
