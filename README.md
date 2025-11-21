## Nano Banana Streamlit Playground

This app provides a Streamlit UI for the `fal-ai/nano-banana` image-generation model. It supports prompt-only and img2img workflows, multiple outputs per request, and automatic local saving.

### Local Development

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
streamlit run main.py
```

Set `FAL_KEY` before launching or edit `DEFAULT_API_KEY` if needed.

### Docker

1. **Build the image**

   ```bash
   docker build -t fal-nano-streamlit .
   ```

2. **Run the container**

   ```bash
   docker run -it --rm -p 8501:8501 \
     -e FAL_KEY=YOUR_FAL_KEY \
     -v "$(pwd)/outputs:/app/outputs" \
     fal-nano-streamlit
   ```

3. Open `http://localhost:8501` to use the UI. Generated images are saved inside `outputs/` on the host.

### Environment Variables

| Variable | Description |
| --- | --- |
| `FAL_KEY` | Required API key for fal.ai. Use secrets or env files; avoid hardcoding. |

### Repository Structure

```
.
├── main.py            # Streamlit application
├── templates/         # Legacy Flask template (reference styling)
├── outputs/           # Generated images (gitignored)
├── requirements.txt   # Python deps for local/docker use
├── Dockerfile         # Container image definition
└── README.md
```

