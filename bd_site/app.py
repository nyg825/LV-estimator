import os
import glob
from flask import Flask, render_template

app = Flask(__name__)


def get_project_photos():
    """Auto-discover photos in static/images/projects/<slug>/ folders."""
    photos = {}
    projects_dir = os.path.join(app.static_folder, "images", "projects")
    if not os.path.exists(projects_dir):
        return photos
    for slug in os.listdir(projects_dir):
        slug_dir = os.path.join(projects_dir, slug)
        if not os.path.isdir(slug_dir):
            continue
        imgs = sorted(
            [f for f in os.listdir(slug_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))],
            key=lambda x: x,
        )
        if imgs:
            photos[slug] = [f"images/projects/{slug}/{img}" for img in imgs]
    return photos


@app.route("/")
def index():
    project_photos = get_project_photos()
    return render_template("index.html", project_photos=project_photos)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
