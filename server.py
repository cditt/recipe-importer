from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import json
import base64
import mimetypes
from dotenv import load_dotenv


app = Flask(__name__, static_url_path="")

CORS(
    app,
    resources={
        r"/recipe-import": {
            "origins": ["*"]
        }
    },
)
load_dotenv("/config/addons/recipe-importer/.env")
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY is missing")

client = OpenAI(api_key=api_key)

PROMPT = """
Read this handwritten recipe card and return ONLY valid JSON.

Use exactly this structure:
{
  "name": "Recipe Name",
  "ingredients": ["ingredient 1", "ingredient 2"],
  "steps": ["step 1", "step 2"]
}

Rules:
- name must be a string
- ingredients must be an array of strings
- steps must be an array of strings
- do not include any extra keys
- do not wrap the JSON in markdown
- if handwriting is unclear, make your best guess
"""

@app.post("/recipe-import")
def recipe_import():
    try:
        if "photo" not in request.files:
            return jsonify({"error": "No photo uploaded"}), 400

        photo = request.files["photo"]

        if not photo or not photo.filename:
            return jsonify({"error": "Invalid photo upload"}), 400

        mime_type = photo.mimetype or mimetypes.guess_type(photo.filename)[0] or "image/jpeg"
        image_bytes = photo.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": PROMPT},
                        {
                            "type": "input_image",
                            "image_url": f"data:{mime_type};base64,{image_b64}",
                        },
                    ],
                }
            ],
        )

        text = response.output_text.strip()

        if text.startswith("```"):
            lines = text.splitlines()
            lines = [line for line in lines if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()

        data = json.loads(text)

        return jsonify({
            "name": data.get("name", ""),
            "ingredients": data.get("ingredients", []),
            "steps": data.get("steps", []),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/")
def home():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8099)