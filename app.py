import asyncio
import os

from flask import Flask, render_template_string, request, send_file
import google.generativeai as genai  # type: ignore
import edge_tts

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
    prompt = f"""You are writing a script for a casual, engaging podcast between two friends who are excited about what they're discussing.

HOSTS:
- Alex (male): Curious, asks good questions, reacts genuinely with "wow", "wait really?", "that's crazy"
- Sam (female): Knowledgeable but not preachy, explains things simply, uses phrases like "honestly", "here's the thing", "right?"

STYLE RULES:
- Sound like real friends talking, NOT a formal interview
- Include natural reactions: "Oh interesting!", "Hmm", "Wait, so..."
- Hosts can interrupt or build on each other's points
- Use casual language: contractions, simple words
- Add brief moments of humor or surprise
- Keep energy up - they're genuinely interested in this topic

FORMAT:
- Keep it under 400 words total
- Format each line as "Alex: ..." or "Sam: ..."
- Start with a hook that grabs attention
- End with a memorable takeaway

TEXT TO DISCUSS:
{text[:4000]}"""

    response = model.generate_content(prompt)
    return response.text


async def generate_audio(script):
    """Convert podcast script to audio using Edge-TTS."""
    lines = script.strip().split('\n')
    audio_files = []

    voice_alex = "en-US-GuyNeural"
    voice_sam = "en-US-JennyNeural"

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        if line.startswith("Alex:"):
            voice = voice_alex
            text = line.replace("Alex:", "").strip()
        elif line.startswith("Sam:"):
            voice = voice_sam
            text = line.replace("Sam:", "").strip()
        else:
            continue

        if text:
            filename = f"temp_audio_{i}.mp3"
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(filename)
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
            audio_files = asyncio.run(generate_audio(script))

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
