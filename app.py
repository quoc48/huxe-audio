import os

from flask import Flask, render_template_string, request, send_file
import google.generativeai as genai  # type: ignore
from gtts import gTTS

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
            max-width: 800px; 
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
        textarea { 
            width: 100%; 
            height: 200px; 
            padding: 16px;
            border: 1px solid #333;
            border-radius: 8px;
            font-size: 16px;
            background: #1a1a1a;
            color: #fff;
            resize: vertical;
        }
        textarea:focus {
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
        .result {
            margin-top: 32px;
            padding: 24px;
            background: #1a1a1a;
            border-radius: 8px;
        }
        audio { 
            width: 100%; 
            margin: 16px 0;
        }
        .download-btn {
            background: #22c55e;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }
        .download-btn:hover { background: #16a34a; }
        .loading {
            text-align: center;
            color: #888;
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
    <p class="subtitle">Paste any text - Get a podcast-style audio</p>

    <form method="POST" id="generateForm">
        <textarea name="text" placeholder="Paste your article, news, or any text here...">{{ text or '' }}</textarea>
        <button type="submit" id="submitBtn">Generate Podcast</button>
    </form>

    {% if audio_file %}
    <div class="result">
        <h3>Your Podcast is Ready!</h3>
        <audio controls autoplay>
            <source src="/audio/{{ audio_file }}" type="audio/mpeg">
        </audio>
        <a href="/download/{{ audio_file }}" class="download-btn" style="width:100%; margin-top:8px;">
            <button type="button" class="download-btn">Download MP3</button>
        </a>
    </div>
    {% endif %}

    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}

    <script>
        document.getElementById('generateForm').onsubmit = function() {
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('submitBtn').textContent = 'Generating... (this takes 30-60 seconds)';
        };
    </script>
</body>
</html>
'''


def create_podcast_script(text):
    """Use Gemini to convert text into a 2-host podcast conversation."""
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
- Keep it under 350 words
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
    """Combine multiple audio files into one (no ffmpeg needed)"""
    with open(output_file, 'wb') as outfile:
        for audio in audio_files:
            if os.path.exists(audio):
                with open(audio, 'rb') as infile:
                    outfile.write(infile.read())

    for audio in audio_files:
        if os.path.exists(audio):
            os.remove(audio)
    if os.path.exists('filelist.txt'):
        os.remove('filelist.txt')


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        text = request.form.get('text', '').strip()

        if not text:
            return render_template_string(HTML_TEMPLATE,
                                          error="Please enter some text")

        if len(text) < 50:
            return render_template_string(
                HTML_TEMPLATE,
                error="Please enter more text (at least 50 characters)",
                text=text)

        try:
            script = create_podcast_script(text)
            audio_files = generate_audio(script)

            if not audio_files:
                return render_template_string(
                    HTML_TEMPLATE,
                    error="Could not generate audio. Try different text.",
                    text=text)

            output_file = "podcast_output.mp3"
            combine_audio_files(audio_files, output_file)

            return render_template_string(HTML_TEMPLATE,
                                          audio_file=output_file,
                                          text=text)

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
    app.run(host='0.0.0.0', port=5000, debug=True)
