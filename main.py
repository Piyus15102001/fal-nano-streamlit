import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from urllib.request import urlretrieve

import requests
import streamlit as st
import fal_client

DEFAULT_API_KEY = "5cdde8f9-430e-4c00-97b6-4096ba7696fd:0d2bdae28676d0ba51410ba2d3ff5e40"
OUTPUT_DIR = Path("outputs")


def _load_api_key() -> str:
    key = os.environ.get("FAL_KEY") or DEFAULT_API_KEY.strip()
    if not key or key == "REPLACE_WITH_FAL_KEY":
        raise RuntimeError(
            "FAL API key missing. Set the FAL_KEY environment variable or update DEFAULT_API_KEY."
        )
    return key


def on_queue_update(update):
    if isinstance(update, fal_client.InProgress):
        # Only show important messages, not every log
        if update.logs:
            latest_log = update.logs[-1]
            message = latest_log.get("message", "")
            if message and "progress" in message.lower():
                pass  # Skip progress messages to reduce spam


def _extract_image_payload(result_obj: Any, save_local: bool = True) -> List[Dict[str, str]]:
    if isinstance(result_obj, dict):
        result_dict = result_obj
    elif hasattr(result_obj, "data"):
        result_dict = result_obj.data
    else:
        raise TypeError("Result is neither dict-like nor exposes a 'data' attribute.")

    images = result_dict.get("images")
    if not images:
        data = result_dict.get("data", {})
        images = data.get("images")

    if not images:
        raise ValueError("No images were found in the response.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image_payload = []
    
    for idx, image in enumerate(images, start=1):
        url = image.get("url")
        if not url:
            continue
        
        filename = image.get("file_name") or f"image_{idx}.png"
        local_path = None
        
        if save_local:
            try:
                destination = OUTPUT_DIR / filename
                urlretrieve(url, destination)
                local_path = str(destination.resolve())
                # Don't show success message for each image to reduce spam
            except Exception as e:
                st.warning(f"⚠️ Failed to save image locally: {e}")
        
        image_payload.append(
            {
                "url": url,
                "file_name": filename,
                "local_path": local_path,
            }
        )

    if not image_payload:
        raise ValueError("No downloadable image URLs were returned.")

    return image_payload


def _upload_local_path(temp_path: Path) -> str:
    try:
        return fal_client.upload_file(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)


def _upload_user_image(uploaded_file) -> str:
    """Persist the incoming file briefly, upload it to fal's CDN, then clean up."""
    suffix = Path(uploaded_file.name).suffix if hasattr(uploaded_file, 'name') else ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        temp_path = Path(tmp.name)

    return _upload_local_path(temp_path)


def _upload_remote_image(url: str) -> str:
    """Download remote image (HTTP/HTTPS), store temporarily, upload to fal CDN."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(response.content)
        temp_path = Path(tmp.name)

    return _upload_local_path(temp_path)


def _build_prompt_payload(prompt: str, preserve_identity: bool) -> Dict[str, str]:
    """Return payload used inside the fal input object."""
    main_prompt = prompt.strip()
    negative_prompt = None

    if preserve_identity:
        main_prompt = (
            f"{main_prompt} | Keep the original person's face, facial features, skin tone, "
            "hair style, pose, and clothing exactly the same; only apply the described effect "
            "to the surroundings."
        )
        negative_prompt = (
            "different person, altered face, changed facial structure, swapped outfit, "
            "new clothing, distorted identity, deformed face"
        )

    payload: Dict[str, str] = {"prompt": main_prompt}
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
    return payload


def generate_images(
    prompt: str, 
    *, 
    image_url: Optional[str] = None, 
    preserve_identity: bool = False,
    num_images: int = 1,
    aspect_ratio: str = "1:1"
) -> List[Dict[str, str]]:
    arguments: Dict[str, Any] = _build_prompt_payload(prompt, preserve_identity)
    if image_url:
        arguments["image_urls"] = [image_url]
    
    # Add num_images and aspect_ratio to arguments
    if num_images > 1:
        arguments["num_images"] = num_images
    arguments["aspect_ratio"] = aspect_ratio

    result = fal_client.subscribe(
        "fal-ai/nano-banana",
        arguments=arguments,
        path="edit" if image_url else None,
        with_logs=True,
        on_queue_update=on_queue_update,
    )
    return _extract_image_payload(result, save_local=True)


# Initialize API key
fal_client.api_key = _load_api_key()
os.environ["FAL_KEY"] = fal_client.api_key

# Custom CSS for dark theme matching the reference design
st.markdown("""
<style>
    /* Dark theme styling */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1e293b;
        border-right: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    /* Form styling */
    .stTextArea textarea {
        background-color: rgba(15, 23, 42, 0.6);
        color: #f8fafc;
        border: 1px solid rgba(148, 163, 184, 0.2);
    }
    
    .stTextInput input {
        background-color: rgba(15, 23, 42, 0.6);
        color: #f8fafc;
        border: 1px solid rgba(148, 163, 184, 0.2);
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(135deg, #38bdf8 0%, #0ea5e9 100%);
        color: #0f172a;
        font-weight: 600;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.4);
    }
    
    /* Number input styling */
    .stNumberInput input {
        background-color: rgba(15, 23, 42, 0.6);
        color: #f8fafc;
        border: 1px solid rgba(148, 163, 184, 0.2);
    }
    
    /* Selectbox styling */
    .stSelectbox label {
        color: #f8fafc;
    }
    
    /* Image container */
    .image-container {
        background: rgba(15, 23, 42, 0.7);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid rgba(148, 163, 184, 0.15);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Streamlit UI
st.set_page_config(
    page_title="AI Image Generator", 
    page_icon="🎨", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main layout with sidebar
with st.sidebar:
    st.markdown("### 🎨 Generate Images")
    
    # Model selection
    st.markdown("**Model**")
    model_selected = st.selectbox(
        "Select Model",
        ["Google Nano Banana"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Prompt input
    prompt = st.text_area(
        "Describe your image or upload",
        placeholder="Enter a detailed description of what you want to generate...",
        height=120,
        help="Describe the image you want to generate"
    )
    
    # Reference images section
    st.markdown("**Image References**")
    uploaded_file = st.file_uploader(
        "Add reference image",
        type=["png", "jpg", "jpeg", "webp"],
        help="Upload an image to use as reference (0/8)",
        label_visibility="collapsed"
    )
    
    image_url = st.text_input(
        "Or paste image URL",
        placeholder="https://example.com/image.png",
        help="Paste a URL to an image",
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Generation parameters
    st.markdown("**Output Configuration**")
    
    # Number of images selector
    col_num1, col_num2, col_num3 = st.columns([1, 2, 1])
    with col_num2:
        num_images = st.number_input(
            "Number of Images",
            min_value=1,
            max_value=4,
            value=1,
            step=1,
            label_visibility="visible"
        )
    
    # Aspect ratio selector
    aspect_ratio = st.selectbox(
        "Aspect Ratio",
        ["21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"],
        index=5,  # Default to 1:1
        help="Select the aspect ratio for generated images"
    )
    
    st.divider()
    
    # Preserve identity checkbox
    preserve_identity = st.checkbox(
        "Preserve Identity",
        value=True,
        help="Keep original face and features when using reference image"
    )
    
    st.divider()
    
    # Generate button
    submit_button = st.button(
        "✨ Generate",
        use_container_width=True,
        type="primary"
    )
    
    st.markdown("---")
    st.caption("💾 Images saved to `outputs/` directory")

# Main content area
st.markdown("### 📸 Generated Images")

# Handle form submission
if submit_button:
    if not prompt.strip():
        st.error("❌ Please enter a prompt first!")
    else:
        reference_url: Optional[str] = None
        
        # Handle image URL
        if image_url and image_url.strip():
            if not image_url.lower().startswith(("http://", "https://")):
                st.error("❌ Image URL must start with http:// or https://")
                st.stop()
            try:
                with st.spinner("📤 Uploading image from URL..."):
                    reference_url = _upload_remote_image(image_url.strip())
            except Exception as e:
                st.error(f"❌ Failed to fetch image from URL: {e}")
                st.stop()
        
        # Handle file upload
        elif uploaded_file is not None:
            try:
                with st.spinner("📤 Uploading image file..."):
                    reference_url = _upload_user_image(uploaded_file)
            except Exception as e:
                st.error(f"❌ Failed to upload image: {e}")
                st.stop()
        
        # Generate images
        try:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.info(f"🎨 Generating {num_images} image(s) with aspect ratio {aspect_ratio}...")
            
            images = generate_images(
                prompt,
                image_url=reference_url,
                preserve_identity=preserve_identity,
                num_images=num_images,
                aspect_ratio=aspect_ratio,
            )
            
            progress_bar.progress(100)
            status_text.empty()
            
            if images:
                st.success(f"✅ Successfully generated {len(images)} image(s)!")
                st.markdown("---")
                
                # Display images in grid based on number of images
                if len(images) == 1:
                    cols = st.columns(1)
                elif len(images) == 2:
                    cols = st.columns(2)
                elif len(images) == 3:
                    cols = st.columns(3)
                else:  # 4 images
                    cols = st.columns(2)
                
                for idx, image in enumerate(images):
                    col_idx = idx % len(cols)
                    with cols[col_idx]:
                        # Image container with styling
                        st.markdown(f'<div class="image-container">', unsafe_allow_html=True)
                        st.image(
                            image["url"], 
                            caption=f"**{image['file_name']}**",
                            use_container_width=True
                        )
                        
                        # Show local path
                        if image.get("local_path"):
                            with st.expander("📁 View Local Path"):
                                st.code(image["local_path"], language=None)
                                st.caption(f"✅ Saved locally")
                        st.markdown('</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"❌ Error generating images: {e}")
            st.exception(e)
else:
    # Show placeholder or instructions
    st.info("👈 Use the sidebar to configure and generate images. Select number of images (1-4) and aspect ratio, then click Generate!")

# Show saved images history section
st.markdown("---")
st.markdown("### 📚 History")

if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
    saved_images = sorted(OUTPUT_DIR.glob("*.png")) + sorted(OUTPUT_DIR.glob("*.jpg")) + sorted(OUTPUT_DIR.glob("*.webp"))
    if saved_images:
        # Show in grid layout
        num_cols = 4
        for i in range(0, len(saved_images[:16]), num_cols):  # Show max 16 images
            cols = st.columns(num_cols)
            for j, col in enumerate(cols):
                if i + j < len(saved_images):
                    img_path = saved_images[i + j]
                    with col:
                        st.image(
                            str(img_path), 
                            caption=img_path.name,
                            use_container_width=True
                        )
                        with st.expander("📁 Path"):
                            st.code(str(img_path.resolve()), language=None)
    else:
        st.info("No saved images yet. Generate some images to see them here!")
else:
    st.info("📂 No images saved yet. Generate your first image to see it here!")