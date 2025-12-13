import os

from flask import Flask, render_template_string, request, send_file
import google.generativeai as genai  # type: ignore
from gtts import gTTS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Huxe Audio - Text to Podcast</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #0f0f0f;
            color: #ffffff;
        }
        h1 {
            text-align: center;
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 2rem;
        }
        .main-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 32px;
        }
        @media (max-width: 768px) {
            .main-container {
                grid-template-columns: 1fr;
            }
        }
        .input-section, .result-section {
            min-height: 400px;
        }
        .section-title {
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #666;
            margin-bottom: 16px;
        }
        .tabs {
            display: flex;
            gap: 0;
            margin-bottom: 0;
        }
        .tab {
            flex: 1;
            padding: 12px 24px;
            background: #1a1a1a;
            border: 1px solid #333;
            border-bottom: none;
            color: #888;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.2s;
            text-align: center;
        }
        .tab:first-child {
            border-radius: 8px 0 0 0;
        }
        .tab:last-child {
            border-radius: 0 8px 0 0;
        }
        .tab.active {
            background: #252525;
            color: #fff;
            border-color: #444;
        }
        .tab:hover:not(.active) {
            background: #222;
        }
        .tab-content {
            display: none;
            background: #252525;
            border: 1px solid #444;
            border-top: none;
            border-radius: 0 0 8px 8px;
            padding: 20px;
        }
        .tab-content.active {
            display: block;
        }
        textarea {
            width: 100%;
            height: 180px;
            padding: 16px;
            border: 1px solid #333;
            border-radius: 8px;
            font-size: 16px;
            background: #1a1a1a;
            color: #fff;
            resize: vertical;
        }
        textarea:focus, input[type="url"]:focus {
            outline: none;
            border-color: #0066ff;
        }
        input[type="url"] {
            width: 100%;
            padding: 16px;
            border: 1px solid #333;
            border-radius: 8px;
            font-size: 16px;
            background: #1a1a1a;
            color: #fff;
        }
        .url-hint {
            color: #666;
            font-size: 14px;
            margin-top: 8px;
        }
        .length-section {
            margin-top: 16px;
        }
        .length-label {
            font-size: 14px;
            color: #888;
            margin-bottom: 8px;
            display: block;
        }
        select {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid #333;
            border-radius: 8px;
            font-size: 16px;
            background: #1a1a1a;
            color: #fff;
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%23888' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10l-5 5z'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 16px center;
        }
        select:focus {
            outline: none;
            border-color: #0066ff;
        }
        button {
            width: 100%;
            padding: 16px 32px;
            font-size: 18px;
            background: #0066ff;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            margin-top: 16px;
        }
        button:hover { background: #0052cc; }
        button:disabled {
            background: #333;
            cursor: not-allowed;
        }
        .result-section {
            background: #1a1a1a;
            border-radius: 12px;
            padding: 24px;
        }
        .result-placeholder {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 300px;
            color: #444;
            text-align: center;
        }
        .result-placeholder-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }
        .audio-section {
            margin-bottom: 24px;
        }
        audio {
            width: 100%;
            margin: 12px 0;
        }
        .download-btn {
            background: #22c55e;
            text-decoration: none;
            display: inline-block;
            text-align: center;
            padding: 12px 24px;
            font-size: 16px;
            border-radius: 8px;
            color: white;
            border: none;
            cursor: pointer;
            width: 100%;
        }
        .download-btn:hover { background: #16a34a; }
        .script-section {
            margin-top: 24px;
        }
        .script-container {
            background: #0f0f0f;
            border-radius: 8px;
            padding: 16px;
            max-height: 300px;
            overflow-y: auto;
        }
        .script-line {
            padding: 8px 12px;
            margin-bottom: 8px;
            border-radius: 6px;
            font-size: 14px;
            line-height: 1.5;
        }
        .script-line.alex {
            background: rgba(59, 130, 246, 0.15);
            border-left: 3px solid #3b82f6;
        }
        .script-line.sam {
            background: rgba(168, 85, 247, 0.15);
            border-left: 3px solid #a855f7;
        }
        .script-line .host-name {
            font-weight: 600;
            margin-right: 4px;
        }
        .script-line.alex .host-name {
            color: #3b82f6;
        }
        .script-line.sam .host-name {
            color: #a855f7;
        }
        .error {
            color: #ff4444;
            padding: 16px;
            background: #1a1a1a;
            border-radius: 8px;
            margin-top: 16px;
        }
    </style>
</head>
<body>
    <h1>Huxe Audio</h1>
    <p class="subtitle">Turn any text or article into a podcast</p>

    <div class="main-container">
        <div class="input-section">
            <div class="section-title">Input</div>
            <form method="POST" id="generateForm">
                <div class="tabs">
                    <div class="tab active" onclick="switchTab('text')">Paste Text</div>
                    <div class="tab" onclick="switchTab('url')">From URL</div>
                </div>

                <div id="textTab" class="tab-content active">
                    <textarea name="text" id="textInput" placeholder="Paste your article, news, or any text here...">{{ text or '' }}</textarea>
                </div>

                <div id="urlTab" class="tab-content">
                    <input type="url" name="url" id="urlInput" placeholder="https://example.com/article" value="{{ url or '' }}">
                    <p class="url-hint">Paste any article URL - we'll extract the content automatically</p>
                </div>

                <input type="hidden" name="input_type" id="inputType" value="text">

                <div class="length-section">
                    <label class="length-label">Podcast Length</label>
                    <select name="length" id="lengthSelect">
                        <option value="short">Short (~1 min)</option>
                        <option value="medium" selected>Medium (~3 min)</option>
                        <option value="long">Long (~5 min)</option>
                    </select>
                </div>

                <button type="submit" id="submitBtn">Generate Podcast</button>
            </form>

            {% if error %}
            <div class="error">{{ error }}</div>
            {% endif %}
        </div>

        <div class="result-section">
            <div class="section-title">Output</div>

            {% if audio_file %}
            <div class="audio-section">
                <audio controls autoplay>
                    <source src="/audio/{{ audio_file }}" type="audio/mpeg">
                </audio>
                <a href="/download/{{ audio_file }}" style="text-decoration: none;">
                    <button type="button" class="download-btn">Download MP3</button>
                </a>
            </div>

            {% if script %}
            <div class="script-section">
                <div class="section-title">Script</div>
                <div class="script-container">
                    {% for line in script_lines %}
                        {% if line.host == 'alex' %}
                        <div class="script-line alex">
                            <span class="host-name">Alex:</span>{{ line.text }}
                        </div>
                        {% elif line.host == 'sam' %}
                        <div class="script-line sam">
                            <span class="host-name">Sam:</span>{{ line.text }}
                        </div>
                        {% endif %}
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            {% else %}
            <div class="result-placeholder">
                <div class="result-placeholder-icon">🎙️</div>
                <p>Your podcast will appear here</p>
                <p style="font-size: 14px;">Paste text or URL, then click Generate</p>
            </div>
            {% endif %}
        </div>
    </div>

    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            if (tab === 'text') {
                document.querySelector('.tab:first-child').classList.add('active');
                document.getElementById('textTab').classList.add('active');
                document.getElementById('inputType').value = 'text';
                document.getElementById('urlInput').value = '';
            } else {
                document.querySelector('.tab:last-child').classList.add('active');
                document.getElementById('urlTab').classList.add('active');
                document.getElementById('inputType').value = 'url';
                document.getElementById('textInput').value = '';
            }
        }

        document.getElementById('generateForm').onsubmit = function() {
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('submitBtn').textContent = 'Generating... (30-60 seconds)';
        };
    </script>
</body>
</html>
'''


def parse_script_lines(script):
    """Parse script into structured lines with host identification."""
    lines = []
    for line in script.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('Alex:'):
            lines.append({
                'host': 'alex',
                'text': line.replace('Alex:', '').strip()
            })
        elif line.startswith('Sam:'):
            lines.append({
                'host': 'sam',
                'text': line.replace('Sam:', '').strip()
            })
    return lines


def extract_text_from_url(url):
    """Fetch webpage and extract article text."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside',
                         'form', 'button', 'iframe', 'noscript']):
            tag.decompose()

        # Try to find main content
        article = soup.find('article') or soup.find('main') or soup.find('body')

        if article:
            # Get text and clean it up
            text = article.get_text(separator=' ', strip=True)
            # Remove extra whitespace
            text = ' '.join(text.split())
            return text

        return None
    except Exception as e:
        return None


def create_podcast_script(text, length='medium'):
    """Use Gemini to convert text into a 2-host podcast conversation."""
    # Length settings: word count targets
    length_config = {
        'short': {'words': 150, 'duration': '1 minute'},
        'medium': {'words': 350, 'duration': '3 minutes'},
        'long': {'words': 600, 'duration': '5 minutes'}
    }
    config = length_config.get(length, length_config['medium'])

    prompt = f"""You are writing a script for two friends having a casual, exciting conversation about something they just discovered. They're NOT doing a formal interview - they're genuinely reacting to interesting information.

HOSTS:
- Alex (male): The curious one. Gets excited easily. Asks "wait, really?" and "hold on, so you're saying...". Sometimes interrupts when excited.
- Sam (female): The explainer. Makes complex things simple. Uses "okay so here's the thing..." and "honestly though...". Laughs easily.

DIALOGUE TECHNIQUES (USE THESE!):
- Interruptions with "—": "Alex: And the thing is— Sam: —exactly what I was thinking!"
- Trailing off with "...": "Sam: I mean, it's kind of..."
- Reactions BEFORE explanations: "Oh wow! So basically..." not just "So basically..."
- Filler words: "like", "honestly", "I mean", "you know", "right?"
- One host finishing other's thought: "Alex: So it's like— Sam: —a game changer, yeah."
- Short rapid exchanges mixed with longer explanations
- Express emotions: surprise, confusion, humor, excitement
- Rhetorical questions: "Can you even imagine?", "Wild, right?"

WHAT TO AVOID:
- Long monologues (max 3 sentences per turn)
- Formal language ("Furthermore", "Indeed", "It is important to note")
- Perfect grammar (real people don't speak perfectly)
- Starting every line the same way
- Being too educational/lecture-y

STRUCTURE:
- Hook: Start mid-conversation, like we dropped in on them talking
- Build: Go back and forth, building excitement
- Peak: The "wow" moment or key insight
- End: Quick memorable takeaway, maybe a joke

FORMAT:
- TARGET LENGTH: Around {config['words']} words ({config['duration']} when spoken)
- Every line must start with "Alex: " or "Sam: "
- No stage directions, no parentheses, just dialogue

EXAMPLE OF GOOD FLOW:
Alex: Okay wait, I have to tell you about this thing I just read—
Sam: Oh no, what now? *laughs*
Alex: No no, it's actually cool! So apparently...
Sam: Wait, seriously? That's...
Alex: Right?! And here's the wild part—
Sam: —there's more?
Alex: So much more.

NOW CREATE A CONVERSATION ABOUT THIS:
{text[:4000]}"""

    response = model.generate_content(prompt)
    return response.text


def generate_audio(script):
    """Convert podcast script to audio using gTTS."""
    lines = script.strip().split('\n')
    audio_files = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        if line.startswith("Alex:"):
            text = line.replace("Alex:", "").strip()
            tld = 'us'  # American accent for Alex
        elif line.startswith("Sam:"):
            text = line.replace("Sam:", "").strip()
            tld = 'co.uk'  # British accent for Sam
        else:
            continue

        if text:
            filename = f"temp_audio_{i}.mp3"
            tts = gTTS(text=text, lang='en', tld=tld)
            tts.save(filename)
            audio_files.append(filename)

    return audio_files


def combine_audio_files(audio_files, output_file):
    """Combine multiple audio files into one."""
    with open(output_file, 'wb') as outfile:
        for audio in audio_files:
            if os.path.exists(audio):
                with open(audio, 'rb') as infile:
                    outfile.write(infile.read())

    # Clean up temp files
    for audio in audio_files:
        if os.path.exists(audio):
            os.remove(audio)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        input_type = request.form.get('input_type', 'text')
        text = ''
        url = ''

        if input_type == 'url':
            url = request.form.get('url', '').strip()
            if not url:
                return render_template_string(HTML_TEMPLATE,
                                              error="Please enter a URL")

            text = extract_text_from_url(url)
            if not text:
                return render_template_string(HTML_TEMPLATE,
                                              error="Could not extract text from that URL. Try a different article or paste the text directly.",
                                              url=url)
        else:
            text = request.form.get('text', '').strip()
            if not text:
                return render_template_string(HTML_TEMPLATE,
                                              error="Please enter some text")

        if len(text) < 50:
            return render_template_string(
                HTML_TEMPLATE,
                error="Not enough content found (need at least 50 characters). Try a different source.",
                text=text if input_type == 'text' else '',
                url=url if input_type == 'url' else '')

        # Get selected length
        length = request.form.get('length', 'medium')

        try:
            script = create_podcast_script(text, length)
            audio_files = generate_audio(script)

            if not audio_files:
                return render_template_string(
                    HTML_TEMPLATE,
                    error="Could not generate audio. Try different text.",
                    text=text if input_type == 'text' else '',
                    url=url if input_type == 'url' else '')

            output_file = "podcast_output.mp3"
            combine_audio_files(audio_files, output_file)

            # Parse script for display
            script_lines = parse_script_lines(script)

            return render_template_string(HTML_TEMPLATE,
                                          audio_file=output_file,
                                          script=script,
                                          script_lines=script_lines,
                                          text=text if input_type == 'text' else '',
                                          url=url if input_type == 'url' else '')

        except Exception as e:
            return render_template_string(HTML_TEMPLATE,
                                          error=f"Error: {str(e)}",
                                          text=text)

    return render_template_string(HTML_TEMPLATE)


@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_file(filename, mimetype='audio/mpeg')


@app.route('/download/<filename>')
def download_audio(filename):
    return send_file(filename,
                     as_attachment=True,
                     download_name='huxe_podcast.mp3')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
